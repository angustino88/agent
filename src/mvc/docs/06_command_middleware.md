# Command Pattern & Middleware

> Execute business operations as first-class objects with undo/redo support.
> Middleware intercepts every command for logging, validation, or auditing.

---

## Imports

```python
from mvc import Command, MacroCommand, Middleware, LoggingMiddleware, MiddlewarePipeline
```

---

## Defining a Command

Subclass `Command` and implement `execute()`. Optionally implement `undo()`
and set `can_undo()` to `True`.

```python
from mvc import Command

class InstallPackage(Command):
    description = "Install a Chocolatey package"

    def __init__(self, service, name: str, version: str | None = None) -> None:
        self._service = service
        self._name = name
        self._version = version

    def can_execute(self) -> bool:
        return self._name.strip() != ""

    def execute(self) -> dict:
        return self._service.install(self._name, self._version)

    def can_undo(self) -> bool:
        return True

    def undo(self) -> None:
        self._service.uninstall(self._name)
```

---

## Executing Commands

Commands are dispatched through `BaseMainModel` (or via the controller shortcut):

```python
class PackageController(BaseController):
    def _handle_install(self, name: str) -> None:
        cmd = InstallPackage(self.get(ChocoModel).service, name)
        result = self.execute(cmd)           # sync execution
        self.bus_emit("install.done", result)

    def _handle_install_background(self, name: str) -> None:
        cmd = InstallPackage(self.get(ChocoModel).service, name)
        self.execute_async(
            cmd,
            on_done=lambda r: self.bus_emit("install.done", r),
            on_error=lambda e: self.bus_emit("install.error", str(e)),
        )
```

### Guard — `can_execute()`

If `can_execute()` returns `False`, the command is skipped silently:

```python
class DeleteItem(Command):
    def __init__(self, items: list, index: int) -> None:
        self._items = items
        self._index = index

    def can_execute(self) -> bool:
        return 0 <= self._index < len(self._items)

    def execute(self) -> None:
        self._deleted = self._items.pop(self._index)

    def can_undo(self) -> bool:
        return True

    def undo(self) -> None:
        self._items.insert(self._index, self._deleted)
```

---

## Undo / Redo

The model tracks an undo and redo stack automatically:

```python
class AppController(BaseMainController):
    def _configure(self) -> None:
        self.bus_subscribe("edit.undo", lambda _: self._undo())
        self.bus_subscribe("edit.redo", lambda _: self._redo())

    def _undo(self) -> None:
        if self.model.can_undo:
            self.model.undo()
            self.bus_emit("history.changed")

    def _redo(self) -> None:
        if self.model.can_redo:
            self.model.redo()
            self.bus_emit("history.changed")
```

### Enable/disable UI buttons

```python
class ToolbarView(BaseView):
    def init(self) -> None:
        self.bus_subscribe("history.changed", self._update_buttons)

    def _update_buttons(self, _=None) -> None:
        self._btn_undo.setEnabled(self.model.can_undo)
        self._btn_redo.setEnabled(self.model.can_redo)
```

---

## MacroCommand — Atomic Batch

Execute multiple commands as one unit. If any fails, only the executed
ones are undone:

```python
from mvc import MacroCommand

class BulkInstall(MacroCommand):
    description = "Install multiple packages"

    def __init__(self, service, names: list[str]) -> None:
        cmds = [InstallPackage(service, n) for n in names]
        super().__init__(cmds)

# Undo reverses all in reverse order
bulk = BulkInstall(service, ["curl", "git", "wget"])
model.execute(bulk)
model.undo()  # uninstalls wget, git, curl
```

---

## Middleware

Middleware intercepts every `execute()` call. Use it for logging,
validation, authorization, or metrics.

### Built-in: LoggingMiddleware

```python
class AppModel(BaseMainModel):
    def _configure(self) -> None:
        self.add_middleware(LoggingMiddleware())
```

Output:

```
[CMD] Executing: InstallPackage — Install a Chocolatey package
[CMD] Success:   InstallPackage (0.342s)
```

### Custom Middleware

```python
from mvc import Middleware, Command

class AuthMiddleware(Middleware):
    """Block commands when user is not authenticated."""

    def __init__(self, auth_service) -> None:
        self._auth = auth_service

    def before(self, cmd: Command) -> bool:
        if not self._auth.is_logged_in():
            log.warning("Blocked %s — not authenticated", type(cmd).__name__)
            return False  # abort execution
        return True

    def after(self, cmd: Command, result, error) -> None:
        if error:
            log.error("Command %s failed: %s", type(cmd).__name__, error)

class MetricsMiddleware(Middleware):
    """Track command execution counts."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def before(self, cmd: Command) -> bool:
        return True

    def after(self, cmd: Command, result, error) -> None:
        name = type(cmd).__name__
        self._counts[name] = self._counts.get(name, 0) + 1
```

### Register middleware

```python
class AppModel(BaseMainModel):
    def _configure(self) -> None:
        self.add_middleware(AuthMiddleware(self.get(AuthModel)))
        self.add_middleware(LoggingMiddleware())
        self.add_middleware(MetricsMiddleware())
```

### Remove middleware

```python
self.remove_middleware(metrics)
```

---

## Middleware Execution Order

```
AuthMiddleware.before() → LoggingMiddleware.before() → cmd.execute()
                                                          │
LoggingMiddleware.after() ← AuthMiddleware.after() ← ─────┘
```

If any `before()` returns `False`, the chain stops and `execute()` is not called.

---

## API Reference

### `Command` (abstract)

| Method | Returns | Description |
|---|---|---|
| `execute()` | `Any` | Run the command |
| `undo()` | `None` | Reverse the command |
| `can_execute()` | `bool` | Guard check (default `True`) |
| `can_undo()` | `bool` | Undo support flag (default `False`) |

### `MacroCommand(commands: list[Command])`

Executes multiple commands atomically. Undo reverses only those that ran.

### `Middleware` (abstract)

| Method | Returns | Description |
|---|---|---|
| `before(cmd)` | `bool` | Return `False` to abort |
| `after(cmd, result, error)` | `None` | Post-execution hook |

### `BaseMainModel` — Command Methods

| Method | Returns | Description |
|---|---|---|
| `execute(cmd)` | `Any` | Sync execution through pipeline |
| `execute_async(cmd, on_done=None, on_error=None)` | `None` | Async execution |
| `undo()` | `bool` | Undo last command |
| `redo()` | `bool` | Redo last undone command |
| `can_undo` | `bool` | Property — undo stack not empty |
| `can_redo` | `bool` | Property — redo stack not empty |
| `clear_history()` | `None` | Discard undo/redo stacks |
| `add_middleware(m)` | `None` | Register middleware |
| `remove_middleware(m)` | `None` | Unregister middleware |
