"""Typed event definitions for compile-time safe event handling.

Replace fragile string-based event names with strongly-typed dataclasses::

    @dataclass(frozen=True, slots=True)
    class PackagesLoaded(Event):
        topic: ClassVar[str] = "choco.packages.loaded"
        packages: list[str] = field(default_factory=list)
        source: str = ""

Emit on the bus::

    bus.emit_event(PackagesLoaded(packages=["7zip"], source="api"))

Subscribe::

    bus.subscribe(PackagesLoaded.topic, self._on_packages_loaded)
    # handler receives the PackagesLoaded instance as payload

The ``Event`` base class is intentionally minimal — it just standardises
``topic`` and provides a ``__str__`` for debugging.  Freeze your subclasses
(``frozen=True``) to guarantee immutability during propagation.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import ClassVar


@dataclass(frozen=True)
class Event:
    """Base class for typed, immutable event payloads.

    Subclasses **must** define ``topic`` as a ``ClassVar[str]``.
    """

    topic: ClassVar[str] = ""

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.topic:
            raise TypeError(
                f"{cls.__name__} must define a non-empty `topic: ClassVar[str]`"
            )

    def __str__(self) -> str:
        field_strs = ", ".join(f"{f.name}={getattr(self, f.name)!r}" for f in fields(self))
        return f"{type(self).__name__}({field_strs})"
