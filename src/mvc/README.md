# MVC Module

Core Model-View-Controller framework for the application. All layers share a single `EventBus` instance and a typed `Registry`, coordinated through a strict two-pass construction lifecycle.

---

## 📦 Files

| File | Description |
|---|---|
| `base_model.py` | `BaseModel` / `BaseMainModel` — root and sub-model base classes |
| `base_view.py` | `BaseView` / `BaseMainView` — root and sub-view base classes |
| `base_controller.py` | `BaseController` / `BaseMainController` — root and sub-controller base classes |
| `event_bus.py` | Shared publish/subscribe event bus (priority, wildcards, weak refs, async, throttle, debounce) |
| `event.py` | `Event` frozen dataclass base for typed events |
| `lifecycle.py` | `Lifecycle` mixin + `State` enum (`CREATED → INITIALIZED → RUNNING → STOPPED`) |
| `registry.py` | Typed key-based component registry shared across all layers |
| `task_engine.py` | `TaskEngine` mixin — registers `@task`-decorated methods with the runner |
| `task_runner.py` | Thread-pool runner that executes scheduled tasks |
| `task_schedule.py` | `ScheduledTask` descriptor and `@task` decorator |
| `base_thread.py` | QThread subclass with loop control, pause/resume, exception handling |
| `router.py` | `Router` — registers named routes and lazily builds full MVC stacks |
| `signal.py` | Custom `Signal` with weak refs, type checking, `blocked()` context manager |
| `slot_guard.py` | `@slot_guard` decorator for exception-safe Qt slot methods |
| `state_machine.py` | Finite state machine with guards, entry/exit hooks, history |
| `command.py` | `Command` + `MacroCommand` for the command pattern with undo/redo |
| `middleware.py` | `Middleware` pipeline for command interception |
| `event_logger.py` | `@log_events` class decorator for Qt event logging |
| `console.py` | `WidgetConsole` + `MessageBoxConsole` with themed output |
| `icon.py` | `IconMixin` for QIcon management (resources and files) |
| `dependency.py` | `UIDependency` for parent→child widget enable/disable |
| `plugin.py` | `Plugin` / `PluginManager` / `PluginContext` — modular extension system |
| `service.py` | `ServiceContainer` — thread-safe lazy-singleton dependency injection |

---

## 📚 Feature Documentation

Detailed guides with examples for every framework feature:

| # | Guide | Covers |
|---|---|---|
| — | [**BaseModel**](docs/00_base_model.md) | `BaseModel`, `BaseMainModel` — state, data, commands, observable fields, batch |
| — | [**BaseView**](docs/00_base_view.md) | `BaseView`, `BaseMainView` — UI, ViewState, flash, bind_model |
| — | [**BaseController**](docs/00_base_controller.md) | `BaseController`, `BaseMainController` — orchestration, expose, execute |
| 01 | [Router & Lifecycle](docs/01_router_lifecycle.md) | `Router`, `Lifecycle`, `State`, two-pass construction, teardown |
| 02 | [EventBus](docs/02_event_bus.md) | Pub/sub, priorities, wildcards, async, collect, request/response |
| 03 | [Throttle & Debounce](docs/03_throttle_debounce.md) | `@throttle`, `@debounce` decorators |
| 04 | [Typed Events](docs/04_typed_events.md) | `Event` base class, `emit_event()`, topic enforcement |
| 05 | [Observable Fields](docs/05_observable_fields.md) | `set_field()`, `notify()`, `batch()` context manager |
| 06 | [Command & Middleware](docs/06_command_middleware.md) | `Command`, `MacroCommand`, undo/redo, `Middleware` pipeline |
| 07 | [Task Scheduling](docs/07_task_scheduling.md) | `@task`, `Schedule`, `TaskRunner`, cron/interval/daily/weekly |
| 08 | [State Machine](docs/08_state_machine.md) | `StateMachine`, guards, entry/exit hooks, history |
| 09 | [ViewState & Console](docs/09_view_state_console.md) | `ViewState`, `flash()`, `WidgetConsole`, `MessageBoxConsole` |
| 10 | [Plugin System](docs/10_plugin_system.md) | `Plugin`, `PluginManager`, `PluginContext`, dependencies |
| 11 | [Service Container](docs/11_service_container.md) | `ServiceContainer` DI with lazy singletons |
| 12 | [Signal, SlotGuard & Thread](docs/12_signal_slot_guard_thread.md) | `Signal`, `@slot_guard`, `BaseThread`, `@log_events` |
| 13 | [Registry, Icon & Dependency](docs/13_registry_icon_dependency.md) | `Registry`, `IconMixin`, `UIDependency` |

---

## 🏗️ Architecture

```
main.py
  router = Router()
  router.register("main", AppModel, AppView, AppController)
  ctrl = router.resolve("main")   # builds bus → model → view → controller
```

Every root class holds a reference to the same `bus` and its own `Registry`. Sub-components reach the bus via `self.model.bus`, `self.view.bus`, or `self.controller.bus`, with `emit` / `subscribe` shortcuts available directly on every base class.

---

## 🗺️ Router

`Router` is the top-level entry point. Instead of constructing `model → view → controller` manually in `main.py`, register named routes and let the router build and cache each full MVC stack lazily on first `resolve()`. Each route gets its own isolated `EventBus`.

```python
from mvc.router import Router

router = Router()

router.register(
    "main",
    model_class      = AppModel,
    view_class       = AppView,
    controller_class = AppController,
)

router.register(
    "settings",
    model_class      = SettingsModel,
    view_class       = SettingsView,
    controller_class = SettingsController,
    controller_kwargs = {"max_workers": 2},
)

# Lazily builds the stack on first call; returns cached controller thereafter
ctrl = router.resolve("main")

# Tear down one route (calls controller.teardown() which cascades)
router.teardown("settings")

# Tear down everything
router.teardown_all()
```

