from __future__ import annotations
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget


class UIDependency:
    """
    Manages UI dependencies between parent and child widgets or actions.
    Allows enabling/disabling groups of widgets/actions based on a parent.
    """
    def __init__(self):
        self._dependencies: dict[QWidget | QAction, list[QWidget | QAction]] = {}

    def register(self, parent: QWidget | QAction, children: list[QWidget | QAction]) -> None:
        """
        Register a parent widget/action and its dependent child widgets/actions.
        """
        if parent in children:
            raise ValueError("Parent cannot be in its own children list.")
        self._dependencies[parent] = list(children)

    def unregister(self, parent: QWidget | QAction) -> None:
        """Remove a parent and all its dependencies."""
        self._dependencies.pop(parent, None)

    def add_child(self, parent: QWidget | QAction, child: QWidget | QAction) -> None:
        """Add a child to a parent's dependency list."""
        if parent not in self._dependencies:
            self._dependencies[parent] = []
        if child not in self._dependencies[parent]:
            self._dependencies[parent].append(child)

    def remove_child(self, parent: QWidget | QAction, child: QWidget | QAction) -> None:
        """Remove a child from a parent's dependency list."""
        if parent in self._dependencies and child in self._dependencies[parent]:
            self._dependencies[parent].remove(child)

    def get_children(self, parent: QWidget | QAction) -> list[QWidget | QAction]:
        """Return the list of children for a parent."""
        return self._dependencies.get(parent, [])

    def set_enabled(self, parent: QWidget | QAction, enabled: bool) -> None:
        """
        Enable or disable all children of the given parent widget/action.
        """
        if parent not in self._dependencies:
            raise ValueError(f"{parent} not registered")
        for child in self._dependencies[parent]:
            if hasattr(child, 'setEnabled'):
                child.setEnabled(enabled)
            else:
                raise TypeError(f"Child {child} does not support setEnabled()")

    def set_all_enabled(self, enabled: bool) -> None:
        """Enable or disable all registered children for all parents."""
        for parent in self._dependencies:
            self.set_enabled(parent, enabled)

    def clear(self) -> None:
        """Remove all dependencies."""
        self._dependencies.clear()

    def __contains__(self, parent: QWidget | QAction) -> bool:
        return parent in self._dependencies

    def __len__(self) -> int:
        return len(self._dependencies)
