# Plugin System

> Modular extension mechanism. Plugins register with a `PluginManager`,
> declare dependencies, and receive a `PluginContext` with access to the
> shared `EventBus` and `Registry`.

---

## Imports

```python
from mvc import Plugin, PluginManager, PluginContext
```

---

## Defining a Plugin

Subclass `Plugin` and implement the required properties and `activate()`:

```python
from mvc import Plugin, PluginContext

class LoggingPlugin(Plugin):

    @property
    def name(self) -> str:
        return "logging"

    @property
    def version(self) -> str:
        return "1.0.0"

    def activate(self, ctx: PluginContext) -> None:
        ctx.bus.subscribe("*", self._log_event)

    def deactivate(self) -> None:
        pass  # cleanup if needed

    def _log_event(self, payload) -> None:
        print(f"Event: {payload}")
```

---

## Plugin Dependencies

Declare dependencies by name. The manager resolves the activation order
automatically:

```python
class DatabasePlugin(Plugin):
    @property
    def name(self) -> str:
        return "database"

    def activate(self, ctx: PluginContext) -> None:
        self._db = PostgresDB(...)
        ctx.registry.register(self._db)

    def deactivate(self) -> None:
        self._db.close()


class CachePlugin(Plugin):
    @property
    def name(self) -> str:
        return "cache"

    @property
    def dependencies(self) -> list[str]:
        return ["database"]  # activated after "database"

    def activate(self, ctx: PluginContext) -> None:
        db = ctx.registry.get(PostgresDB)
        self._cache = Cache(db)
        ctx.registry.register(self._cache)

    def deactivate(self) -> None:
        self._cache.flush()
```

---

## Using the PluginManager

### Registration & activation

```python
class AppController(BaseMainController):
    def _configure(self) -> None:
        manager = PluginManager(self.bus, self.model._registry)
        manager.register(LoggingPlugin())
        manager.register(DatabasePlugin())
        manager.register(CachePlugin())

        # Activate all — dependency order is resolved automatically
        manager.activate_all()
        # Activation order: database → cache → logging
```

### Selective activation

```python
manager.activate("database")   # activates deps first if needed
manager.activate("cache")      # "database" already active, just activates "cache"
```

### Deactivation

```python
manager.deactivate("cache")       # deactivate single plugin
manager.deactivate_all()           # deactivate all in reverse order
```

> Deactivation raises if other active plugins depend on the target.
> Use `deactivate_all()` for safe teardown.

---

## Bus Events

The `PluginManager` emits events on the shared bus:

| Event | Payload | When |
|---|---|---|
| `"plugin.activated"` | plugin name (`str`) | After successful activation |
| `"plugin.deactivated"` | plugin name (`str`) | After deactivation |

```python
self.bus_subscribe("plugin.activated", lambda name: log.info("Plugin loaded: %s", name))
```

---

## PluginContext

Plugins receive a `PluginContext` in `activate()` providing access to:

| Attribute | Type | Description |
|---|---|---|
| `bus` | `EventBus` | Shared event bus |
| `registry` | `Registry` | Shared component registry |

```python
class MetricsPlugin(Plugin):
    @property
    def name(self) -> str:
        return "metrics"

    def activate(self, ctx: PluginContext) -> None:
        # Subscribe to events
        ctx.bus.subscribe("install.completed", self._on_install)

        # Access registered components
        config = ctx.registry.get(ConfigModel)
        self._endpoint = config.metrics_url

    def deactivate(self) -> None:
        self._flush_metrics()
```

---

## Querying Plugin State

```python
manager.is_active("logging")          # True / False
manager.active_plugins                 # ["database", "cache", "logging"]
manager.registered_plugins             # all registered names
plugin = manager.get("logging")        # Plugin instance
```

---

## Circular Dependency Detection

The manager detects circular dependencies and raises `ValueError`:

```python
class A(Plugin):
    name = "a"
    dependencies = ["b"]

class B(Plugin):
    name = "b"
    dependencies = ["a"]

manager.register(A())
manager.register(B())
manager.activate_all()  # → ValueError: Circular dependency detected
```

---

## Practical Example — Feature Flag Plugin

```python
class FeatureFlagsPlugin(Plugin):
    @property
    def name(self) -> str:
        return "feature-flags"

    def activate(self, ctx: PluginContext) -> None:
        self._ctx = ctx
        self._flags: dict[str, bool] = {}

        # Expose flags via request/response
        ctx.bus.subscribe("get:feature-flags", self._handle_get)
        ctx.bus.subscribe("set:feature-flag", self._handle_set)

        # Load flags from config
        config = ctx.registry.get(ConfigModel)
        self._flags = config.get("feature_flags", {})

    def _handle_get(self, payload) -> None:
        future, _ = payload
        future.set_result(self._flags)

    def _handle_set(self, payload) -> None:
        name, enabled = payload
        self._flags[name] = enabled
        self._ctx.bus.emit("feature-flag.changed", (name, enabled))

    def deactivate(self) -> None:
        self._flags.clear()
```

Usage from a controller:

```python
flags = self.request("get:feature-flags")
if flags.get("dark-mode"):
    self.bus_emit("set:theme", "dark")
```

---

## API Reference

### `Plugin` (abstract)

| Property / Method | Returns | Description |
|---|---|---|
| `name` | `str` | **Required.** Unique identifier |
| `version` | `str` | Semantic version (default `"1.0.0"`) |
| `dependencies` | `list[str]` | Plugin names that must activate first (default `[]`) |
| `activate(ctx)` | `None` | **Required.** Called on load |
| `deactivate()` | `None` | Called on unload (default no-op) |

### `PluginManager(bus, registry)`

| Method | Returns | Description |
|---|---|---|
| `register(plugin)` | `None` | Register a plugin |
| `activate(name)` | `None` | Activate with dependency resolution |
| `activate_all()` | `None` | Activate all registered plugins |
| `deactivate(name)` | `None` | Deactivate single plugin |
| `deactivate_all()` | `None` | Deactivate all in reverse order |
| `is_active(name)` | `bool` | Check activation state |
| `active_plugins` | `list[str]` | Property — active names |
| `registered_plugins` | `list[str]` | Property — all registered names |
| `get(name)` | `Plugin` | Get plugin instance |
