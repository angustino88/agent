"""Custom Signal class with weak references, type checking, and async support."""
from __future__ import annotations

import asyncio
import inspect
import logging
import weakref
from contextlib import contextmanager
from typing import Any, Callable

_log = logging.getLogger(__name__)


class Signal:
    """Lightweight signal/slot mechanism independent of Qt.

    Features:
    * Optional argument type-checking (pass types to the constructor).
    * Weak references for bound methods (prevents reference cycles).
    * Async coroutine support when an event loop is running.
    * ``blocked()`` context manager to temporarily suppress emissions.
    """

    def __init__(self, *types: type) -> None:
        """Initialize with optional *types* for strict argument type-checking."""
        self._types: list[type] = list(types)
        self._slots: list[weakref.WeakMethod | Callable] = []
        self._blocked = False

    def __str__(self) -> str:
        return f"<Signal types={self._types}, slots={len(self._slots)}>"

    # ---- type validation ----------------------------------------------------

    def _type_check(self, args: tuple[Any, ...]) -> bool:
        if not self._types:
            return True
        if len(args) != len(self._types):
            caller = inspect.stack()[2].function
            raise TypeError(
                f"{caller}() expected {len(self._types)} arguments, got {len(args)}"
            )
        for arg, expected in zip(args, self._types):
            if not isinstance(arg, expected):
                caller = inspect.stack()[2].function
                raise TypeError(
                    f"{caller}() expected type {expected.__name__}, "
                    f"got {type(arg).__name__}"
                )
        return True

    # ---- connect / disconnect -----------------------------------------------

    def connect(self, slot: Callable) -> None:
        """Connect *slot* (uses a weak reference for bound methods)."""
        if not callable(slot):
            raise TypeError("Slot must be callable")
        if hasattr(slot, "__self__") and slot.__self__ is not None:
            self._slots.append(weakref.WeakMethod(slot))
        else:
            self._slots.append(slot)

    def disconnect(self, slot: Callable) -> None:
        """Disconnect *slot*."""
        for s in reversed(self._slots):
            target = s() if isinstance(s, weakref.WeakMethod) else s
            if target is slot:
                self._slots.remove(s)
                break

    def disconnect_all(self) -> None:
        """Disconnect all slots."""
        self._slots.clear()

    @property
    def slot_count(self) -> int:
        """Number of currently connected (alive) slots."""
        return sum(
            1 for s in self._slots
            if (s() if isinstance(s, weakref.WeakMethod) else s) is not None
        )

    # ---- blocking -----------------------------------------------------------

    @contextmanager
    def blocked(self):
        """Context manager that temporarily suppresses ``emit()``::

            with signal.blocked():
                widget.setText("...")  # connected slots won't fire
        """
        self._blocked = True
        try:
            yield
        finally:
            self._blocked = False

    # ---- emit ---------------------------------------------------------------

    def emit(self, *args: Any) -> None:
        """Emit the signal, calling all connected slots with *args*.

        Dead weak-references are pruned automatically on each emit.
        Suppressed when inside a ``blocked()`` context.
        """
        if self._blocked:
            return

        if not self._type_check(args):
            return

        alive: list[weakref.WeakMethod | Callable] = []
        for s in self._slots:
            target = s() if isinstance(s, weakref.WeakMethod) else s
            if target is None:
                continue  # weakref dead — skip and prune
            alive.append(s)
            try:
                result = target(*args)
                if result is not None:
                    try:
                        if asyncio.iscoroutine(result):
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                loop.create_task(result)
                    except RuntimeError:
                        pass
            except Exception as exc:
                _log.exception("Signal slot error in %r: %s", target, exc)
        self._slots = alive