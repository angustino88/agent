# Typed Events

> Strongly-typed event objects built on frozen dataclasses. Each event
> carries a mandatory `topic` and typed payload fields, providing compile-time
> safety and self-documenting event contracts.

---

## Imports

```python
from mvc import Event, EventBus
```

---

## Defining a Typed Event

Every `Event` subclass **must** define a `topic` class variable. The framework
enforces this at class-definition time — a missing or empty `topic` raises
`TypeError`.

```python
from dataclasses import dataclass
from typing import ClassVar
from mvc import Event

@dataclass(frozen=True)
class PackagesChanged(Event):
    topic: ClassVar[str] = "packages.changed"
    packages: list[str]
    source: str = "unknown"

@dataclass(frozen=True)
class UserLoggedIn(Event):
    topic: ClassVar[str] = "user.logged_in"
    username: str
    role: str
```

### Invalid — will raise TypeError

```python
@dataclass(frozen=True)
class BadEvent(Event):
    topic: ClassVar[str] = ""    # ← empty string → TypeError

@dataclass(frozen=True)
class BadEvent2(Event):          # ← missing topic → TypeError
    data: str
```

---

## Emitting Typed Events

Use `emit_event()` on the bus. The topic is read from the event object:

```python
class PackageModel(BaseModel):
    def refresh(self) -> None:
        pkgs = self._fetch_packages()
        self.model.bus.emit_event(
            PackagesChanged(packages=pkgs, source="refresh")
        )
```

### Shortcut via BaseModel / BaseController / BaseView

Since `emit()` takes a string topic, use the bus directly for typed events:

```python
# In a sub-model / sub-controller / sub-view:
bus = self.model.bus          # from BaseModel
bus = self.controller.bus     # from BaseController
bus = self.view.bus           # from BaseMainView

bus.emit_event(PackagesChanged(packages=pkgs))
```

---

## Subscribing to Typed Events

Subscribe using the topic string — the handler receives the `Event` instance:

```python
class PackageView(BaseView):
    def init(self) -> None:
        self.bus_subscribe("packages.changed", self._on_packages)

    def _on_packages(self, event: PackagesChanged) -> None:
        self._list.clear()
        self._list.addItems(event.packages)
        self._status.setText(f"Source: {event.source}")
```

---

## String Representation

Events include a human-readable `__str__`:

```python
evt = PackagesChanged(packages=["curl", "git"], source="api")
print(evt)
# PackagesChanged(packages=['curl', 'git'], source='api')
```

---

## Frozen & Immutable

Events are frozen dataclasses — fields cannot be modified after creation:

```python
evt = UserLoggedIn(username="admin", role="superuser")
evt.username = "hacker"  # ← FrozenInstanceError
```

---

## Design Patterns

### Event catalog module

Keep all events in a single module for discoverability:

```python
# src/app/events.py
from dataclasses import dataclass
from typing import ClassVar
from mvc import Event

@dataclass(frozen=True)
class PackagesChanged(Event):
    topic: ClassVar[str] = "packages.changed"
    packages: list[str]

@dataclass(frozen=True)
class InstallRequested(Event):
    topic: ClassVar[str] = "install.requested"
    package_name: str
    version: str | None = None

@dataclass(frozen=True)
class ExportCompleted(Event):
    topic: ClassVar[str] = "export.completed"
    path: str
    row_count: int
```

### Wildcards with typed events

```python
# Subscribe to all package-related events
self.bus_subscribe("packages.*", self._on_package_event)

def _on_package_event(self, event: Event) -> None:
    log.info("Package event: %s", event)
```

---

## API Reference

### `Event` (base class)

| Attribute | Type | Description |
|---|---|---|
| `topic` | `ClassVar[str]` | **Required.** Event routing key |

### `EventBus.emit_event(event)`

| Parameter | Type | Description |
|---|---|---|
| `event` | `Event` | Typed event instance; `event.topic` is used as the event name |