`_build()` always follows the required construction order:

```python
bus   = EventBus()
model = ModelClass(bus, **model_kwargs)
view  = ViewClass(model, bus, **view_kwargs)
ctrl  = ControllerClass(model, view, bus, **controller_kwargs)
```

---

## 🔄 Two-Pass Construction Lifecycle

Sub-components are created in two explicit passes to eliminate ordering dependencies in `init()`:

```
_setup()          ← Pass 1: _make() all sub-components (register only, no init)
  _make(A)        register A in registry
  _make(B)        register B in registry
  _make(C)        register C in registry

init loop         ← Pass 2: init every sub-component (all peers visible)
  A.init()        self.get(B) and self.get(C) work here ✓
  B.init()        self.get(A) and self.get(C) work here ✓
  C.init()        self.get(A) and self.get(B) work here ✓

_configure()      ← Pass 3: root-level cross-cutting wiring
runner.start()
```

| Phase | Method | Rule |
|---|---|---|
| **Pass 1** | `_setup()` calling `_make()` | Create, bind, register. No cross-component access. |
| **Pass 2** | `sub.init()` loop | Subscribe to events, call `self.get(Any)` freely. |
| **Pass 3** | `_configure()` | Application-level wiring after all sub-components are live. |

---

## 🚌 EventBus Integration

All three layers can emit and subscribe. The recommended data flow direction is:

```
View  ──emit("user.action")──►  Controller  ──emit("model.update")──►  Model
 ▲                                                                         │
 └──────────subscribe("model.changed", self._refresh)─────────────────────┘
```

### Subscribe options

```python
# Available on BaseController, BaseView, BaseModel
self.bus_subscribe("event.name", self._handler)               # basic
self.bus_subscribe("event.name", self._handler, priority=10)  # run before others
self.bus_subscribe("event.name", self._handler, once=True)    # auto-unsubscribes
self.bus_subscribe("event.name", self._handler, weak=True)    # won't prevent GC
self.bus_subscribe_once("event.name", self._handler)          # shorthand for once=True
self.unsubscribe("event.name", self._handler)

# Wildcards (fnmatch) on the subscriber side
self.bus_subscribe("app.*", self._handler)   # catches "app.started", "app.stopped", …

# Async emit
self.controller.bus.emit_async("event.name", payload)     # fire-and-forget

# Collect all return values
results = self.controller.bus.emit_collect("event.name", payload)
```

### Request / Response pattern

```python
# Publisher side — expose a value
self.expose_get("choco.packages", lambda: self._packages)

# Consumer side — query it (blocks up to timeout)
packages = self.request("get:choco.packages")

# Expose a setter
self.expose_set("choco.selected", lambda name: self._set_selected(name))
self.bus_emit("set:choco.selected", "curl")
```

Handlers registered via `subscribe()` are tracked automatically and removed in `teardown()` — no manual cleanup required.

---

## 🔧 Implementing a Sub-Component

### Sub-model

```python
from mvc.base_model import BaseModel

class PackageModel(BaseModel):
    def init(self) -> None:
        self._packages: list[str] = []
        # safe to call self.get(OtherModel) here — all peers registered

    def add(self, name: str) -> None:
        self._packages.append(name)
        self.bus_emit("packages.changed", self._packages)
```

### Sub-view

```python
from mvc.base_view import BaseView

class PackageView(BaseView):
    def init(self) -> None:
        self.bus_subscribe("packages.changed", self._refresh, weak=True)

    def _refresh(self, packages: list[str]) -> None:
        self._list.clear()
        self._list.addItems(packages)

    def _on_install_clicked(self) -> None:   # connected to QPushButton.clicked
        self.bus_emit("install.requested", self._input.text().strip())
```

### Sub-controller

```python
from mvc.base_controller import BaseController

class PackageController(BaseController):
    def init(self) -> None:
        self.bus_subscribe("install.requested", self._handle_install)
        self.expose_get("packages", lambda: self.get(PackageModel)._packages)

    def _handle_install(self, name: str) -> None:
        self.get(PackageModel).add(name)
```

### Root controller

```python
from mvc.base_controller import BaseMainController

class AppController(BaseMainController):
    def _setup(self) -> None:           # Pass 1 — register all
        self._make(PackageController)
        self._make(SettingsController)

    def _configure(self) -> None:       # Pass 3 — cross-cutting wiring
        self.bus.set_error_handler(lambda e, h, exc: log.error(exc))
```

---

## 🛑 Teardown

Calling `AppController.teardown()` cascades automatically:

1. `sub.teardown()` on every sub-controller — unsubscribes tracked handlers
2. `bus.clear()` — removes any remaining subscriptions
3. `runner.stop()` — stops the controller task runner
4. `model.teardown()` — stops sub-models and their runner
5. `view.teardown()` — stops sub-views and their runner

---

## 🗂️ Lifecycle States

```
CREATED → (after _make) → INITIALIZED → (after runner.start) → RUNNING → (after teardown) → STOPPED
```

Listen to state changes on any component:

```python
obj.on_state_change(lambda state: print(f"State: {state}"))
obj.is_running()   # True when state == RUNNING
```

---

## 👥 For Maintainers

- All new sub-components belong in `src/app/{model,view,controller}/`.
- Keep shared framework code here; do not add application-specific logic.
- Update this README when base classes or lifecycle rules change.
