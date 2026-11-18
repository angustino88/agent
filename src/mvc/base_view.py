from __future__ import annotations
import enum
from abc import ABCMeta, abstractmethod
from typing import TypeVar, Any, Callable, TYPE_CHECKING
from .task_engine import TaskEngine
from .registry import Registry
from .event_bus import EventBus, BusMixin
from .lifecycle import Lifecycle, State

if TYPE_CHECKING:
    from .base_model import BaseMainModel

T = TypeVar("T", bound="BaseView")


class ViewState(str, enum.Enum):
    """Discrete display states for any sub-view or root view.

    Transition between states with ``set_loading()``, ``set_ready()``,
    ``set_error()``, and ``set_empty()``; each emits a
    ``"{ClassName}.state.changed"`` bus event so other components
    (e.g. a spinner widget) can react without coupling to the view class.
    """
    IDLE    = "idle"
    LOADING = "loading"
    READY   = "ready"
    ERROR   = "error"
    EMPTY   = "empty"


class BaseView(Lifecycle, metaclass=ABCMeta):
    """Abstract base for sub-views.

    Provides reactive subscriptions (``subscribe`` / ``bind_model``),
    display-state tracking (``set_loading`` / ``set_ready`` / ``set_error`` /
    ``set_empty``), transient notifications (``flash``), teardown hooks
    (``on_teardown``), and a bus request shortcut (``request``).
    """

    def __init__(self) -> None:
        super().__init__()
        self._subscriptions   : list[tuple[str, Callable]] = []
        self._teardown_hooks  : list[Callable]             = []
        self._view_state      : ViewState                  = ViewState.IDLE

    def bind(self, view: BaseMainView, model: BaseMainModel) -> None:
        """Bind to the root view and model."""
        self._view  = view
        self._model = model

    @property
    def view(self) -> BaseMainView:
        try:
            return self._view
        except AttributeError:
            raise RuntimeError(f"{type(self).__name__} must be bound first.")

    @property
    def model(self) -> BaseMainModel:
        try:
            return self._model
        except AttributeError:
            raise RuntimeError(f"{type(self).__name__} must be bound first.")

    @property
    def view_state(self) -> ViewState:
        """The current display state of this view."""
        return self._view_state

    def get(self, cls: type[T], key: str | None = None) -> T:
        return self.view.get(cls, key)

    def get_all(self, cls: type[T]) -> list[T]:
        return self.view.get_all(cls)

    def bus_emit(self, event: str, payload: Any = None) -> None:
        self.view.bus.emit(event, payload)

    def bus_request(self, event: str, payload: Any = None, timeout: float = 2.0) -> Any:
        """Blocking request/response via the bus."""
        return self.view.bus.request(event, payload, timeout)

    def bus_subscribe(
        self,
        event   : str,
        handler : Callable,
        *,
        priority: int  = 0,
        once    : bool = False,
        weak    : bool = False,
    ) -> None:
        self.view.bus.subscribe(event, handler, priority=priority, once=once, weak=weak)
        if not once:
            self._subscriptions.append((event, handler))

    def bus_subscribe_once(self, event: str, handler: Callable, *, priority: int = 0) -> None:
        self.view.bus.subscribe_once(event, handler, priority=priority)

    def bus_unsubscribe(self, event: str, handler: Callable) -> None:
        self.view.bus.unsubscribe(event, handler)
        self._subscriptions = [
            (e, h) for e, h in self._subscriptions
            if not (e == event and h is handler)
        ]

    def bind_model(self, event: str, handler: Callable, *, once: bool = False) -> None:
        """Subscribe to a model-sourced bus event (semantic alias for ``bus_subscribe``).

        Use instead of ``bus_subscribe`` when the handler reacts to model state
        changes (e.g. ``"chocomodel.packages.changed"``) rather than UI gestures.
        Tracked for automatic cleanup in ``teardown()``.
        """
        self.bus_subscribe(event, handler, once=once)

    def on_teardown(self, hook: Callable) -> None:
        """Register a zero-arg cleanup callable invoked during ``teardown()``.

        Use to release Qt connections, timers, or other resources that are not
        tracked via ``subscribe``.
        """
        self._teardown_hooks.append(hook)

    # ---- display-state helpers ---------------------------------------------

    def set_state(self, state: ViewState, payload: Any = None) -> None:
        """Transition to *state* and emit ``"{ClassName}.state.changed"`` on the bus."""
        self._view_state = state
        self.bus_emit(
            f"{type(self).__name__.lower()}.state.changed",
            {"state": state, "payload": payload},
        )

    def set_loading(self, message: str | None = None) -> None:
        """Transition to ``LOADING`` state."""
        self.set_state(ViewState.LOADING, message)

    def set_ready(self, payload: Any = None) -> None:
        """Transition to ``READY`` state."""
        self.set_state(ViewState.READY, payload)

    def set_error(self, message: str) -> None:
        """Transition to ``ERROR`` state with *message*."""
        self.set_state(ViewState.ERROR, message)

    def set_empty(self, message: str | None = None) -> None:
        """Transition to ``EMPTY`` state."""
        self.set_state(ViewState.EMPTY, message)

    def flash(self, message: str, level: str = "info") -> None:
        """Emit a ``"view.flash"`` event for transient UI notifications.

        *level* is a hint for the receiver (``"info"``, ``"warning"``,
        ``"error"``, ``"success"``).
        """
        self.bus_emit("view.flash", {
            "message": message,
            "level":   level,
            "source":  type(self).__name__,
        })

    def teardown(self) -> None:
        """Unsubscribe all tracked handlers and run registered teardown hooks."""
        for event, handler in self._subscriptions:
            self.view.bus.unsubscribe(event, handler)
        self._subscriptions.clear()
        for hook in self._teardown_hooks:
            try:
                hook()
            except Exception:
                pass
        self._teardown_hooks.clear()
        self._transition(State.STOPPED)

    @abstractmethod
    def init(self) -> None: ...


