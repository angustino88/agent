# BaseController & BaseMainController

> The **Controller** layer orchestrates communication between Model and View.
> `BaseMainController` is the composition root; `BaseController` is the
> base for every sub-controller handling a specific feature.

---

## Imports

```python
from mvc import BaseController, BaseMainController
```

---

## Architecture

```
BaseMainController  (root — one per route)
  ├── PackageController(BaseController)    ← feature logic
  ├── SettingsController(BaseController)   ← settings management
  └── ExportController(BaseController)     ← data export
```

- **`BaseMainController`** — owns the `Registry`, `TaskRunner`, and
  references the `EventBus`, `BaseMainModel`, and `BaseMainView`.
  Orchestrates teardown of the entire MVC stack.
- **`BaseController`** — lightweight sub-controller for a single feature.
  Listens to view events, manipulates models, and emits results.

---

## Root Controller — `BaseMainController`

### Minimal implementation

```python
from mvc import BaseMainController

class AppController(BaseMainController):

    def _setup(self) -> None:
        """Pass 1 — instantiate and register all sub-controllers."""
        self._make(PackageController)
        self._make(SettingsController)
        self._make(ExportController)

    def _configure(self) -> None:
        """Pass 3 — cross-cutting wiring (optional)."""
        self.bus.set_error_handler(
            lambda ev, handler, exc: log.error("Bus error: %s", exc)
        )
```

### Construction lifecycle

```
__init__(model, view, bus, max_workers=4)
  _setup()                         ← Pass 1: _make() every sub-controller
    sub.bind(model, view, self)    ← each sub gets model, view, root ctrl
    registry.register(sub)         ← each sub added to the registry

  for sub in subs:
    sub.init()                     ← Pass 2: all peers visible via get()

  _configure()                     ← Pass 3: application-level wiring
  runner.start()                   ← task runner begins polling
```

### `_make()` — create a sub-controller

```python
def _setup(self) -> None:
    self._make(PackageController)
    self._make(SettingsController)

    # Keyed registration (multiple instances of same type)
    self._make(ChartController, key="cpu")
    self._make(ChartController, key="memory")
```

### Direct access to Model and View

```python
self.model                      # BaseMainModel
self.view                       # BaseMainView
self.bus                        # EventBus
```

### Expose getter/setter APIs

```python
def _configure(self) -> None:
    self.expose_get("app.version", lambda: "2.1.0")
    self.expose_set("app.theme", self._apply_theme)
```

### Teardown cascade

Calling `teardown()` on the root controller cascades through the entire
MVC stack:

```
AppController.teardown()
  1. sub.teardown() for each sub-controller
  2. bus.clear()
  3. runner.stop()
  4. model.teardown()  → sub-models + hooks
  5. view.teardown()   → sub-views + hooks
```

---

## Sub-Controller — `BaseController`

### Minimal implementation

```python
from mvc import BaseController

class PackageController(BaseController):

    def init(self) -> None:
        """Called in Pass 2 — all siblings are accessible."""
        # Subscribe to view events
        self.bus_subscribe("install.requested", self._handle_install)
        self.bus_subscribe("search.input", self._handle_search)

        # Expose APIs for other components
        self.expose_get("packages", lambda: self.get(PackageModel)._packages)

    def _handle_install(self, name: str) -> None:
        result = self.get(PackageModel).install(name)
        self.bus_emit("install.completed", result)

    def _handle_search(self, query: str) -> None:
        results = self.get(PackageModel).search(query)
        self.bus_emit("search.results", results)
```

### Accessing all layers

```python
self.model           # → BaseMainModel
self.view            # → BaseMainView
self.controller      # → BaseMainController (root)
```

### Event flow pattern

The controller is the **mediator** between View and Model:

```
View                    Controller                Model
  │                         │                        │
  ├─emit("install.req")──► │                        │
  │                         ├─ get(PackageModel) ──► │
  │                         │  .install(name)        │
  │                         │ ◄── result ────────────┤
  │ ◄─emit("install.done")─┤                        │
  │                         │                        │
```

### Subscribe to events

```python
def init(self) -> None:
    self.bus_subscribe("user.login", self._on_login)
    self.bus_subscribe("user.logout", self._on_logout)
    self.bus_subscribe("data.*", self._on_any_data)           # wildcard
    self.bus_subscribe("startup", self._once, once=True)      # one-shot
    self.bus_subscribe_once("startup", self._once)             # shorthand
```

### Emit events

```python
self.bus_emit("install.completed", {"name": "curl", "success": True})
```

### Request/Response

```python
# Query data from another controller domain
packages = self.request("get:packages")

# With timeout
config = self.request("get:config.settings", timeout=5.0)
```

### Expose getter/setter

```python
def init(self) -> None:
    # Other components can call: self.request("get:packages")
    self.expose_get("packages", self._get_packages)

    # Other components can call: self.bus_emit("set:theme", "dark")
    self.expose_set("theme", self._set_theme)

def _get_packages(self) -> list[dict]:
    return self.get(PackageModel)._packages

def _set_theme(self, theme: str) -> None:
    self.get(ConfigModel).set_theme(theme)
    self.get(SettingsView).apply_theme(theme)
```

### Execute commands

```python
def _handle_install(self, name: str) -> None:
    # Sync execution through the model's command pipeline
    cmd = InstallCommand(self.get(PackageModel), name)
    result = self.execute(cmd)

    # Async execution (non-blocking)
    self.execute_async(
        cmd,
        on_done=lambda r: self.bus_emit("install.done", r),
        on_error=lambda e: self.bus_emit("install.error", str(e)),
    )
```

