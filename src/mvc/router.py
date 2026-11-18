from __future__ import annotations
from typing import Any
from .base_controller import BaseMainController
from .base_model import BaseMainModel
from .base_view import BaseMainView
from .event_bus import EventBus


class Route:
    __slots__ = (
        "model_class", "view_class", "controller_class",
        "model_kwargs", "view_kwargs", "controller_kwargs",
    )
    def __init__(self, model_class, view_class, controller_class,
                 model_kwargs, view_kwargs, controller_kwargs):
        self.model_class       = model_class
        self.view_class        = view_class
        self.controller_class  = controller_class
        self.model_kwargs      = model_kwargs
        self.view_kwargs       = view_kwargs
        self.controller_kwargs = controller_kwargs


class Router:
    """Top-level entry point. Builds and caches one MVC stack per registered path."""

    def __init__(self) -> None:
        self._routes: dict[str, Route]               = {}
        self._active: dict[str, BaseMainController]  = {}

    def register(
        self,
        path: str,
        model_class: type[BaseMainModel],
        view_class: type[BaseMainView],
        controller_class: type[BaseMainController],
        *,
        model_kwargs: dict[str, Any] | None = None,
        view_kwargs: dict[str, Any] | None = None,
        controller_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Register an MVC triple for *path*. Raises if already registered."""
        if path in self._routes:
            raise KeyError(f"Path '{path}' is already registered.")
        self._routes[path] = Route(
            model_class, view_class, controller_class,
            model_kwargs or {}, view_kwargs or {}, controller_kwargs or {},
        )

    def resolve(self, path: str) -> BaseMainController:
        """Return the cached controller for *path*, building the stack on first call."""
        if path not in self._routes:
            raise KeyError(f"No route registered for path '{path}'.")
        if path not in self._active or self._active[path].is_stopped():
            self._active[path] = self._build(self._routes[path])
        return self._active[path]

    def teardown(self, path: str) -> None:
        """Tear down the active stack for *path*."""
        if path in self._active:
            self._active.pop(path).teardown()

    def teardown_all(self) -> None:
        """Tear down all active stacks."""
        for path in list(self._active):
            self.teardown(path)

    def is_active(self, path: str) -> bool:
        """Return ``True`` if *path* has a live (non-stopped) controller instance."""
        ctrl = self._active.get(path)
        return ctrl is not None and not ctrl.is_stopped()

    def active_paths(self) -> list[str]:
        """Return all paths with a live (non-stopped) controller instance."""
        return [p for p, c in self._active.items() if not c.is_stopped()]

    def registered_paths(self) -> list[str]:
        """Return all registered paths (active or not)."""
        return list(self._routes.keys())

    @staticmethod
    def _build(route: Route) -> BaseMainController:
        """Construct a fresh ``EventBus → model → view → controller`` chain."""
        try:
            bus   = EventBus()
            model = route.model_class(bus, **route.model_kwargs)
            view  = route.view_class(model, bus, **route.view_kwargs)
            return route.controller_class(model, view, bus, **route.controller_kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to build route: {e}") from e
