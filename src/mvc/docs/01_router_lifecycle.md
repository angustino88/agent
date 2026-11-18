# Router & Lifecycle

> Entry point for the MVC framework. The `Router` lazily builds and caches
> complete MVC stacks, while the `Lifecycle` mixin tracks component state.

---

## Imports

```python
from mvc import Router, Lifecycle, State
```

---

## Router

### Register a route

```python
from src.app.model.main_model   import AppModel
from src.app.view.main_view     import AppView
from src.app.controller.main_controller import AppController

router = Router()

router.register(
    "main",
    model_class      = AppModel,
    view_class       = AppView,
    controller_class = AppController,
)

# Optional keyword arguments forwarded to constructors
router.register(
    "settings",
    model_class      = SettingsModel,
    view_class       = SettingsView,
    controller_class = SettingsController,
    controller_kwargs = {"max_workers": 2},
)
```

### Resolve (build on first call, return cached)

```python
ctrl = router.resolve("main")       # builds EventBus → Model → View → Controller
ctrl = router.resolve("main")       # returns the same cached controller
```

### Query state

```python
router.is_active("main")            # True if controller exists and is not stopped
router.active_paths()               # ["main"]
router.registered_paths()           # ["main", "settings"]
```

### Teardown

```python
router.teardown("settings")         # tear down one route
router.teardown_all()               # tear down everything
```

### Build order (internal)

When `resolve()` is called for the first time, `Router._build()` constructs
the stack in strict order:

```
EventBus()
Model(bus)     → model._setup()  → sub.init() loop  → model._configure()
View(model, bus) → view._setup() → sub.init() loop  → view._configure()
Controller(model, view, bus) → ctrl._setup() → sub.init() → ctrl._configure()
```

---

## Lifecycle Mixin

Every `BaseModel`, `BaseView`, and `BaseController` inherits `Lifecycle`.

### States

| State | Meaning |
|---|---|
| `State.CREATED` | After `__init__()`, before `init()` |
| `State.INITIALIZED` | After `init()` completed |
| `State.RUNNING` | After `runner.start()` |
| `State.STOPPED` | After `teardown()` |
| `State.ERROR` | On fatal error |

### Check state

```python
obj.state                    # State.RUNNING
obj.is_running()             # True
obj.is_stopped()             # False
```

### Listen to state changes

```python
def on_state(state: State) -> None:
    if state == State.ERROR:
        logger.error("Component entered error state")

obj.on_state_change(on_state)
```

---

## Two-Pass Construction

Sub-components are built in two explicit passes to eliminate ordering
dependencies:

```
_setup()          ← Pass 1: _make() all sub-components (register only)
  _make(A)        register A in registry
  _make(B)        register B in registry

init loop         ← Pass 2: init every sub-component (all peers visible)
  A.init()        self.get(B) works here ✓
  B.init()        self.get(A) works here ✓

_configure()      ← Pass 3: root-level cross-cutting wiring
```

### Root controller example

```python
from mvc import BaseMainController

class AppController(BaseMainController):

    def _setup(self) -> None:               # Pass 1
        self._make(PackageController)
        self._make(SettingsController)

    def _configure(self) -> None:           # Pass 3
        self.bus.set_error_handler(
            lambda ev, handler, exc: log.error(exc)
        )
```

### Root model example

```python
from mvc import BaseMainModel

class AppModel(BaseMainModel):

    def _setup(self) -> None:
        self._make(ConfigModel)
        self._make(PackageModel)
        self._make_runtime_dirs("logs", "cache")

    def _configure(self) -> None:
        self.add_middleware(LoggingMiddleware())
```

### Root view example

```python
from mvc import BaseMainView

class AppView(BaseMainView):

    def _setup(self) -> None:
        self._make(SettingsView)
        self._make(PackageView)
```

---

## Teardown Cascade

Calling `ctrl.teardown()` cascades through the entire stack:

1. Every sub-controller `teardown()` — unsubscribes handlers
2. `bus.clear()` — removes remaining subscriptions
3. `runner.stop()` — stops the task runner
4. `model.teardown()` — tears down sub-models
5. `view.teardown()` — tears down sub-views

```python
# Teardown hooks run in registration order
model.on_teardown(lambda: db.close())
view.on_teardown(lambda: timer.stop())
```

---

## Full Application Entry Point

```python
import sys
from PySide6.QtWidgets import QApplication
from mvc import Router

app = QApplication(sys.argv)

router = Router()
router.register("main",
    model_class      = AppModel,
    view_class       = AppView,
    controller_class = AppController,
)

ctrl = router.resolve("main")
ctrl.view.show()

exit_code = app.exec()
router.teardown_all()
sys.exit(exit_code)
```

---

## API Reference

### `Router`

| Method | Returns | Description |
|---|---|---|
| `register(path, model_class, view_class, controller_class, **kwargs)` | `None` | Register an MVC triple |
| `resolve(path)` | `BaseMainController` | Build (once) and return cached controller |
| `teardown(path)` | `None` | Tear down one route |
| `teardown_all()` | `None` | Tear down all routes |
| `is_active(path)` | `bool` | Check if route has a live controller |
| `active_paths()` | `list[str]` | All paths with live controllers |
| `registered_paths()` | `list[str]` | All registered paths |

### `Lifecycle`

| Method / Property | Returns | Description |
|---|---|---|
| `state` | `State` | Current lifecycle state |
| `on_state_change(handler)` | `None` | Register a state change callback |
| `is_created()` | `bool` | `True` if not yet initialized |
| `is_initialized()` | `bool` | `True` if initialized but not running |
| `is_running()` | `bool` | `True` if running |
| `is_stopped()` | `bool` | `True` if stopped |
| `is_error()` | `bool` | `True` if in error state |
