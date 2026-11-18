import os
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize


class IconMixin:
    def __init__(self):
        self._icon_path = ""         # Directory for file-based icons
        self._resource_prefix = "icons"  # Qt resource prefix for resource-based icons

    def set_icon_path(self, path: str) -> None:
        """Set the directory for file-based icons."""
        self._icon_path = path

    def set_resource_prefix(self, prefix: str) -> None:
        """Set the Qt resource prefix for resource-based icons."""
        self._resource_prefix = prefix

    def get_icon(self, icon_name: str, from_resource: bool = True, icon_path: str = None, resource_prefix: str = None) -> QIcon:
        """Return a QIcon from resource or file."""
        icon_path = icon_path if icon_path is not None else self._icon_path
        resource_prefix = resource_prefix if resource_prefix is not None else self._resource_prefix
        if from_resource:
            return QIcon(f":/{resource_prefix}/{icon_name}")
        else:
            return QIcon(os.path.join(icon_path, icon_name))

    def set_window_icon(self, icon_name: str, from_resource: bool = True, icon_path: str = None, resource_prefix: str = None) -> None:
        """Set the window icon for self."""
        self.setWindowIcon(self.get_icon(icon_name, from_resource, icon_path, resource_prefix))

    def set_widget_icon(self, widget, icon_name: str, size: tuple[int, int] = None, from_resource: bool = True, icon_path: str = None, resource_prefix: str = None) -> None:
        """Set an icon for a widget (must support setIcon)."""
        if not hasattr(widget, 'setIcon'):
            raise TypeError(f"Object {widget} does not support setIcon()")
        widget.setIcon(self.get_icon(icon_name, from_resource, icon_path, resource_prefix))
        if size is not None and hasattr(widget, 'setIconSize'):
            if isinstance(size, (tuple, list)) and len(size) == 2:
                widget.setIconSize(QSize(*size))
            else:
                raise ValueError(f"Invalid size format: {size}")

    def set_icons_bulk(self, mappings: list[tuple], from_resource: bool = True, icon_path: str = None, resource_prefix: str = None) -> None:
        """
        Set icons for multiple widgets.
        mappings: list of (widget, icon_name, size)
        """
        for widget, icon_name, size in mappings:
            self.set_widget_icon(widget, icon_name, size, from_resource, icon_path, resource_prefix)

    def clear_widget_icon(self, widget) -> None:
        """Remove icon from widget if supported."""
        if hasattr(widget, 'setIcon'):
            widget.setIcon(QIcon())

    def has_icon(self, widget) -> bool:
        """Check if widget has an icon (if supported)."""
        if hasattr(widget, 'icon'):
            return not widget.icon().isNull()
        return False

    def get_widget_icon(self, widget) -> QIcon | None:
        """Get the QIcon from widget if supported."""
        if hasattr(widget, 'icon'):
            return widget.icon()
        return None
