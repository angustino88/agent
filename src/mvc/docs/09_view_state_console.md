# ViewState, Flash & Console

> UI state management, transient notifications, and rich logging consoles.
> `ViewState` tracks whether a view is loading/ready/error, `flash()` sends
> brief messages, and `WidgetConsole` / `MessageBoxConsole` provide themed logging.

---

## Imports

```python
from mvc import BaseView, BaseMainView, ViewState, WidgetConsole, MessageBoxConsole
```

---

## ViewState

Every `BaseView` tracks a `ViewState` enum:

| State | Meaning | Typical UI |
|---|---|---|
| `ViewState.IDLE` | Default, no data loaded | Placeholder / instructions |
| `ViewState.LOADING` | Fetching or computing | Spinner, progress bar |
| `ViewState.READY` | Data available and valid | Normal content |
| `ViewState.ERROR` | Something went wrong | Error banner |
| `ViewState.EMPTY` | Data loaded but empty set | "No results" message |

### Setting state

```python
class PackageView(BaseView):
    def init(self) -> None:
        self.bus_subscribe("packages.loading", lambda _: self.set_loading("Fetching..."))
        self.bus_subscribe("packages.changed", self._on_packages)
        self.bus_subscribe("packages.error", lambda msg: self.set_error(msg))

    def _on_packages(self, packages: list[str]) -> None:
        if packages:
            self._list.clear()
            self._list.addItems(packages)
            self.set_ready(packages)
        else:
            self.set_empty("No packages found")
```

### Reading state

```python
if self.view_state == ViewState.LOADING:
    return  # skip update while loading
```

### State change events

Every `set_*` call emits a bus event:

```
"{ClassName}.state.changed"    payload = (ViewState, optional_payload)
```

```python
class AppController(BaseMainController):
    def _configure(self) -> None:
        self.bus_subscribe("PackageView.state.changed", self._on_view_state)

    def _on_view_state(self, payload) -> None:
        state, data = payload
        if state == ViewState.ERROR:
            log.error("Package view error: %s", data)
```

---

## Flash Messages

Send transient notifications from any view:

```python
class SettingsView(BaseView):
    def _on_save_clicked(self) -> None:
        self.get(ConfigModel).save()
        self.flash("Settings saved successfully", level="info")

    def _on_import_error(self, error: str) -> None:
        self.flash(f"Import failed: {error}", level="error")
```

Flash emits `"view.flash"` on the bus with `(message, level)`:

```python
class NotificationView(BaseView):
    def init(self) -> None:
        self.bus_subscribe("view.flash", self._show_notification)

    def _show_notification(self, payload) -> None:
        message, level = payload
        self._toast.show(message, icon=level, timeout=3000)
```

Levels: `"info"`, `"warning"`, `"error"`, `"debug"`

---

## WidgetConsole

Rich logging output in a `QPlainTextEdit` with color-coded log levels and
optional inline (live-updating) output.

### Setup

```python
from PySide6.QtWidgets import QPlainTextEdit
from mvc import WidgetConsole

console_widget = QPlainTextEdit()
console = WidgetConsole(
    widget=console_widget,
    theme="dark",              # "dark" or "light"
)
```

### Basic logging

```python
console.info("Application started")
console.warning("Token expires in 5 minutes")
console.error("Connection failed")
console.debug("Payload: %s", data)
console.exception("Unhandled error")
```

### Inline output (live progress)

```python
for i, pkg in enumerate(packages):
    console.info(f"Installing {pkg} ({i+1}/{len(packages)})...", inline=True)
    install(pkg)
console.info("All packages installed", inline=True, final=True)
```

`inline=True` overwrites the current line — useful for progress bars.
`final=True` commits the line and starts a new block.

### Custom theme colors

```python
import logging

console.set_level_color(logging.WARNING, "#FFA500")  # orange
console.set_theme("light")
```

### Default color maps

**Dark theme**:
| Level | Color |
|---|---|
| DEBUG | `#888888` |
| INFO | `#CCCCCC` |
| WARNING | `#FFD700` |
| ERROR | `#FF4444` |
| CRITICAL | `#FF0000` |

**Light theme**:
| Level | Color |
|---|---|
| DEBUG | `#666666` |
| INFO | `#333333` |
| WARNING | `#CC8800` |
| ERROR | `#CC0000` |
| CRITICAL | `#990000` |

### Clear console

```python
console.clear()
```

---

## MessageBoxConsole

Shows log messages as modal Qt message boxes. Useful for critical errors
or confirmations.

### Setup

```python
from mvc import MessageBoxConsole

msgbox = MessageBoxConsole(parent=main_window)
```

### Usage

```python
msgbox.info("Operation completed", title="Success")
msgbox.warning("Unsaved changes will be lost", title="Warning")
msgbox.error("Database connection failed", title="Error")
```

### Custom icon and blocking

```python
from PySide6.QtWidgets import QMessageBox

msgbox.log(
    "Are you sure?",
    level=logging.WARNING,
    title="Confirm",
    icon=QMessageBox.Question,
    block=True,      # modal
    parent=dialog,   # parent widget
)
```

---

## Practical Example — Console Integration

```python
class AppView(BaseMainView):
    def _setup(self) -> None:
        # Widget console for operation logs
        self._console = WidgetConsole(
            widget=self._ui.txt_console,
            theme="dark",
        )
        # Message box for critical errors
        self._msgbox = MessageBoxConsole(parent=self)

        self._make(PackageView)
        self._make(SettingsView)

    def _configure(self) -> None:
        self.bus_subscribe("view.flash", self._on_flash)
        self.bus_subscribe("app.critical", self._on_critical)

    def _on_flash(self, payload) -> None:
        msg, level = payload
        level_map = {"info": self._console.info, "warning": self._console.warning,
                     "error": self._console.error}
        level_map.get(level, self._console.info)(msg)

    def _on_critical(self, error: str) -> None:
        self._msgbox.error(error, title="Critical Error")
```

---

## API Reference

### `ViewState` (Enum)

`IDLE`, `LOADING`, `READY`, `ERROR`, `EMPTY`

### `BaseView` — State Methods

| Method | Description |
|---|---|
| `set_state(state, payload=None)` | Generic transition |
| `set_loading(message=None)` | → `LOADING` |
| `set_ready(payload=None)` | → `READY` |
| `set_error(message)` | → `ERROR` |
| `set_empty(message=None)` | → `EMPTY` |
| `view_state` | Property — current `ViewState` |
| `flash(message, level="info")` | Emit transient notification |

### `WidgetConsole(widget, logger=None, formatter=None, theme="dark", custom_colors=None)`

| Method | Description |
|---|---|
| `info(msg, **k)` | Log info message |
| `debug(msg, **k)` | Log debug message |
| `warning(msg, **k)` | Log warning message |
| `error(msg, **k)` | Log error message |
| `exception(msg, **k)` | Log exception with traceback |
| `log(msg, level, *, inline=False, final=False)` | Generic log |
| `clear()` | Clear all console text |
| `set_theme(theme)` | `"dark"` or `"light"` |
| `set_level_color(level, color)` | Custom hex color per level |

### `MessageBoxConsole(parent=None, logger=None, formatter=None)`

| Method | Description |
|---|---|
| `info(msg, title="Info")` | Info dialog |
| `warning(msg, title="Warning")` | Warning dialog |
| `error(msg, title="Error")` | Error dialog |
| `exception(msg, title="Exception")` | Exception dialog |
| `log(msg, level, title, icon=None, block=False)` | Generic dialog |
