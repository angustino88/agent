from __future__ import annotations
from abc import ABCMeta, abstractmethod
from typing import Any


class Command(metaclass=ABCMeta):
    """Unit of reversible work dispatched through ``BaseMainModel.execute()``.

    Subclass and implement ``execute()``.  Override ``undo()`` and return
    ``True`` from ``can_undo()`` for reversible commands.  The framework
    manages the undo / redo stacks and runs commands through the middleware
    pipeline automatically.

    Set ``description`` to a human-readable label for logging, UI display,
    and audit trails.
    """

    description: str = ""

    @abstractmethod
    def execute(self) -> Any:
        """Carry out the command; return a result if useful."""
        ...

    def undo(self) -> None:
        """Reverse the effect of ``execute()``.  Only called when ``can_undo()`` is ``True``."""
        raise NotImplementedError(f"{type(self).__name__} does not support undo")

    def can_undo(self) -> bool:
        """Return ``True`` if this command supports ``undo()``.  Default is ``False``."""
        return False

    def can_execute(self) -> bool:
        """Guard: return ``False`` to block execution without raising.  Default is ``True``."""
        return True


class MacroCommand(Command):
    """Execute multiple commands as one atomic, undoable group.

    Sub-commands run in order.  ``undo()`` reverses only those that
    successfully executed, in reverse order.  ``can_undo()`` is ``True``
    only when every sub-command supports undo.
    """

    def __init__(self, commands: list[Command]) -> None:
        self._commands = list(commands)
        self._executed: list[Command] = []   # track which ran (for safe undo)

    def execute(self) -> list[Any]:
        self._executed.clear()
        results: list[Any] = []
        for cmd in self._commands:
            if cmd.can_execute():
                results.append(cmd.execute())
                self._executed.append(cmd)
        return results

    def undo(self) -> None:
        for cmd in reversed(self._executed):
            cmd.undo()
        self._executed.clear()

    def can_undo(self) -> bool:
        return all(c.can_undo() for c in self._commands)

    def can_execute(self) -> bool:
        return any(c.can_execute() for c in self._commands)
