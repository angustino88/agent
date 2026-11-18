# State Machine

> Finite state machine with guarded transitions, entry/exit callbacks,
> and optional state history tracking.

---

## Imports

```python
from mvc import StateMachine
```

---

## Quick Start

```python
from mvc import StateMachine

sm = StateMachine("idle")

sm.add_transition("idle",       "loading")
sm.add_transition("loading",    "ready")
sm.add_transition("loading",    "error")
sm.add_transition("error",      "idle")
sm.add_transition("ready",      "idle")

sm.state                           # "idle"
sm.transition("loading")           # True
sm.state                           # "loading"
sm.transition("idle")              # False — not a valid transition
```

---

## Guards

A `guard` is a callable that returns `bool`. The transition is blocked if
the guard returns `False`:

```python
class ConnectionManager:
    def __init__(self) -> None:
        self._connected = False
        self._sm = StateMachine("disconnected")

        self._sm.add_transition(
            "disconnected", "connecting",
            guard=lambda: self._has_network(),
        )
        self._sm.add_transition("connecting", "connected")
        self._sm.add_transition("connecting", "error")
        self._sm.add_transition("connected", "disconnected")
        self._sm.add_transition("error", "disconnected")

    def _has_network(self) -> bool:
        return ping("8.8.8.8")

    def connect(self) -> bool:
        return self._sm.transition("connecting")
```

---

## Entry / Exit Callbacks

Run code when entering or leaving a state:

```python
sm = StateMachine("idle")

sm.add_transition(
    "idle", "loading",
    on_exit=lambda: log.info("Leaving idle"),
    on_enter=lambda: spinner.show(),
)

sm.add_transition(
    "loading", "ready",
    on_exit=lambda: spinner.hide(),
    on_enter=lambda: status.setText("Ready"),
)

sm.add_transition(
    "loading", "error",
    on_exit=lambda: spinner.hide(),
    on_enter=lambda: status.setText("Error — retry?"),
)
```

### Execution order

```
on_exit(from_state) → state changes → on_enter(to_state)
```

---

## History Tracking

Enable `track_history=True` to record every state visited:

```python
sm = StateMachine("idle", track_history=True)

sm.add_transition("idle", "loading")
sm.add_transition("loading", "ready")
sm.add_transition("ready", "idle")

sm.transition("loading")
sm.transition("ready")
sm.transition("idle")

sm.history  # ["idle", "loading", "ready", "idle"]
```

---

## Querying Transitions

```python
sm.valid_transitions()           # list of reachable states from current
sm.can_transition("loading")     # True / False (checks guard too)
```

---

## Reset

Return to initial state without firing callbacks:

```python
sm.reset()
sm.state     # "idle"
sm.history   # ["idle"] (reset if tracking)
```

---

## Practical Example — Package Installation Flow

```python
class InstallController(BaseController):
    def init(self) -> None:
        self._sm = StateMachine("idle", track_history=True)

        self._sm.add_transition("idle", "validating",
            on_enter=self._start_validation,
        )
        self._sm.add_transition("validating", "downloading",
            guard=lambda: self._validation_passed,
            on_enter=self._start_download,
        )
        self._sm.add_transition("validating", "error",
            on_enter=lambda: self.bus_emit("install.error", "Validation failed"),
        )
        self._sm.add_transition("downloading", "installing",
            on_enter=self._start_install,
        )
        self._sm.add_transition("downloading", "error",
            on_enter=lambda: self.bus_emit("install.error", "Download failed"),
        )
        self._sm.add_transition("installing", "completed",
            on_enter=lambda: self.bus_emit("install.completed"),
        )
        self._sm.add_transition("installing", "error",
            on_enter=lambda: self.bus_emit("install.error", "Install failed"),
        )
        self._sm.add_transition("completed", "idle")
        self._sm.add_transition("error", "idle")

        self.bus_subscribe("install.requested", self._on_install)

    def _on_install(self, package: str) -> None:
        self._package = package
        self._sm.transition("validating")

    def _start_validation(self) -> None:
        self._validation_passed = self.get(PackageModel).validate(self._package)
        if self._validation_passed:
            self._sm.transition("downloading")
        else:
            self._sm.transition("error")

    def _start_download(self) -> None:
        self.get(DownloadModel).download(self._package)
        self._sm.transition("installing")

    def _start_install(self) -> None:
        self.get(InstallerModel).install(self._package)
        self._sm.transition("completed")
```

---

## Integration with ViewState

Combine `StateMachine` with the view's `ViewState` for UI synchronization:

```python
class InstallView(BaseView):
    def init(self) -> None:
        self.bus_subscribe("install.started", lambda _: self.set_loading("Installing..."))
        self.bus_subscribe("install.completed", lambda _: self.set_ready())
        self.bus_subscribe("install.error", lambda msg: self.set_error(msg))
```

---

## API Reference

### `StateMachine(initial, *, track_history=False)`

| Method / Property | Returns | Description |
|---|---|---|
| `state` | `str` | Current state name |
| `history` | `list[str]` | Ordered states visited (if tracking enabled) |
| `add_transition(from_state, to_state, *, guard=None, on_exit=None, on_enter=None)` | `None` | Register allowed transition |
| `valid_transitions()` | `list[str]` | Reachable states from current |
| `can_transition(to_state)` | `bool` | Check if transition is valid (including guard) |
| `transition(to_state)` | `bool` | Attempt transition, returns success |
| `reset()` | `None` | Reset to initial state silently |
