from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from abc import ABCMeta, abstractmethod
from typing import TypeVar, Any, Callable
from .task_engine import TaskEngine
from .registry import Registry
from .event_bus import EventBus, BusMixin
from .lifecycle import Lifecycle, State
from .command import Command
from .middleware import Middleware, MiddlewarePipeline

T = TypeVar("T", bound="BaseModel")
_MISSING = object()   # sentinel — distinct from None for set_field change detection


# ---------------------------------------------------------------------------
# BaseModel  (sub-model)
# ---------------------------------------------------------------------------

class BaseModel(Lifecycle, metaclass=ABCMeta):
    """Abstract base for sub-models."""

    def __init__(self) -> None:
        super().__init__()
        self._subscriptions: list[tuple[str, Callable]] = []
        self._batching: bool = False
        self._batch_queue: list[tuple[str, Any]] = []

    def bind(self, model: BaseMainModel) -> None:
        self._model = model

    @property
    def model(self) -> BaseMainModel:
        try:
            return self._model
        except AttributeError:
            raise RuntimeError(f"{type(self).__name__} must be bound first.")

    # Registry shortcuts
    def get(self, cls: type[T], key: str | None = None) -> T:
        return self.model.get(cls, key)

    def get_all(self, cls: type[T]) -> list[T]:
        return self.model.get_all(cls)

    # Bus shortcuts
    def bus_emit(self, event: str, payload: Any = None) -> None:
        if self._batching:
            self._batch_queue.append((event, payload))
        else:
            self.model.bus.emit(event, payload)

    @contextmanager
    def batch(self):
        """Defer all event emissions from ``set_field`` / ``notify`` until the block exits.

        Views are notified only once after all mutations are complete::

            with self.batch():
                self.set_field("_items", new_items)
                self.set_field("_count", len(new_items))
            # → both events emitted here, atomically
        """
        self._batching = True
        self._batch_queue = []
        try:
            yield
        finally:
            self._batching = False
            queue = self._batch_queue
            self._batch_queue = []
            for event, payload in queue:
                self.model.bus.emit(event, payload)

    def bus_subscribe(
        self,
        event   : str,
        handler : Callable,
        *,
        priority: int  = 0,
        once    : bool = False,
        weak    : bool = False,
    ) -> None:
        self.model.bus.subscribe(event, handler, priority=priority, once=once, weak=weak)
        if not once:
            self._subscriptions.append((event, handler))

    def bus_subscribe_once(self, event: str, handler: Callable, *, priority: int = 0) -> None:
        self.model.bus.subscribe_once(event, handler, priority=priority)

    def bus_unsubscribe(self, event: str, handler: Callable) -> None:
        self.model.bus.unsubscribe(event, handler)
        self._subscriptions = [
            (e, h) for e, h in self._subscriptions
            if not (e == event and h is handler)
        ]

    # ---- observable field helpers ------------------------------------------

    def set_field(self, name: str, value: Any,
                  *, event: str | None = None, force: bool = False) -> bool:
        """Set attribute *name* and emit ``"{class}.{field}.changed"``.

        No-op if the value is unchanged; use ``force=True`` for mutable
        containers.  Returns ``True`` when a change occurred.
        """
        current = getattr(self, name, _MISSING)
        if not force and current is not _MISSING and current == value:
            return False
        setattr(self, name, value)
        field = name.lstrip("_")
        self.bus_emit(event or f"{type(self).__name__.lower()}.{field}.changed", value)
        return True

    def notify(self, field: str, value: Any = None,
               *, event: str | None = None) -> None:
        """Emit ``"{class}.{field}.changed"`` without modifying an attribute.

        Use after in-place mutations (list append, dict update) where
        ``set_field`` won't detect a change.
        """
        self.bus_emit(event or f"{type(self).__name__.lower()}.{field}.changed", value)

    def teardown(self) -> None:
        """Unsubscribe all tracked handlers and mark as stopped."""
        for event, handler in self._subscriptions:
            self.model.bus.unsubscribe(event, handler)
        self._subscriptions.clear()
        self._transition(State.STOPPED)

    @abstractmethod
    def init(self) -> None: ...


