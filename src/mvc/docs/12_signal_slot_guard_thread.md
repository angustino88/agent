# Signal, SlotGuard & BaseThread

> Custom `Signal` class (non-Qt) with weak references and type checking,
> `@slot_guard` decorator for exception-safe Qt slots, and `BaseThread`
> for managed background work with pause/resume.

---

## Imports

```python
from mvc import Signal, slot_guard, BaseThread, EHandle
```

---

# Signal

A lightweight, non-Qt signal class with weak references, type checking,
and a `blocked()` context manager.

## Basic Usage

```python
from mvc import Signal

class DataProcessor:
    def __init__(self) -> None:
        self.progress = Signal(int)        # accepts one int argument
        self.completed = Signal()           # no arguments
        self.error = Signal(str, Exception) # two arguments

    def process(self, data: list) -> None:
        for i, item in enumerate(data):
            self._handle(item)
            self.progress.emit(i + 1)
        self.completed.emit()
```

## Connect / Disconnect

```python
processor = DataProcessor()

# Connect
processor.progress.connect(lambda pct: print(f"{pct}%"))
processor.completed.connect(self._on_done)

# Disconnect
processor.completed.disconnect(self._on_done)

# Disconnect all
processor.progress.disconnect_all()
```

## Type Checking

If types are specified, `emit()` validates arguments:

```python
sig = Signal(int, str)
sig.emit(42, "hello")     # ✓
sig.emit("bad", "hello")  # raises TypeError
```

## Weak References

Bound methods are stored as weak references — when the object is garbage
collected, the slot is automatically removed:

```python
class Listener:
    def on_progress(self, pct: int) -> None:
        print(pct)

listener = Listener()
processor.progress.connect(listener.on_progress)

del listener  # slot is automatically cleaned up
processor.progress.emit(50)  # no error, just skipped
```

## Blocked Context Manager

Temporarily suppress all emissions:

```python
with processor.progress.blocked():
    processor.process(data)  # no progress signals emitted
# Emissions resume normally here
```

## Slot Count

```python
processor.progress.slot_count    # number of connected slots
```

---

# @slot_guard

Decorator for PySide6 slot methods that catches exceptions and provides
configurable error handling.

## Basic Usage

```python
from mvc import slot_guard

class PackageView(BaseView):

    @slot_guard()
    def _on_install_clicked(self) -> None:
        name = self._input.text().strip()
        self.bus_emit("install.requested", name)
```

If `_on_install_clicked` raises, the exception is logged and the app
does **not** crash.

## Custom Error Message

```python
@slot_guard(error_msg="Failed to process installation")
def _on_install_clicked(self) -> None:
    ...
```

## Custom Logger

```python
@slot_guard(logger=my_logger)
def _on_save_clicked(self) -> None:
    ...
```

## Exception Callback

```python
def _handle_error(exc: Exception) -> None:
    show_error_dialog(str(exc))

@slot_guard(on_exception=_handle_error)
def _on_export_clicked(self) -> None:
    ...
```

## PySide6 Slot Type Hints

```python
@slot_guard(slot_args=[str, int])
def _on_item_selected(self, name: str, index: int) -> None:
    ...
```

## Reraise

```python
@slot_guard(reraise=True)
def _on_critical_action(self) -> None:
    ...  # exception is logged AND re-raised
```

---

# BaseThread

QThread subclass with built-in loop control, pause/resume, and configurable
exception handling.

## Basic Usage

```python
from mvc import BaseThread, EHandle

class DataFetcher(BaseThread):
    def run_user(self) -> None:
        data = self._fetch_data()
        self.info.emit(f"Fetched {len(data)} items")

    def e_handler(self, e: Exception) -> None:
        self.exception.emit(e)
```

## Signals

| Signal | Type | Description |
|---|---|---|
| `info` | `Signal(str)` | Status messages |
| `exception` | `Signal(Exception)` | Error reports |

