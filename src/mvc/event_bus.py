from collections import defaultdict
from functools import wraps
from typing import Callable, Any, Optional, Union
import concurrent.futures
import threading
import time
import weakref
import fnmatch
import logging
from .event_def import EventDef

log = logging.getLogger(__name__)

# Type alias accepted by all public bus methods
_EventArg = Union[str, EventDef]


# ======================================================================
# BusMixin — shared emit / subscribe shortcuts for root MVC classes
# ======================================================================

class BusMixin:
    """Mixin that adds ``emit`` / ``subscribe`` / ``subscribe_once`` /
    ``unsubscribe`` / ``request`` shortcuts to any class that exposes a
    ``bus`` property returning an :class:`EventBus`.

    Intended for root classes (``BaseMainModel``, ``BaseMainController``,
    ``BaseMainView``) which all own ``self._bus`` directly.  Sub-classes
    (``BaseModel``, ``BaseController``, ``BaseView``) are NOT expected to
    use this mixin because they route through their parent's bus (and
    ``BaseModel.emit`` adds batch-defer logic on top).
    """

    @property
    def bus(self) -> "EventBus":
        raise NotImplementedError  # concrete class must override

    def bus_emit(self, event: str, payload: Any = None) -> None:
        self.bus.emit(event, payload)

    def bus_subscribe(
        self,
        event   : str,
        handler : Callable,
        *,
        priority: int  = 0,
        once    : bool = False,
        weak    : bool = False,
    ) -> None:
        self.bus.subscribe(event, handler, priority=priority, once=once, weak=weak)

    def bus_subscribe_once(self, event: str, handler: Callable, *, priority: int = 0) -> None:
        self.bus.subscribe_once(event, handler, priority=priority)

    def bus_unsubscribe(self, event: str, handler: Callable) -> None:
        self.bus.unsubscribe(event, handler)

    def bus_request(self, event: str, payload: Any = None, timeout: float = 2.0) -> Any:
        return self.bus.request(event, payload, timeout)


# ======================================================================
# Throttle / Debounce decorators
# ======================================================================

def throttle(interval: float) -> Callable:
    """Decorator — ensure *func* is called at most once per *interval* seconds.

    Excess calls within the window are silently dropped.  Thread-safe.

    Usage::

        @throttle(0.3)
        def on_resize(self, payload):
            self._relayout()

        bus.subscribe("window.resized", on_resize)
    """

    def wrapper(func: Callable) -> Callable:
        last_call: list[float] = [0.0]
        lock = threading.Lock()

        @wraps(func)
        def throttled(*args: Any, **kwargs: Any) -> Any:
            now = time.monotonic()
            with lock:
                if now - last_call[0] >= interval:
                    last_call[0] = now
                else:
                    return None
            return func(*args, **kwargs)

        return throttled

    return wrapper


def debounce(delay: float) -> Callable:
    """Decorator — delay *func* until *delay* seconds of silence.

    Every call resets the timer.  Only the **last** call in a burst
    actually executes.  Thread-safe.

    Usage::

        @debounce(0.25)
        def on_search_text_changed(self, payload):
            self._run_search(payload)

        bus.subscribe("search.changed", on_search_text_changed)
    """

    def wrapper(func: Callable) -> Callable:
        timer: list[threading.Timer | None] = [None]
        lock = threading.Lock()

        @wraps(func)
        def debounced(*args: Any, **kwargs: Any) -> None:
            with lock:
                if timer[0] is not None:
                    timer[0].cancel()
                timer[0] = threading.Timer(delay, func, args, kwargs)
                timer[0].daemon = True
                timer[0].start()

        return debounced

    return wrapper


class _Subscription:
    """Internal descriptor for a single handler registration."""

    __slots__ = ("_handler", "_weak", "priority", "once")

    def __init__(
        self,
        handler : Callable,
        priority: int  = 0,
        once    : bool = False,
        weak    : bool = False,
    ) -> None:
        self.priority = priority
        self.once     = once
        if weak:
            # WeakMethod for bound methods, plain weakref for functions/lambdas
            self._weak    = weakref.WeakMethod(handler) if hasattr(handler, "__self__") else weakref.ref(handler)
            self._handler = None
        else:
            self._handler = handler
            self._weak    = None

    def get(self) -> Optional[Callable]:
        """Return the handler, or *None* if the weak reference has expired."""
        return self._weak() if self._weak is not None else self._handler

    def is_alive(self) -> bool:
        return self._weak() is not None if self._weak is not None else True


