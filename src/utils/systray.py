"""System tray icon wrapper for PySide6."""
from __future__ import annotations

from enum import Enum
from typing import Callable

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

class SystemTray:
    """Configurable Qt system-tray icon with context menu and activation handlers."""

    class IconActivateReason(Enum):
        TRIGGER      = QSystemTrayIcon.ActivationReason.Trigger
        DOUBLE_CLICK = QSystemTrayIcon.ActivationReason.DoubleClick
        MIDDLE_CLICK = QSystemTrayIcon.ActivationReason.MiddleClick

    def __init__(self) -> None:
        self._icon_path: str = ''
        self._tooltip: str = ''
        self._menu_actions: list[tuple[str, Callable]] = []
        self._icon_actions: dict[SystemTray.IconActivateReason, list[Callable]] = {
            self.IconActivateReason.TRIGGER: [],
            self.IconActivateReason.DOUBLE_CLICK: [],
            self.IconActivateReason.MIDDLE_CLICK: [],
        }
        self.tray: QSystemTrayIcon | None = None
        self.menu: QMenu | None = None
        self._action_objects: list[QAction] = []

    def set_icon(self, icon_path: str) -> None:
        self._icon_path = icon_path

    def set_tooltip(self, tooltip: str) -> None:
        self._tooltip = tooltip

    def add_menu_action(self, label: str, action: Callable) -> None:
        self._menu_actions.append((label, action))

    def add_icon_action(self, reason: IconActivateReason, action: Callable) -> None:
        if reason in self._icon_actions:
            self._icon_actions[reason].append(action)

    def show_message(self, title: str, message: str, icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information, timeout_ms: int = 5000) -> None:
        """Show a balloon / notification message (requires tray to be started)."""
        if self.tray:
            self.tray.showMessage(title, message, icon, timeout_ms)

    def _on_trayicon_activated(self, reason):
        for enum_reason, actions in self._icon_actions.items():
            if reason == enum_reason.value:
                for action in actions:
                    if callable(action):
                        action()

    def start(self) -> None:
        icon = QIcon(self._icon_path)
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(icon)
        self.tray.setVisible(True)
        self.tray.setToolTip(self._tooltip)
        self.tray.activated.connect(self._on_trayicon_activated)
        self.menu = QMenu()
        self._action_objects = []
        for label, action in self._menu_actions:
            act = QAction(str(label))
            self.menu.addAction(act)
            act.triggered.connect(action)
            self._action_objects.append(act)
        self.tray.setContextMenu(self.menu)

    def stop(self) -> None:
        """Hide and remove the system tray icon."""
        if self.tray:
            self.tray.setVisible(False)
            self.tray = None