# ---------------------------------------------------------------------------
# BaseMainModel  (root model)
# ---------------------------------------------------------------------------

class BaseMainModel(BusMixin, TaskEngine, Lifecycle, metaclass=ABCMeta):
    """Abstract root model — the **composition root** of the model layer.

    Store every sub-model as a **typed attribute** via ``_make()``; siblings
    access each other through ``self.model.<attr>`` — no string keys, full
    IDE navigation.  Sub-models are initialised in declaration order, so
    declare dependencies before the models that need them.

    Lifecycle order:

    1. ``_setup()``   — instantiate all sub-models with ``_make()`` (no I/O).
    2. ``_prepare()`` — environment setup between construction and init:
                        create runtime dirs, apply env overrides, validate
                        bundle paths.  Default is a no-op.
    3. ``init()``     — each sub-model's ``init()`` is called in order.
    4. ``_configure()`` — cross-cutting wiring after all inits complete.

    External resources that need cleanup (DB connections, HTTP clients) are
    stored as typed attributes too; register their teardown with
    ``on_teardown(hook)``.

    Commands (``Command`` subclasses) dispatched via ``execute()`` or
    ``execute_async()`` can be tracked for undo / redo and run through a
    middleware pipeline for cross-cutting concerns.
    """

    def __init__(self, bus: EventBus, max_workers: int = 4) -> None:
        TaskEngine.__init__(self, max_workers=max_workers)
        Lifecycle.__init__(self)
        self._registry       = Registry()
        self._bus            = bus
        self._sub_models     : list[BaseModel] = []
        self._teardown_hooks : list[Callable]  = []
        self._undo_stack     : list[Command]   = []
        self._redo_stack     : list[Command]   = []
        self._pipeline       = MiddlewarePipeline()
        self._setup()
        self._prepare()
        for sub in self._sub_models:
            sub.init()
            sub._transition(State.INITIALIZED)
        self._configure()
        self.runner.start()
        self._transition(State.RUNNING)

    @property
    def bus(self) -> EventBus:
        return self._bus

    # ---- teardown hooks -----------------------------------------------------

    def on_teardown(self, hook: Callable) -> None:
        """Register a zero-arg cleanup function called when the root model tears down."""
        self._teardown_hooks.append(hook)

    def add_middleware(self, middleware: Middleware) -> None:
        """Append *middleware* to the command execution pipeline.

        Middleware is applied in registration order to every ``execute()``
        and ``execute_async()`` call.  Use for logging, access control,
        rate limiting, or telemetry.
        """
        self._pipeline.add(middleware)

    def remove_middleware(self, middleware: Middleware) -> None:
        """Remove a previously registered middleware from the pipeline."""
        self._pipeline.remove(middleware)

    # ---- command dispatch ---------------------------------------------------

    def execute(self, cmd: Command) -> Any:
        """Execute *cmd* synchronously through the middleware pipeline.

        Pushes to the undo stack when ``cmd.can_undo()`` is ``True`` and
        clears the redo stack.  Returns ``None`` without executing when
        ``cmd.can_execute()`` is ``False``.
        """
        if not cmd.can_execute():
            return None

        def _run() -> Any:
            result = cmd.execute()
            if cmd.can_undo():
                self._undo_stack.append(cmd)
                self._redo_stack.clear()
            return result

        return self._pipeline.run(cmd, _run)

    def execute_async(
        self,
        cmd      : Command,
        *,
        on_done  : Callable[[Any], None] | None = None,
        on_error : Callable[[Exception], None] | None = None,
    ) -> None:
        """Dispatch *cmd* to the thread pool so the UI stays responsive.

        Emits ``"command.started"``, ``"command.done"``, and ``"command.error"``
        on the bus around the command lifecycle.  *on_done* / *on_error* are
        optional callbacks in addition to bus events.  The undo stack is
        updated on success when ``cmd.can_undo()`` is ``True``.
        """
        if not cmd.can_execute():
            return

        bus = self._bus
        pipeline = self._pipeline

        def _run() -> None:
            bus.emit("command.started", cmd)

            def _execute() -> Any:
                return cmd.execute()

            try:
                result = pipeline.run(cmd, _execute)
            except Exception as exc:
                bus.emit("command.error", exc)
                if on_error:
                    on_error(exc)
                return
            if cmd.can_undo():
                self._undo_stack.append(cmd)
                self._redo_stack.clear()
            bus.emit("command.done", result)
            if on_done:
                on_done(result)

        self.runner._executor.submit(_run)

    def undo(self) -> bool:
        """Undo the last tracked command.  Returns ``True`` if a command was undone."""
        if not self._undo_stack:
            return False
        cmd = self._undo_stack.pop()
        cmd.undo()
        self._redo_stack.append(cmd)
        return True

    def redo(self) -> bool:
        """Re-execute the last undone command.  Returns ``True`` if successful."""
        if not self._redo_stack:
            return False
        cmd = self._redo_stack.pop()
        cmd.execute()
        self._undo_stack.append(cmd)
        return True

    @property
    def can_undo(self) -> bool:
        """``True`` if there is at least one command on the undo stack."""
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        """``True`` if there is at least one command on the redo stack."""
        return bool(self._redo_stack)

    def clear_history(self) -> None:
        """Discard the undo and redo stacks."""
        self._undo_stack.clear()
        self._redo_stack.clear()

    # ---- registry -----------------------------------------------------------

    def register(self, obj: object, key: str | None = None) -> None:
        self._registry.register(obj, key)

    def get(self, cls: type[T], key: str | None = None) -> T:
        return self._registry.get(cls, key)

    def get_all(self, cls: type[T]) -> list[T]:
        return self._registry.get_all(cls)

    # ---- factory ------------------------------------------------------------

    def _make(self, model_class: type[T], key: str | None = None) -> T:
        """Instantiate, bind, and register a sub-model; return the instance.

        Store the return value as a typed attribute so siblings can reach it
        through ``self.model.<attr>`` — no registry lookup needed at call sites.
        """
        try:
            obj: T = model_class()
            obj.bind(self)
            self._registry.register(obj, key)
            self.register_task(obj)
            self._sub_models.append(obj)
            return obj
        except Exception as e:
            raise RuntimeError(
                f"Failed to create model '{model_class.__name__}': {e}"
            ) from e

    # ---- lifecycle ----------------------------------------------------------

    def teardown(self) -> None:
        """Stop sub-models, run teardown hooks, stop the runner."""
        for sub in self._sub_models:
            try:
                sub.teardown()
            except Exception:
                pass
        for hook in self._teardown_hooks:
            try:
                hook()
            except Exception:
                pass
        self.runner.stop()
        self._transition(State.STOPPED)

    # ---- utilities ----------------------------------------------------------

    def _make_runtime_dirs(self, *dirs: str | Path) -> list[Path]:
        """Create directories if absent and return their resolved paths."""
        paths: list[Path] = []
        for d in dirs:
            path = Path(d).resolve()
            path.mkdir(parents=True, exist_ok=True)
            paths.append(path)
        return paths

    # ---- abstract hooks -----------------------------------------------------

    @abstractmethod
    def _setup(self) -> None:
        """Pass 1 — create all sub-models with ``_make()``.

        Store each return value as a typed attribute.  Sub-models initialise
        in declaration order; place dependencies before the models that need them.
        No I/O here — directories may not exist yet.
        """
        ...

    def _prepare(self) -> None:
        """Pass 2 — environment setup after construction, before ``init()``.

        Override to create runtime directories, apply env-var overrides, or
        validate bundled resources.  All sub-model objects exist at this point
        but none have called ``init()`` yet, so no file I/O has occurred.

        Typical usage::

            def _prepare(self) -> None:
                self._make_runtime_dirs(*self.config_model.app_config.runtime_dirs)
                self.config_model.app_config.validate_bundle()
        """

    def _configure(self) -> None:
        """Pass 4 — cross-cutting wiring after all ``init()`` calls complete.

        All typed sub-model attributes from ``_setup()`` are available here.
        Default is a no-op.
        """