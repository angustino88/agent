# Registry, IconMixin & UIDependency

> Component registry for typed lookups, icon management mixin, and
> parent→child widget enable/disable coordination.

---

## Imports

```python
from mvc import Registry, IconMixin, UIDependency
```

---

# Registry

Thread-safe typed component registry used internally by the framework.
Available for direct use when you need a shared lookup table.

## Basic Usage

```python
from mvc import Registry

registry = Registry()

# Register an object
config = ConfigService()
registry.register(config)

# Retrieve by type
cfg = registry.get(ConfigService)

# Check existence
registry.has(ConfigService)             # True
```

## Keyed Registration

Register multiple instances of the same type with different keys:

```python
registry.register(DatabaseService(host="primary"), key="primary")
registry.register(DatabaseService(host="replica"), key="replica")

primary = registry.get(DatabaseService, key="primary")
replica = registry.get(DatabaseService, key="replica")
```

## Get All Instances

```python
all_dbs = registry.get_all(DatabaseService)
# Returns: [primary_db, replica_db]
```

### Including subclasses

```python
class PostgresDB(DatabaseService): ...
class SQLiteDB(DatabaseService): ...

registry.register(PostgresDB())
registry.register(SQLiteDB())

# Only exact type
registry.get_all(DatabaseService)                          # []

# Include subclasses
registry.get_all(DatabaseService, subclasses=True)         # [postgres, sqlite]
```

## Update / Unregister

```python
# Replace existing (register raises on duplicate)
registry.register_or_update(new_config)

# Remove
registry.unregister(ConfigService)
```

## In the MVC Framework

The registry is available on every root component (`BaseMainModel`,
`BaseMainView`, `BaseMainController`). Sub-components access it via
the `get()` shortcut:

```python
class PackageController(BaseController):
    def init(self) -> None:
        config = self.get(ConfigModel)       # registry lookup
        gateway = self.get(ServiceGatewayModel)
```

---

# IconMixin

Mixin for managing QIcon loading from Qt resources or file paths.

## Setup

```python
from mvc import IconMixin

class AppView(BaseMainView, IconMixin):
    def __init__(self, model, bus) -> None:
        super().__init__(model, bus)
        IconMixin.__init__(self)

        # Set defaults
        self.set_resource_prefix(":/icons/")
        self.set_icon_path("assets/icons/")
```

## Window Icon

```python
self.set_window_icon("app_icon.png")

# From file instead of resource
self.set_window_icon("app_icon.png", from_resource=False)
```

## Widget Icons

```python
self.set_widget_icon(self._btn_install, "install.png")
self.set_widget_icon(self._btn_install, "install.png", size=(24, 24))
```

## Bulk Icon Assignment

```python
self.set_icons_bulk([
    (self._btn_install, "install.png", (24, 24)),
    (self._btn_remove,  "remove.png",  (24, 24)),
    (self._btn_refresh, "refresh.png", (24, 24)),
    (self._btn_settings, "settings.png", None),
])
```

## Get / Check Icons

```python
icon = self.get_icon("install.png")                # returns QIcon
icon = self.get_widget_icon(self._btn_install)     # QIcon or None
self.has_icon(self._btn_install)                    # True / False
```

## Clear Icon

```python
self.clear_widget_icon(self._btn_install)
```

---

# UIDependency

Manages parent→child widget enable/disable relationships. When a parent
is disabled, all registered children are disabled too.

## Setup

```python
from mvc import UIDependency

deps = UIDependency()
```

## Register Dependencies

```python
# When btn_connect is disabled, all children are disabled too
deps.register(
    parent=self._btn_connect,
    children=[
        self._btn_send,
        self._btn_disconnect,
        self._combo_channel,
    ],
)
```

## Enable / Disable

```python
# Disable btn_connect and all its children
deps.set_enabled(self._btn_connect, enabled=False)

# Re-enable
deps.set_enabled(self._btn_connect, enabled=True)

# Disable everything
deps.set_all_enabled(enabled=False)
```

## Dynamic Children

```python
deps.add_child(self._btn_connect, self._btn_monitor)
deps.remove_child(self._btn_connect, self._btn_monitor)
```

## Query

```python
children = deps.get_children(self._btn_connect)
self._btn_connect in deps                          # True
len(deps)                                           # number of parents
```

## Cleanup

```python
deps.unregister(self._btn_connect)  # remove one parent
deps.clear()                         # remove all
```

## Practical Example — Connection UI

```python
class ConnectionView(BaseView):
    def init(self) -> None:
        self._deps = UIDependency()

        # Register dependency groups
        self._deps.register(self._chk_enable, [
            self._btn_connect,
            self._combo_port,
            self._spin_baudrate,
        ])

        self._deps.register(self._btn_connect, [
            self._btn_send,
            self._btn_disconnect,
            self._txt_command,
        ])

        # Wire checkbox
        self._chk_enable.toggled.connect(
            lambda checked: self._deps.set_enabled(self._chk_enable, checked)
        )

        # Wire connect button
        self.bus_subscribe("connection.established", lambda _:
            self._deps.set_enabled(self._btn_connect, True))
        self.bus_subscribe("connection.lost", lambda _:
            self._deps.set_enabled(self._btn_connect, False))
```

---

## API Reference

### `Registry()`

| Method | Returns | Description |
|---|---|---|
| `register(obj, key=None)` | `None` | Register; raises on duplicate |
| `register_or_update(obj, key=None)` | `None` | Register or replace |
| `has(cls, key=None)` | `bool` | Check if registered |
| `get(cls, key=None)` | `T` | Retrieve instance; raises `LookupError` |
| `get_all(cls, *, subclasses=False)` | `list[T]` | All instances of type |
| `unregister(cls, key=None)` | `None` | Remove entry |
| `__len__()` | `int` | Number of entries |

### `IconMixin()`

| Method | Description |
|---|---|
| `set_icon_path(path)` | Set file-based icon directory |
| `set_resource_prefix(prefix)` | Set Qt resource prefix |
| `get_icon(name, from_resource=True)` | Return `QIcon` |
| `set_window_icon(name, from_resource=True)` | Set window icon |
| `set_widget_icon(widget, name, size=None)` | Set widget icon |
| `set_icons_bulk(mappings)` | Batch set icons |
| `clear_widget_icon(widget)` | Remove icon |
| `has_icon(widget)` | `bool` — has icon |
| `get_widget_icon(widget)` | `QIcon \| None` |

### `UIDependency()`

| Method | Returns | Description |
|---|---|---|
| `register(parent, children)` | `None` | Register parent→children |
| `unregister(parent)` | `None` | Remove parent entry |
| `add_child(parent, child)` | `None` | Add a child dynamically |
| `remove_child(parent, child)` | `None` | Remove a child |
| `get_children(parent)` | `list` | List children |
| `set_enabled(parent, enabled)` | `None` | Enable/disable children |
| `set_all_enabled(enabled)` | `None` | Enable/disable all |
| `clear()` | `None` | Remove all |
| `__contains__(parent)` | `bool` | Check registration |
| `__len__()` | `int` | Number of parents |
