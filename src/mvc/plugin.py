"""Plugin system for extending the MVC framework.

Plugins are self-contained extension units that participate in the framework
lifecycle.  Each plugin can register event handlers, middleware, services,
and components without modifying core code — the primary extensibility
mechanism of the framework.

Usage::

    class AnalyticsPlugin(Plugin):
        @property
        def name(self) -> str:
            return "analytics"

        def activate(self, ctx: PluginContext) -> None:
            ctx.bus.subscribe("command.done", self._track)

        def deactivate(self) -> None:
            pass

    manager = PluginManager(bus, registry)
    manager.register(AnalyticsPlugin())
    manager.activate_all()
"""
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Any

from .event_bus import EventBus
from .registry import Registry


class PluginContext:
    """Read-only facade passed to :pymethod:`Plugin.activate`.

    Provides controlled access to framework internals without
    exposing the full model/view/controller surface.
    """

    __slots__ = ("bus", "registry")

    def __init__(self, bus: EventBus, registry: Registry) -> None:
        self.bus = bus
        self.registry = registry


class Plugin(metaclass=ABCMeta):
    """Interface that every framework plugin must implement.

    *name* must be unique across the application.  *dependencies* lists
    plugin names that must be activated first.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin identifier."""
        ...

    @property
    def version(self) -> str:
        """Semantic version string (informational only)."""
        return "1.0.0"

    @property
    def dependencies(self) -> list[str]:
        """Names of plugins that must be activated before this one."""
        return []

    @abstractmethod
    def activate(self, ctx: PluginContext) -> None:
        """Called when the plugin is loaded.  Register handlers, middleware, etc."""
        ...

    def deactivate(self) -> None:
        """Called when the plugin is unloaded.  Clean up resources."""


class PluginManager:
    """Manages plugin registration, dependency resolution, and lifecycle."""

    def __init__(self, bus: EventBus, registry: Registry) -> None:
        self._bus = bus
        self._registry = registry
        self._plugins: dict[str, Plugin] = {}
        self._active: list[str] = []  # ordered by activation

    # ---- registration -------------------------------------------------------

    def register(self, plugin: Plugin) -> None:
        """Register a plugin.  Raises ``KeyError`` if already registered."""
        if plugin.name in self._plugins:
            raise KeyError(f"Plugin '{plugin.name}' is already registered.")
        self._plugins[plugin.name] = plugin

    # ---- activation ---------------------------------------------------------

    def activate(self, name: str) -> None:
        """Activate *name* and all its transitive dependencies."""
        if name in self._active:
            return
        plugin = self._plugins.get(name)
        if plugin is None:
            raise LookupError(f"Plugin '{name}' is not registered.")
        # Resolve dependencies first (topological)
        for dep in plugin.dependencies:
            if dep not in self._active:
                self.activate(dep)
        ctx = PluginContext(self._bus, self._registry)
        plugin.activate(ctx)
        self._active.append(name)
        self._bus.emit("plugin.activated", {"name": name, "version": plugin.version})

    def activate_all(self) -> None:
        """Activate every registered plugin (dependency order honoured)."""
        for name in self._plugins:
            self.activate(name)

    # ---- deactivation -------------------------------------------------------

    def deactivate(self, name: str) -> None:
        """Deactivate *name*.  Raises if other active plugins depend on it."""
        if name not in self._active:
            return
        # Guard: check reverse dependencies
        for other_name in self._active:
            if name in self._plugins[other_name].dependencies:
                raise RuntimeError(
                    f"Cannot deactivate '{name}': '{other_name}' depends on it."
                )
        self._plugins[name].deactivate()
        self._active.remove(name)
        self._bus.emit("plugin.deactivated", {"name": name})

    def deactivate_all(self) -> None:
        """Deactivate all plugins in reverse activation order."""
        for name in reversed(list(self._active)):
            try:
                self._plugins[name].deactivate()
            except Exception:
                pass
        self._active.clear()

    # ---- introspection ------------------------------------------------------

    def is_active(self, name: str) -> bool:
        return name in self._active

    @property
    def active_plugins(self) -> list[str]:
        """Activated plugin names in activation order."""
        return list(self._active)

    @property
    def registered_plugins(self) -> list[str]:
        return sorted(self._plugins.keys())

    def get(self, name: str) -> Plugin:
        """Return the Plugin instance for *name* (``LookupError`` if absent)."""
        if name not in self._plugins:
            raise LookupError(f"Plugin '{name}' is not registered.")
        return self._plugins[name]