class BaseMainView(BusMixin, TaskEngine, Lifecycle, metaclass=ABCMeta):
    """Abstract root view — registry, bus access, and sub-view lifecycle."""

    def __init__(
        self,
        model: BaseMainModel,
        bus: EventBus,
        max_workers: int = 4
    ) -> None:
        TaskEngine.__init__(self, max_workers=max_workers)
        Lifecycle.__init__(self)
        self._model          = model
        self._bus            = bus
        self._registry       = Registry()
        self._sub_views      : list[BaseView] = []
        self._teardown_hooks : list[Callable] = []
        self._setup()
        for sub in self._sub_views:
            sub.init()
            sub._transition(State.INITIALIZED)
        self._configure()
        self.runner.start()
        self._transition(State.RUNNING)

    @property
    def model(self) -> BaseMainModel:
        return self._model

    @property
    def bus(self) -> EventBus:
        return self._bus

    def on_teardown(self, hook: Callable) -> None:
        """Register a zero-arg cleanup callable invoked during ``teardown()``."""
        self._teardown_hooks.append(hook)

    def register(self, obj: object, key: str | None = None) -> None:
        self._registry.register(obj, key)

    def get(self, cls: type[T], key: str | None = None) -> T:
        return self._registry.get(cls, key)

    def get_all(self, cls: type[T]) -> list[T]:
        return self._registry.get_all(cls)

    def _make(self, view_class: type[T], key: str | None = None) -> T:
        """Instantiate, bind, and register a sub-view; return the instance."""
        try:
            obj: T = view_class()
            obj.bind(self, self._model)
            self._registry.register(obj, key)
            self.register_task(obj)
            self._sub_views.append(obj)
            return obj
        except Exception as e:
            raise RuntimeError(
                f"Failed to create view '{view_class.__name__}': {e}"
            ) from e

    def teardown(self) -> None:
        """Tear down all sub-views, run teardown hooks, and stop the runner."""
        for sub in self._sub_views:
            try:
                sub.teardown()
            except Exception:
                pass
        for hook in self._teardown_hooks:
            try:
                hook()
            except Exception:
                pass
        self._teardown_hooks.clear()
        self.runner.stop()
        self._transition(State.STOPPED)

    @abstractmethod
    def _setup(self) -> None:
        """Pass 1 — create all sub-views with ``_make()``."""
        ...

    def _configure(self) -> None:
        """Pass 3 — optional cross-view wiring after all ``init()`` calls.  Default is a no-op."""