class EventBus:
    """Thread-safe publish/subscribe event bus.

    Features
    --------
    * **Priority** – handlers execute highest-priority-first.
    * **One-shot** – ``once=True`` auto-unsubscribes after the first call.
    * **Weak references** – ``weak=True`` prevents the bus from keeping
      objects alive; dead refs are pruned lazily.
    * **Wildcard patterns** – subscribe with ``fnmatch``-style patterns
      (e.g. ``"app.*"``) to match multiple emitted events.
    * **Async emit** – ``emit_async`` dispatches to a thread-pool.
    * **Collect** – ``emit_collect`` returns every handler's return value.
    * **Request/response** – ``request`` blocks until a handler resolves a
      ``Future``.
    * **Error isolation** – handler exceptions are caught; an optional global
      error hook receives them instead of propagating.
    """

    def __init__(self, executor: Optional[concurrent.futures.Executor] = None) -> None:
        self._bus     : dict[str, list[_Subscription]] = defaultdict(list)
        self._lock    : threading.RLock                = threading.RLock()
        self._executor: concurrent.futures.Executor    = executor or concurrent.futures.ThreadPoolExecutor()
        self._on_error: Optional[Callable[[str, Callable, Exception], None]] = None

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_error_handler(self, handler: Callable[[str, Callable, Exception], None]) -> None:
        """Set a global error callback ``(event, handler, exc)`` for subscriber exceptions."""
        self._on_error = handler

    # ------------------------------------------------------------------
    # Subscribe / Unsubscribe
    # ------------------------------------------------------------------

    def subscribe(
        self,
        event   : _EventArg,
        handler : Callable[[Any], None],
        *,
        priority: int  = 0,
        once    : bool = False,
        weak    : bool = False,
    ) -> None:
        """Register *handler* for *event* (supports ``fnmatch`` wildcard patterns).

        *event* may be an :class:`EventDef` or a plain ``str``.
        ``priority`` controls execution order (higher first).
        ``once=True`` auto-unsubscribes after the first call.
        ``weak=True`` holds only a weak reference to the handler.
        """
        sub = _Subscription(handler, priority=priority, once=once, weak=weak)
        key = str(event)   # EventDef.__str__ returns its name
        with self._lock:
            subs = self._bus[key]
            # Deduplicate non-weak registrations by identity
            if not weak and any(s.get() is handler for s in subs):
                return
            subs.append(sub)
            subs.sort(key=lambda s: s.priority, reverse=True)

    def subscribe_once(
        self,
        event   : _EventArg,
        handler : Callable[[Any], None],
        *,
        priority: int = 0,
    ) -> None:
        """Equivalent to ``subscribe(..., once=True)``."""
        self.bus_subscribe(event, handler, priority=priority, once=True)

    def unsubscribe(self, event: _EventArg, handler: Callable[[Any], None]) -> None:
        """Remove *handler* from *event*.  Silent if not registered."""
        key = str(event)
        with self._lock:
            subs = self._bus.get(key)
            if subs is None:
                return
            self._bus[key] = [s for s in subs if s.get() is not handler]

    def unsubscribe_all(self, event: _EventArg) -> None:
        """Remove every subscriber for *event*."""
        key = str(event)
        with self._lock:
            self._bus.pop(key, None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _matching_keys(self, event: str) -> list[str]:
        """Return all registered keys whose *pattern* matches *event* (plain str only)."""
        return [key for key in self._bus if fnmatch.fnmatch(event, key)]

    def _snapshot(self, event: str) -> list[tuple[str, _Subscription]]:
        """Snapshot live subscriptions for *event*, pruning dead weak-refs.

        Must be called while holding ``self._lock``.
        """
        result: list[tuple[str, _Subscription]] = []
        dead  : list[tuple[str, _Subscription]] = []

        for key in self._matching_keys(event):
            for sub in list(self._bus[key]):
                if sub.is_alive():
                    result.append((key, sub))
                else:
                    dead.append((key, sub))

        for key, sub in dead:
            try:
                self._bus[key].remove(sub)
            except ValueError:
                pass

        return result

    def _invoke(self, event: str, key: str, sub: _Subscription, payload: Any) -> Any:
        """Invoke one subscription, honouring ``once`` and catching errors."""
        handler = sub.get()
        if handler is None:
            return None

        if sub.once:
            with self._lock:
                try:
                    self._bus[key].remove(sub)
                except ValueError:
                    pass  # already removed by a concurrent emit

        try:
            return handler(payload)
        except Exception as exc:
            if self._on_error:
                self._on_error(event, handler, exc)
            else:
                log.exception("EventBus: handler %r raised for event %r", handler, event)
            return None

    # ------------------------------------------------------------------
    # Public emit API
    # ------------------------------------------------------------------

    def emit(self, event: _EventArg, payload: Any = None) -> None:
        """Synchronously call all handlers for *event* in priority order.

        If *event* is an :class:`EventDef`, its ``payload_type`` is enforced
        before any handler is invoked — identical to PyQt signal type checking.
        Raises ``TypeError`` on mismatch.  Plain ``str`` events skip validation.
        """
        if isinstance(event, EventDef):
            event.validate(payload)   # raises TypeError on mismatch
            event_name = event.name
        else:
            event_name = event
        with self._lock:
            pairs = self._snapshot(event_name)
        for key, sub in pairs:
            self._invoke(event_name, key, sub, payload)

    def emit_event(self, event: Any) -> None:
        """Emit a typed :class:`Event` instance.

        The event's ``topic`` class-variable is used as the event name,
        and the event object itself becomes the payload::

            bus.emit_event(PackagesLoaded(packages=[...]))
        """
        topic = getattr(type(event), "topic", None)
        if not topic:
            raise TypeError(
                f"{type(event).__name__} does not define a `topic` ClassVar."
            )
        self.emit(topic, event)

    def emit_async(self, event: _EventArg, payload: Any = None) -> concurrent.futures.Future:
        """Dispatch *event* on the internal thread-pool; returns a ``Future``.

        Payload validation (for :class:`EventDef`) is performed on the calling
        thread before the task is submitted, so the ``TypeError`` surfaces
        immediately rather than inside the worker.
        """
        if isinstance(event, EventDef):
            event.validate(payload)   # validate eagerly on the caller's thread
        return self._executor.submit(self.emit, event, payload)

    def emit_collect(self, event: _EventArg, payload: Any = None) -> list[Any]:
        """Emit *event* synchronously and collect every handler's return value."""
        if isinstance(event, EventDef):
            event.validate(payload)
            event_name = event.name
        else:
            event_name = event
        with self._lock:
            pairs = self._snapshot(event_name)
        return [self._invoke(event_name, key, sub, payload) for key, sub in pairs]

    def request(self, event: str, payload: Any = None, timeout: float = 2.0) -> Any:
        """Block until a handler calls ``future.set_result(value)`` and return it.

        Handler receives ``{"payload": ..., "future": Future}``.
        """
        future: concurrent.futures.Future = concurrent.futures.Future()
        self.emit(event, {"payload": payload, "future": future})
        return future.result(timeout=timeout)

    # ------------------------------------------------------------------
    # Introspection / housekeeping
    # ------------------------------------------------------------------

    def events(self) -> list[str]:
        """Snapshot of all registered event/pattern names."""
        with self._lock:
            return list(self._bus.keys())

    def subscriber_count(self, event: _EventArg) -> int:
        """Number of live subscribers for *event*."""
        key = str(event)
        with self._lock:
            return sum(1 for s in self._bus.get(key, []) if s.is_alive())

    def clear(self) -> None:
        """Remove all subscriptions."""
        with self._lock:
            self._bus.clear()

    def __repr__(self) -> str:
        with self._lock:
            n_events = len(self._bus)
            n_subs   = sum(len(v) for v in self._bus.values())
        return f"<EventBus events={n_events} subscriptions={n_subs}>"