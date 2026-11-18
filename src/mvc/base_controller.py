from __future__ import annotations
from abc import ABCMeta, abstractmethod
from typing import TypeVar, Any, Callable, TYPE_CHECKING
from .task_engine import TaskEngine
from .registry import Registry
from .event_bus import EventBus, BusMixin
from .lifecycle import Lifecycle, State

if TYPE_CHECKING:
    from .base_model import BaseMainModel
    from .base_view import BaseMainView

T = TypeVar("T", bound="BaseController")


class BaseController(Lifecycle, metaclass=ABCMeta):
    """Abstract base for sub-controllers."""

    def __init__(self) -> None:
        super().__init__()
        self._subscriptions: list[tuple[str, Callable]] = []

    def bind(
        self,
        model: BaseMainModel,
        view: BaseMainView,
        controller: BaseMainController,
    ) -> None:
        self._model      = model
        self._view       = view
        self._controller = controller

    @property
    def model(self) -> BaseMainModel:
        try:
            return self._model
        except AttributeError:
            raise RuntimeError(f"{type(self).__name__} must be bound first.")

    @property
    def view(self) -> BaseMainView:
        try:
            return self._view
        except AttributeError:
            raise RuntimeError(f"{type(self).__name__} must be bound first.")

    @property
    def controller(self) -> BaseMainController:
        try:
            return self._controller
        except AttributeError:
            raise RuntimeError(f"{type(self).__name__} must be bound first.")

    # Registry shortcuts
    def get(self, cls: type[T], key: str | None = None) -> T:
        return self.controller.get(cls, key)

    def get_all(self, cls: type[T]) -> list[T]:
        return self.controller.get_all(cls)

    # Bus shortcuts
    def bus_emit(self, event: str, payload: Any = None) -> None:
        self.controller.bus.emit(event, payload)

    def bus_subscribe(
        self,
        event   : str,
        handler : Callable,
        *,
        priority: int  = 0,
        once    : bool = False,
        weak    : bool = False,
    ) -> None:
        self.controller.bus.subscribe(event, handler, priority=priority, once=once, weak=weak)
        if not once:
            self._subscriptions.append((event, handler))

    def bus_subscribe_once(self, event: str, handler: Callable, *, priority: int = 0) -> None:
        self.controller.bus.subscribe_once(event, handler, priority=priority)

    def bus_unsubscribe(self, event: str, handler: Callable) -> None:
        self.controller.bus.unsubscribe(event, handler)
        self._subscriptions = [
            (e, h) for e, h in self._subscriptions
            if not (e == event and h is handler)
        ]

    def bus_request(self, event: str, payload: Any = None, timeout: float = 2.0) -> Any:
        """Request/response via the bus; blocks until a handler resolves the future."""
        return self.controller.bus.request(event, payload, timeout)

    def execute(self, cmd: Any) -> Any:
        """Dispatch *cmd* through the model's command pipeline."""
        return self.model.execute(cmd)

    def execute_async(self, cmd: Any, **kwargs: Any) -> None:
        """Dispatch *cmd* asynchronously through the model's command pipeline."""
        self.model.execute_async(cmd, **kwargs)

    def expose_get(self, key: str, getter: Callable[[], Any]) -> None:
        """Respond to ``get:{key}`` bus requests by calling *getter*."""
        def handler(msg: dict) -> None:
            try:
                msg["future"].set_result(getter())
            except Exception as e:
                msg["future"].set_exception(e)
        self.bus_subscribe(f"get:{key}", handler)

    def expose_set(self, key: str, setter: Callable[[Any], None]) -> None:
        """Forward ``set:{key}`` bus events to *setter*."""
        self.bus_subscribe(f"set:{key}", setter)

    def teardown(self) -> None:
        """Unsubscribe all tracked handlers."""
        for event, handler in self._subscriptions:
            self.controller.bus.unsubscribe(event, handler)
        self._subscriptions.clear()
        self._transition(State.STOPPED)

    @abstractmethod
    def init(self) -> None: ...


class BaseMainController(BusMixin, TaskEngine, Lifecycle, metaclass=ABCMeta):
    """Abstract root controller — registry, bus access, and sub-controller lifecycle."""

    def __init__(
        self,
        model: BaseMainModel,
        view: BaseMainView,
        bus: EventBus,
        max_workers: int = 4,
    ) -> None:
        TaskEngine.__init__(self, max_workers=max_workers)
        Lifecycle.__init__(self)
        self._model    = model
        self._view     = view
        self._bus      = bus
        self._registry = Registry()
        self._sub_controllers: list[BaseController] = []

        # Pre-populate registry with top-level model and view
        self._registry.register(model)
        self._registry.register(view)

        self._setup()
        for sub in self._sub_controllers:
            sub.init()
            sub._transition(State.INITIALIZED)
        self._configure()
        self.runner.start()
        self._transition(State.RUNNING)

    @property
    def model(self) -> BaseMainModel:
        return self._model

    @property
    def view(self) -> BaseMainView:
        return self._view

    @property
    def bus(self) -> EventBus:
        return self._bus

    # Registry
    def register(self, obj: object, key: str | None = None) -> None:
        self._registry.register(obj, key)

    def get(self, cls: type[T], key: str | None = None) -> T:
        return self._registry.get(cls, key)

    def get_all(self, cls: type[T]) -> list[T]:
        return self._registry.get_all(cls)

    def _make(self, controller_class: type[T], key: str | None = None) -> T:
        """Instantiate, bind, and register a sub-controller; return the instance."""
        try:
            obj: T = controller_class()
            obj.bind(self._model, self._view, self)
            self._registry.register(obj, key)
            self.register_task(obj)
            self._sub_controllers.append(obj)
            return obj
        except Exception as e:
            raise RuntimeError(
                f"Failed to create '{controller_class.__name__}': {e}"
            ) from e

    def expose_get(self, key: str, getter: Callable[[], Any]) -> None:
        """Respond to ``get:{key}`` bus requests by calling *getter*."""
        def handler(msg: dict) -> None:
            try:
                msg["future"].set_result(getter())
            except Exception as e:
                msg["future"].set_exception(e)
        self._bus.subscribe(f"get:{key}", handler)

    def expose_set(self, key: str, setter: Callable[[Any], None]) -> None:
        """Forward ``set:{key}`` bus events to *setter*."""
        self._bus.subscribe(f"set:{key}", setter)

    def teardown(self) -> None:
        """Tear down sub-controllers, clear bus, stop runner; then teardown model and view."""
        for sub in self._sub_controllers:
            try:
                sub.teardown()
            except Exception:
                pass
        self._bus.clear()
        self.runner.stop()
        self._model.teardown()
        self._view.teardown()
        self._transition(State.STOPPED)

    @abstractmethod
    def _setup(self) -> None:
        """Pass 1 — create all sub-controllers with ``_make()``."""
        ...

    def _configure(self) -> None:
        """Pass 3 — optional cross-controller wiring after all ``init()`` calls.  Default is a no-op."""