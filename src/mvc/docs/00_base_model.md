# BaseModel & BaseMainModel

> The **Model** layer holds application state, business logic, and data
> access. `BaseMainModel` is the composition root; `BaseModel` is the
> base for every sub-model.

---

## Imports

```python
from mvc import BaseModel, BaseMainModel
```

---

## Architecture

```
BaseMainModel  (root — one per route)
  ├── ConfigModel(BaseModel)
  ├── PackageModel(BaseModel)
  └── ServiceGatewayModel(BaseModel)
```

- **`BaseMainModel`** — owns the `EventBus`, `Registry`, command pipeline,
  undo/redo stacks, and `TaskRunner`. Created by the `Router`.
- **`BaseModel`** — lightweight sub-model for a single domain concern.
  Accesses siblings via `self.get()`.

---

## Root Model — `BaseMainModel`

### Minimal implementation

```python
from mvc import BaseMainModel

class AppModel(BaseMainModel):

    def _setup(self) -> None:
        """Pass 1 — instantiate and register all sub-models."""
        self._make(ConfigModel)
        self._make(PackageModel)
        self._make(ServiceGatewayModel)

    def _configure(self) -> None:
        """Pass 3 — cross-cutting wiring (optional)."""
        self.add_middleware(LoggingMiddleware())
        self._make_runtime_dirs("logs", "cache", "export")
```

### Construction lifecycle

The `Router` calls the following sequence automatically:

```
__init__(bus, max_workers=4)
  _setup()                   ← Pass 1: _make() every sub-model
    sub.bind(self)           ← each sub receives a back-reference
    registry.register(sub)   ← each sub added to the registry

  for sub in subs:
    sub.init()               ← Pass 2: all peers visible via get()

  _configure()               ← Pass 3: application-level wiring
  runner.start()             ← task runner begins polling
```

### `_make()` — create a sub-model

```python
def _setup(self) -> None:
    self._make(ConfigModel)
    self._make(PackageModel)

    # Keyed registration (multiple instances of same type)
    self._make(DatabaseModel, key="primary")
    self._make(DatabaseModel, key="replica")
```

### `_make_runtime_dirs()` — create directories

```python
def _setup(self) -> None:
    self._make(ConfigModel)
    paths = self._make_runtime_dirs("logs", "cache")
    # paths = [Path("logs"), Path("cache")]  (created if absent)
```

### Command pipeline

```python
self.add_middleware(LoggingMiddleware())          # intercept commands
result = self.execute(MyCommand(...))            # sync execution
self.execute_async(MyCommand(...),               # async execution
    on_done=lambda r: ...,
    on_error=lambda e: ...,
)
```

### Undo / Redo

```python
self.execute(cmd)           # pushes to undo stack
self.undo()                 # pops and reverses
self.redo()                 # re-executes
self.can_undo               # bool property
self.can_redo               # bool property
self.clear_history()        # discard stacks
```

### Teardown hooks

```python
def _configure(self) -> None:
    self.on_teardown(lambda: self._db.close())
    self.on_teardown(lambda: self._cache.flush())
```

### Registry shortcuts

```python
self.register(my_service)                  # manual registration
config = self.get(ConfigModel)             # lookup by type
all_dbs = self.get_all(DatabaseModel)      # all instances of type
```

---

## Sub-Model — `BaseModel`

### Minimal implementation

```python
from mvc import BaseModel

class PackageModel(BaseModel):

    def init(self) -> None:
        """Called in Pass 2 — all siblings are accessible."""
        self._packages: list[dict] = []
        self._config = self.get(ConfigModel)

        self.bus_subscribe("refresh.requested", self._on_refresh)
```

### Accessing the root model and bus

```python
self.model           # → BaseMainModel instance
self.model.bus       # → EventBus instance
```

### Emit events

```python
def update(self, packages: list[dict]) -> None:
    self._packages = packages
    self.bus_emit("packages.changed", self._packages)
```

### Observable fields — `set_field()`

Automatically emits `"{ClassName}.{field}.changed"` when the value changes:

```python
class ConfigModel(BaseModel):
    def init(self) -> None:
        self._theme = "dark"
        self._language = "en"

    def set_theme(self, theme: str) -> None:
        self.set_field("_theme", theme)
        # Emits "ConfigModel.theme.changed" with value "dark"

    def set_language(self, lang: str) -> None:
        self.set_field("_language", lang, event="settings.lang.changed")
        # Emits custom event name instead
```

### Manual notification — `notify()`

Use after in-place mutations where `set_field` can't detect change:

```python
def add_package(self, pkg: dict) -> None:
    self._packages.append(pkg)
    self.notify("packages", self._packages)
    # Emits "PackageModel.packages.changed"
```

### Batch updates

Defer all events until the block exits:

```python
def bulk_update(self, theme: str, lang: str) -> None:
    with self.batch():
        self.set_field("_theme", theme)
        self.set_field("_language", lang)
    # Both events emitted here, in order
```

### Subscribe / Unsubscribe

```python
self.bus_subscribe("event.name", self._handler)
self.bus_subscribe("event.name", self._handler, priority=-10)
self.bus_subscribe("event.name", self._handler, once=True)
self.bus_subscribe("event.name", self._handler, weak=True)
self.bus_subscribe_once("event.name", self._handler)
self.unsubscribe("event.name", self._handler)
```

> All subscriptions are tracked and auto-unsubscribed on `teardown()`.

### Access siblings

```python
def init(self) -> None:
    config = self.get(ConfigModel)
    gateway = self.get(ServiceGatewayModel)
    all_models = self.get_all(BaseModel)   # all sub-models
```

---

## Practical Example — Full Model Layer

```python
# src/app/model/main_model.py
from mvc import BaseMainModel
from mvc import LoggingMiddleware

class AppModel(BaseMainModel):
    def _setup(self) -> None:
        self._make(ConfigModel)
        self._make(PackageModel)
        self._make(ServiceGatewayModel)
        self._make_runtime_dirs("logs", "cache", "export")

    def _configure(self) -> None:
        self.add_middleware(LoggingMiddleware())
        self.on_teardown(lambda: log.info("Model teardown complete"))


# src/app/model/config_model.py
from mvc import BaseModel

class ConfigModel(BaseModel):
    def init(self) -> None:
        self._settings = self._load_config()
        self._theme = self._settings.get("theme", "dark")

    @property
    def api_url(self) -> str:
        return self._settings["api_url"]

    def set_theme(self, theme: str) -> None:
        self.set_field("_theme", theme)


# src/app/model/package_model.py
from mvc import BaseModel

class PackageModel(BaseModel):
    def init(self) -> None:
        self._packages: list[dict] = []
        self.bus_subscribe("packages.fetch", self._fetch)

    def _fetch(self, _=None) -> None:
        gateway = self.get(ServiceGatewayModel)
        self._packages = gateway.fetch_packages()
        self.bus_emit("packages.changed", self._packages)
```

---

## API Reference

### `BaseMainModel(bus, max_workers=4)`

| Method / Property | Returns | Description |
|---|---|---|
| `bus` | `EventBus` | Shared event bus |
| `_setup()` | — | **Abstract.** Pass 1 — create sub-models |
| `_configure()` | — | Pass 3 — optional wiring (default no-op) |
| `_make(cls, key=None)` | `T` | Instantiate, bind, register a sub-model |
| `_make_runtime_dirs(*dirs)` | `list[Path]` | Create dirs if absent |
| `register(obj, key=None)` | `None` | Manual registry entry |
| `get(cls, key=None)` | `T` | Registry lookup |
| `get_all(cls)` | `list[T]` | All instances of type |
| `execute(cmd)` | `Any` | Sync command execution |
| `execute_async(cmd, on_done, on_error)` | `None` | Async command execution |
| `undo()` | `bool` | Undo last command |
| `redo()` | `bool` | Redo last undone |
| `can_undo` | `bool` | Undo stack not empty |
| `can_redo` | `bool` | Redo stack not empty |
| `clear_history()` | `None` | Discard stacks |
| `add_middleware(m)` | `None` | Register middleware |
| `remove_middleware(m)` | `None` | Unregister middleware |
| `on_teardown(hook)` | `None` | Register cleanup hook |
| `teardown()` | `None` | Cascade teardown |

### `BaseModel()`

| Method / Property | Returns | Description |
|---|---|---|
| `model` | `BaseMainModel` | Root model reference |
| `init()` | — | **Abstract.** Pass 2 initialization |
| `get(cls, key=None)` | `T` | Registry lookup |
| `get_all(cls)` | `list[T]` | All instances of type |
| `emit(event, payload=None)` | `None` | Emit via bus |
| `subscribe(event, handler, **opts)` | `None` | Subscribe to bus event |
| `subscribe_once(event, handler)` | `None` | One-shot subscribe |
| `unsubscribe(event, handler)` | `None` | Remove handler |
| `set_field(name, value, *, event, force)` | `bool` | Reactive setter |
| `notify(field, value, *, event)` | `None` | Manual event emit |
| `batch()` | context mgr | Defer event emissions |
| `teardown()` | `None` | Cleanup |