### Access siblings

```python
def init(self) -> None:
    pkg_ctrl = self.get(PackageController)
    settings_ctrl = self.get(SettingsController)
    all_ctrls = self.get_all(BaseController)
```

---

## Data Flow Summary

```
┌─────────────────────────────────────────────────────────┐
│                         Router                           │
│  builds: EventBus → Model → View → Controller            │
└──────────┬──────────────────────────────────┬────────────┘
           │                                  │
     ┌─────▼─────┐      ┌──────────┐    ┌─────▼─────┐
     │   Model    │◄────│Controller│────►│   View    │
     │            │     │          │     │           │
     │ • state    │     │ • logic  │     │ • UI      │
     │ • data     │     │ • flow   │     │ • display │
     │ • commands │     │ • expose │     │ • flash   │
     └────────────┘     └──────────┘     └───────────┘

  Direction:
    View ──emit("user.action")──► Controller
    Controller ──model.method()──► Model
    Model ──emit("data.changed")──► View (via bus subscription)
```

---

## Practical Example — Full Controller Layer

```python
# src/app/controller/main_controller.py
from mvc import BaseMainController

class AppController(BaseMainController):
    def _setup(self) -> None:
        self._make(PackageController)
        self._make(SettingsController)
        self._make(ConnectionController)

    def _configure(self) -> None:
        self.bus.set_error_handler(
            lambda ev, h, exc: log.error("Bus[%s]: %s", ev, exc)
        )


# src/app/controller/package_controller.py
from mvc import BaseController, slot_guard

class PackageController(BaseController):
    def init(self) -> None:
        self.bus_subscribe("install.requested", self._install)
        self.bus_subscribe("uninstall.requested", self._uninstall)
        self.bus_subscribe("search.input", self._search)
        self.expose_get("packages.list", self._get_packages)

    @slot_guard(error_msg="Install failed")
    def _install(self, name: str) -> None:
        model = self.get(PackageModel)
        result = model.install(name)
        self.bus_emit("install.completed", result)
        self.get(PackageView).flash(f"Installed {name}", "info")

    def _uninstall(self, name: str) -> None:
        self.get(PackageModel).uninstall(name)
        self.bus_emit("packages.changed", self._get_packages())

    def _search(self, query: str) -> None:
        results = self.get(PackageModel).search(query)
        self.bus_emit("search.results", results)

    def _get_packages(self) -> list[dict]:
        return self.get(PackageModel).packages


# src/app/controller/connection_controller.py
from mvc import BaseController, BaseThread, EHandle

class PingThread(BaseThread):
    def __init__(self, host: str) -> None:
        super().__init__(loop=True, interval=5.0, e_handle=EHandle.ALL)
        self._host = host

    def run_user(self) -> None:
        self.info.emit(f"Ping {self._host}: OK")

    def e_handler(self, e: Exception) -> None:
        self.exception.emit(e)


class ConnectionController(BaseController):
    def init(self) -> None:
        config = self.get(ConfigModel)
        self._ping = PingThread(config.server_host)
        self._ping.info.connect(lambda msg: self.bus_emit("connection.status", msg))
        self._ping.exception.connect(lambda e: self.bus_emit("connection.error", str(e)))

    def connect(self) -> None:
        self._ping.start()

    def disconnect(self) -> None:
        self._ping.kill()
```

---

## API Reference

### `BaseMainController(model, view, bus, max_workers=4)`

| Method / Property | Returns | Description |
|---|---|---|
| `model` | `BaseMainModel` | Root model reference |
| `view` | `BaseMainView` | Root view reference |
| `bus` | `EventBus` | Shared event bus |
| `_setup()` | — | **Abstract.** Pass 1 — create sub-controllers |
| `_configure()` | — | Pass 3 — optional wiring (default no-op) |
| `_make(cls, key=None)` | `T` | Instantiate, bind, register a sub-controller |
| `register(obj, key=None)` | `None` | Manual registry entry |
| `get(cls, key=None)` | `T` | Registry lookup |
| `get_all(cls)` | `list[T]` | All instances of type |
| `expose_get(key, getter)` | `None` | Respond to `get:{key}` requests |
| `expose_set(key, setter)` | `None` | Forward `set:{key}` events |
| `teardown()` | `None` | Cascade teardown (ctrl → bus → model → view) |

### `BaseController()`

| Method / Property | Returns | Description |
|---|---|---|
| `model` | `BaseMainModel` | Root model reference |
| `view` | `BaseMainView` | Root view reference |
| `controller` | `BaseMainController` | Root controller reference |
| `init()` | — | **Abstract.** Pass 2 initialization |
| `get(cls, key=None)` | `T` | Registry lookup |
| `get_all(cls)` | `list[T]` | All instances of type |
| `emit(event, payload=None)` | `None` | Emit via bus |
| `subscribe(event, handler, **opts)` | `None` | Subscribe to bus event |
| `subscribe_once(event, handler)` | `None` | One-shot subscribe |
| `unsubscribe(event, handler)` | `None` | Remove handler |
| `request(event, payload, timeout)` | `Any` | Bus request/response |
| `execute(cmd)` | `Any` | Sync command via model pipeline |
| `execute_async(cmd, **kw)` | `None` | Async command via model pipeline |
| `expose_get(key, getter)` | `None` | Respond to `get:{key}` requests |
| `expose_set(key, setter)` | `None` | Forward `set:{key}` events |
| `teardown()` | `None` | Unsubscribe all tracked handlers |
