# EventBus

> Thread-safe publish/subscribe event bus shared across Model, View, and
> Controller layers. Supports priorities, wildcards, weak references,
> fire-and-forget async, collect, and request/response patterns.

---

## Imports

```python
from mvc import EventBus
```

All `BaseModel`, `BaseView`, and `BaseController` subclasses expose shortcut
methods (`emit`, `subscribe`, `subscribe_once`, `unsubscribe`) so you rarely
need to touch the `EventBus` instance directly.

---

## Basic Publish/Subscribe

### Subscribe

```python
class PackageView(BaseView):
    def init(self) -> None:
        self.bus_subscribe("packages.changed", self._on_packages)

    def _on_packages(self, packages: list[str]) -> None:
        self._list.clear()
        self._list.addItems(packages)
```

### Emit

```python
class PackageModel(BaseModel):
    def add(self, name: str) -> None:
        self._packages.append(name)
        self.bus_emit("packages.changed", self._packages)
```

### Unsubscribe

```python
self.unsubscribe("packages.changed", self._on_packages)
```

> Handlers subscribed via `subscribe()` are automatically tracked and
> removed during `teardown()` — no manual cleanup required.

---

## Subscribe Options

### Priority (lower number = runs first)

```python
# This handler runs before the default (priority=0) handlers
self.bus_subscribe("app.started", self._early_init, priority=-10)

# This handler runs after default handlers
self.bus_subscribe("app.started", self._late_setup, priority=50)
```

### Once (auto-unsubscribes after first call)

```python
self.bus_subscribe("app.ready", self._first_time_setup, once=True)
# or shorthand
self.bus_subscribe_once("app.ready", self._first_time_setup)
```

### Weak references (won't prevent garbage collection)

```python
self.bus_subscribe("data.updated", self._refresh, weak=True)
```

---

## Wildcard Patterns

Subscriber-side patterns use `fnmatch` syntax:

```python
# Catches "app.started", "app.stopped", "app.error", etc.
self.bus_subscribe("app.*", self._on_app_event)

# Catches all "model.X.changed" events
self.bus_subscribe("model.*.changed", self._on_any_change)
```

---

## Async Emit (fire-and-forget)

Dispatches the event on the internal thread pool. Returns a `Future`:

```python
future = self.controller.bus.emit_async("export.start", data)
# Optionally wait for completion
future.result(timeout=10)
```

---

## Collect Return Values

`emit_collect` calls all handlers and returns a list of their return values:

```python
# Each handler returns a validation result
results = self.controller.bus.emit_collect("validate.form", form_data)
errors = [r for r in results if r is not None]
```

---

## Request / Response

A synchronous request/response pattern built on top of the bus.

### Expose a getter (publisher side)

```python
class PackageController(BaseController):
    def init(self) -> None:
        self.expose_get("packages", lambda: self._model._packages)
```

### Query it (consumer side)

```python
packages = self.request("get:packages")
```

### Expose a setter

```python
class SettingsController(BaseController):
    def init(self) -> None:
        self.expose_set("theme", self._apply_theme)

    def _apply_theme(self, theme: str) -> None:
        self._view.set_theme(theme)
```

### Trigger a setter

```python
self.bus_emit("set:theme", "dark")
```

### Custom request/response with timeout

```python
# The subscriber receives a Future and must resolve it
self.bus_subscribe("compute.hash", self._handle_hash_request)

def _handle_hash_request(self, payload):
    future, data = payload
    result = hashlib.sha256(data).hexdigest()
    future.set_result(result)

# Caller side — blocks up to 5 seconds
digest = self.controller.bus.request("compute.hash", data, timeout=5.0)
```

---

## Error Handling

```python
class AppController(BaseMainController):
    def _configure(self) -> None:
        self.bus.set_error_handler(self._on_bus_error)

    def _on_bus_error(self, event: str, handler: Callable, exc: Exception) -> None:
        log.error("Event %s handler %s raised: %s", event, handler, exc)
```

---

## Recommended Data Flow

```
View ──emit("user.action")──► Controller ──emit("model.update")──► Model
 ▲                                                                      │
 └───────subscribe("model.changed", self._refresh)──────────────────────┘
```

- **View → Controller**: User actions (button clicks, input changes)
- **Controller → Model**: Business logic triggers
- **Model → View**: Data changes (via bus subscription)

---

## Introspection

```python
bus.events()                    # list of all registered event names
bus.subscriber_count("app.*")   # number of live subscribers
bus.clear()                     # remove all subscriptions
```

---

## API Reference

| Method | Returns | Description |
|---|---|---|
| `subscribe(event, handler, *, priority=0, once=False, weak=False)` | `None` | Register handler for event |
| `subscribe_once(event, handler, *, priority=0)` | `None` | Subscribe, auto-remove after first call |
| `unsubscribe(event, handler)` | `None` | Remove specific handler |
| `unsubscribe_all(event)` | `None` | Remove all handlers for event |
| `emit(event, payload=None)` | `None` | Synchronous dispatch |
| `emit_event(event)` | `None` | Emit a typed `Event` instance |
| `emit_async(event, payload=None)` | `Future` | Async dispatch on thread pool |
| `emit_collect(event, payload=None)` | `list[Any]` | Sync dispatch, collect returns |
| `request(event, payload=None, timeout=2.0)` | `Any` | Block until a handler resolves |
| `set_error_handler(handler)` | `None` | Global exception callback |
| `events()` | `list[str]` | All registered event names |
| `subscriber_count(event)` | `int` | Live subscriber count |
| `clear()` | `None` | Remove all subscriptions |
