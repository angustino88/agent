# BaseView & BaseMainView

> The **View** layer manages the user interface. `BaseMainView` is the
> composition root (typically inheriting `QMainWindow`); `BaseView` is
> the base for every sub-view (panels, tabs, dialogs).

---

## Imports

```python
from mvc import BaseView, BaseMainView, ViewState
```

---

## Architecture

```
BaseMainView  (root — one per route, usually QMainWindow)
  ├── PackageView(BaseView)      ← tab or panel
  ├── SettingsView(BaseView)     ← dialog or panel
  └── NotificationView(BaseView) ← overlay widget
```

- **`BaseMainView`** — owns the `Registry`, `TaskRunner`, and
  references the shared `EventBus` and `BaseMainModel`.
- **`BaseView`** — lightweight sub-view for a single UI concern.
  Accesses siblings via `self.get()` and reacts to model changes
  through bus subscriptions.

---

## Root View — `BaseMainView`

### Minimal implementation

```python
from PySide6.QtWidgets import QMainWindow
from mvc import BaseMainView

class AppView(BaseMainView, QMainWindow):

    def __init__(self, model, bus) -> None:
        QMainWindow.__init__(self)
        BaseMainView.__init__(self, model, bus)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the graphical layout (called from __init__)."""
        self.setWindowTitle("My Application")
        self.resize(1200, 800)

    def _setup(self) -> None:
        """Pass 1 — instantiate and register all sub-views."""
        self._make(PackageView)
        self._make(SettingsView)
        self._make(NotificationView)

    def _configure(self) -> None:
        """Pass 3 — cross-view wiring (optional)."""
        self.bus_subscribe("view.flash", self._on_flash)

    def _on_flash(self, payload) -> None:
        msg, level = payload
        self.get(NotificationView).show_toast(msg, level)
```

### Construction lifecycle

```
__init__(model, bus, max_workers=4)
  _setup()                   ← Pass 1: _make() every sub-view
    sub.bind(self, model)    ← each sub receives root view + model refs
    registry.register(sub)   ← each sub added to the registry

  for sub in subs:
    sub.init()               ← Pass 2: all peers visible via get()

  _configure()               ← Pass 3: cross-view wiring
  runner.start()             ← task runner begins polling
```

### `_make()` — create a sub-view

```python
def _setup(self) -> None:
    self._make(PackageView)
    self._make(SettingsView)

    # Keyed registration
    self._make(ChartView, key="cpu")
    self._make(ChartView, key="memory")
```

### Bus access

```python
self.bus                                    # EventBus
self.model                                  # BaseMainModel

# Request/response
packages = self.request("get:packages")
```

### Teardown hooks

```python
def _configure(self) -> None:
    self.on_teardown(lambda: self._save_window_geometry())
    self.on_teardown(lambda: self._timer.stop())
```

### Registry shortcuts

```python
pkg_view = self.get(PackageView)
all_views = self.get_all(BaseView)
self.register(custom_widget)
```

---

## Sub-View — `BaseView`

### Minimal implementation

```python
from PySide6.QtWidgets import QWidget
from mvc import BaseView

class PackageView(BaseView, QWidget):

    def __init__(self) -> None:
        QWidget.__init__(self)
        BaseView.__init__(self)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the widget layout."""
        self._list = QListWidget()
        self._btn_install = QPushButton("Install")
        # ... layout setup

    def init(self) -> None:
        """Called in Pass 2 — subscribe to events, access siblings."""
        self.bus_subscribe("packages.changed", self._on_packages)
        self._btn_install.clicked.connect(self._on_install_clicked)

    def _on_packages(self, packages: list[dict]) -> None:
        self._list.clear()
        for pkg in packages:
            self._list.addItem(pkg["name"])
        self.set_ready(packages)

    def _on_install_clicked(self) -> None:
        name = self._list.currentItem().text()
        self.bus_emit("install.requested", name)
```

### Accessing root view and model

```python
self.view            # → BaseMainView instance
self.model           # → BaseMainModel instance
self.view.bus        # → EventBus
```

### Subscribe to model events

```python
# Generic subscribe
self.bus_subscribe("packages.changed", self._refresh)

# Semantic alias for model events
self.bind_model("ConfigModel.theme.changed", self._on_theme)

# With options
self.bus_subscribe("data.loaded", self._show, priority=-10, once=True)
```

### Emit events (view → controller)

```python
def _on_button_clicked(self) -> None:
    self.bus_emit("install.requested", {"name": "curl", "version": "8.0"})
```

### Request/Response

```python
def _load_data(self) -> None:
    packages = self.request("get:packages")
    self._populate(packages)
```

---

## ViewState — Display State Tracking

Every sub-view tracks a `ViewState` that represents its current display
mode. State changes emit bus events for decoupled UI reactions.

### Setting state

```python
class PackageView(BaseView):
    def _on_fetch_start(self, _=None) -> None:
        self.set_loading("Fetching packages...")

    def _on_fetch_done(self, packages: list) -> None:
        if packages:
            self.set_ready(packages)
        else:
            self.set_empty("No packages found")

    def _on_fetch_error(self, error: str) -> None:
        self.set_error(error)
```

### Custom state transition

```python
self.set_state(ViewState.LOADING, "Please wait...")
```

