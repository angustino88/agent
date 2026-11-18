"""Lightweight service container with lazy singleton creation.

Provides a thread-safe dependency injection container where services are
registered as factories and instantiated lazily on first ``get()``.  This
decouples component construction from component usage and makes the
framework easy to test (swap real services for mocks via ``register``).

Usage::

    services = ServiceContainer()

    # Register lazy factory
    services.register(HttpClient, lambda: HttpClient(base_url=cfg.api_url))

    # Or register a pre-built instance
    services.register_instance(EventBus, bus)

    # Anywhere later — singleton created once, reused
    client = services.get(HttpClient)
"""
from __future__ import annotations

import threading
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class ServiceContainer:
    """Thread-safe service locator / DI container with lazy singleton semantics."""

    def __init__(self) -> None:
        self._factories: dict[type, Callable[[], Any]] = {}
        self._instances: dict[type, Any] = {}
        self._lock = threading.Lock()

    # ---- registration -------------------------------------------------------

    def register(self, cls: type[T], factory: Callable[[], T]) -> None:
        """Register a *factory* for *cls*.  Instance is created on first ``get()``."""
        self._factories[cls] = factory

    def register_instance(self, cls: type[T], instance: T) -> None:
        """Register a pre-built *instance* for *cls*."""
        self._instances[cls] = instance

    # ---- resolution ---------------------------------------------------------

    def get(self, cls: type[T]) -> T:
        """Return the singleton for *cls*, creating it if needed (thread-safe)."""
        if cls in self._instances:
            return self._instances[cls]
        with self._lock:
            # Double-check after acquiring lock
            if cls in self._instances:
                return self._instances[cls]
            factory = self._factories.get(cls)
            if factory is None:
                raise LookupError(f"No service registered for {cls.__name__}")
            instance = factory()
            self._instances[cls] = instance
            return instance

    def get_optional(self, cls: type[T]) -> T | None:
        """Like ``get()`` but returns ``None`` instead of raising."""
        try:
            return self.get(cls)
        except LookupError:
            return None

    # ---- introspection ------------------------------------------------------

    def has(self, cls: type) -> bool:
        """Return ``True`` if *cls* is registered (factory or instance)."""
        return cls in self._instances or cls in self._factories

    # ---- lifecycle ----------------------------------------------------------

    def reset(self, cls: type | None = None) -> None:
        """Drop the cached instance for *cls* (recreated on next ``get()``).

        If *cls* is ``None``, reset **all** cached instances.
        """
        with self._lock:
            if cls is None:
                self._instances.clear()
            else:
                self._instances.pop(cls, None)

    def clear(self) -> None:
        """Remove all registrations and cached instances."""
        with self._lock:
            self._factories.clear()
            self._instances.clear()

    def __contains__(self, cls: type) -> bool:
        return self.has(cls)

    def __repr__(self) -> str:
        return (
            f"<ServiceContainer factories={len(self._factories)} "
            f"instances={len(self._instances)}>"
        )