## Looping Thread

```python
class PollingThread(BaseThread):
    def __init__(self) -> None:
        super().__init__(
            loop=True,         # repeat run_user() until killed
            interval=5.0,      # 5 seconds between iterations
            e_handle=EHandle.ALL,
        )

    def run_user(self) -> None:
        status = check_server_status()
        self.info.emit(f"Server: {status}")

    def e_handler(self, e: Exception) -> None:
        self.exception.emit(e)
```

## Exception Handling Modes

| Mode | Behavior |
|---|---|
| `EHandle.ALL` | Emit every exception via `exception` signal |
| `EHandle.IGNORE` | Silently ignore all exceptions |
| `EHandle.ONLY_E_CHANGE` | Only emit when exception message changes |

```python
# Only report new/different errors
thread = PollingThread()
thread = BaseThread(loop=True, interval=1.0, e_handle=EHandle.ONLY_E_CHANGE)
```

## Lifecycle Control

```python
thread = DataFetcher()

thread.start()              # start the thread
thread.has_started()        # True after start

thread.pause()              # pause execution
thread.has_paused()         # True while paused

thread.resume()             # resume from pause
thread.kill()               # request stop
```

## Connecting in a Controller

```python
class PackageController(BaseController):
    def init(self) -> None:
        self._fetcher = DataFetcher()
        self._fetcher.info.connect(self._on_info)
        self._fetcher.exception.connect(self._on_error)
        self._fetcher.finished.connect(self._on_done)

    def start_fetch(self) -> None:
        if not self._fetcher.has_started():
            self._fetcher.start()

    def _on_info(self, msg: str) -> None:
        self.bus_emit("fetch.progress", msg)

    def _on_error(self, e: Exception) -> None:
        self.bus_emit("fetch.error", str(e))

    def _on_done(self) -> None:
        self.bus_emit("fetch.completed")
```

---

# @log_events (Event Logger)

Class decorator that wraps specified Qt event methods for debug logging.

```python
from mvc import log_events

@log_events("mousePressEvent", "resizeEvent", "closeEvent")
class MainWindow(QMainWindow):
    ...
```

### Custom logger

```python
@log_events("paintEvent", logger=my_logger)
class Canvas(QWidget):
    ...

# Or via nested attribute path
@log_events("resizeEvent", logger_name="_view.logger")
class Panel(QWidget):
    ...
```

---

## API Reference

### `Signal(*types)`

| Method / Property | Returns | Description |
|---|---|---|
| `connect(slot)` | `None` | Connect a callable |
| `disconnect(slot)` | `None` | Disconnect a callable |
| `disconnect_all()` | `None` | Remove all connections |
| `emit(*args)` | `None` | Fire signal with args |
| `blocked()` | context manager | Suppress emissions |
| `slot_count` | `int` | Number of live connections |

### `@slot_guard(**kwargs)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `error_msg` | `str \| None` | `None` | Custom error message |
| `slot_args` | `list[type] \| None` | `None` | PySide6 Slot types |
| `on_exception` | `Callable \| None` | `None` | Exception callback |
| `logger` | `object \| None` | `None` | Logger instance |
| `reraise` | `bool` | `False` | Re-raise after logging |

### `BaseThread(loop=False, interval=0, e_handle=EHandle.ALL)`

| Method | Returns | Description |
|---|---|---|
| `run_user()` | `None` | **Abstract.** Main logic |
| `e_handler(e)` | `None` | **Abstract.** Handle exceptions |
| `start()` | `None` | Start the thread |
| `kill()` | `None` | Request stop |
| `pause()` | `None` | Pause execution |
| `resume()` | `None` | Resume from pause |
| `has_started()` | `bool` | Check if started |
| `has_paused()` | `bool` | Check if paused |

### `EHandle` (Enum)

`IGNORE`, `ALL`, `ONLY_E_CHANGE`