### Reading state

```python
if self.view_state == ViewState.LOADING:
    return  # skip update
```

### Reacting to state changes (from other components)

```python
# In AppController or another view
self.bus_subscribe("PackageView.state.changed", self._on_pkg_state)

def _on_pkg_state(self, payload) -> None:
    state, data = payload
    if state == ViewState.LOADING:
        self._spinner.show()
    else:
        self._spinner.hide()
```

---

## Flash Messages

Send transient notifications from any view:

```python
self.flash("Settings saved", level="info")
self.flash("Invalid input", level="warning")
self.flash("Connection lost", level="error")
```

A central handler listens and displays them:

```python
# In the root view
def _configure(self) -> None:
    self.bus_subscribe("view.flash", self._show_toast)

def _show_toast(self, payload) -> None:
    message, level = payload
    self._toast_widget.show(message, level)
```

---

## Teardown

```python
class PackageView(BaseView):
    def init(self) -> None:
        self._timer = QTimer()
        self._timer.start(1000)
        self.on_teardown(lambda: self._timer.stop())
```

All subscriptions are automatically unsubscribed on `teardown()`.

---

## Practical Example — Full View Layer

```python
# src/app/view/main_view.py
from PySide6.QtWidgets import QMainWindow
from mvc import BaseMainView, WidgetConsole, MessageBoxConsole

class AppView(BaseMainView, QMainWindow):
    def __init__(self, model, bus) -> None:
        QMainWindow.__init__(self)
        BaseMainView.__init__(self, model, bus)
        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle("Package Manager")
        self._console = WidgetConsole(self._txt_log, theme="dark")
        self._msgbox = MessageBoxConsole(parent=self)

    def _setup(self) -> None:
        self._make(PackageView)
        self._make(SettingsView)

    def _configure(self) -> None:
        self.bus_subscribe("view.flash", self._on_flash)

    def _on_flash(self, payload) -> None:
        msg, level = payload
        getattr(self._console, level, self._console.info)(msg)


# src/app/view/package_view.py
from PySide6.QtWidgets import QWidget, QListWidget, QPushButton
from mvc import BaseView

class PackageView(BaseView, QWidget):
    def __init__(self) -> None:
        QWidget.__init__(self)
        BaseView.__init__(self)
        self._list = QListWidget()
        self._btn_install = QPushButton("Install")

    def init(self) -> None:
        self.bus_subscribe("packages.changed", self._refresh)
        self.bus_subscribe("packages.loading", lambda _: self.set_loading())
        self._btn_install.clicked.connect(self._on_install)

    def _refresh(self, packages: list[dict]) -> None:
        self._list.clear()
        self._list.addItems([p["name"] for p in packages])
        self.set_ready(packages) if packages else self.set_empty()

    def _on_install(self) -> None:
        if item := self._list.currentItem():
            self.bus_emit("install.requested", item.text())
```

---

## API Reference

### `BaseMainView(model, bus, max_workers=4)`

| Method / Property | Returns | Description |
|---|---|---|
| `model` | `BaseMainModel` | Root model reference |
| `bus` | `EventBus` | Shared event bus |
| `_setup()` | — | **Abstract.** Pass 1 — create sub-views |
| `_configure()` | — | Pass 3 — optional wiring (default no-op) |
| `_make(cls, key=None)` | `T` | Instantiate, bind, register a sub-view |
| `register(obj, key=None)` | `None` | Manual registry entry |
| `get(cls, key=None)` | `T` | Registry lookup |
| `get_all(cls)` | `list[T]` | All instances of type |
| `request(event, payload, timeout)` | `Any` | Bus request/response |
| `on_teardown(hook)` | `None` | Register cleanup hook |
| `teardown()` | `None` | Cascade teardown |

### `BaseView()`

| Method / Property | Returns | Description |
|---|---|---|
| `view` | `BaseMainView` | Root view reference |
| `model` | `BaseMainModel` | Root model reference |
| `view_state` | `ViewState` | Current display state |
| `init()` | — | **Abstract.** Pass 2 initialization |
| `get(cls, key=None)` | `T` | Registry lookup |
| `get_all(cls)` | `list[T]` | All instances of type |
| `emit(event, payload=None)` | `None` | Emit via bus |
| `subscribe(event, handler, **opts)` | `None` | Subscribe to bus event |
| `subscribe_once(event, handler)` | `None` | One-shot subscribe |
| `unsubscribe(event, handler)` | `None` | Remove handler |
| `bind_model(event, handler, *, once)` | `None` | Semantic alias for subscribe |
| `request(event, payload, timeout)` | `Any` | Bus request/response |
| `set_state(state, payload)` | `None` | Generic state transition |
| `set_loading(message=None)` | `None` | → `LOADING` |
| `set_ready(payload=None)` | `None` | → `READY` |
| `set_error(message)` | `None` | → `ERROR` |
| `set_empty(message=None)` | `None` | → `EMPTY` |
| `flash(message, level="info")` | `None` | Transient notification |
| `on_teardown(hook)` | `None` | Register cleanup hook |
| `teardown()` | `None` | Cleanup |

### `ViewState` (Enum)

`IDLE`, `LOADING`, `READY`, `ERROR`, `EMPTY`
