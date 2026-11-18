# Throttle & Debounce Decorators

> Rate-limiting decorators for any callable. Thread-safe. Useful for
> controlling the frequency of event handlers, UI updates, or API calls.

---

## Imports

```python
from mvc import throttle, debounce
```

---

## `@throttle(interval)`

Ensures the decorated function executes **at most once** per `interval`
seconds. Excess calls within the interval are **silently dropped**.

```
Time →  0s    0.2s   0.4s   0.6s   0.8s   1.0s   1.2s
Call →  ✓      ✗      ✗      ✗      ✗      ✓      ✗
        │                                   │
        └── runs immediately                └── runs (1s elapsed)
```

### Example — Limit API calls

```python
from mvc import throttle

class ServiceGatewayModel(BaseModel):

    @throttle(2.0)  # at most one call every 2 seconds
    def refresh_token(self) -> None:
        response = self._http.post("/auth/refresh", ...)
        self._token = response.json()["token"]
```

### Example — Limit search-as-you-type

```python
class SearchController(BaseController):
    def init(self) -> None:
        self.bus_subscribe("search.input", self._on_search)

    @throttle(0.5)
    def _on_search(self, query: str) -> None:
        results = self.get(SearchModel).search(query)
        self.bus_emit("search.results", results)
```

---

## `@debounce(delay)`

Delays execution until `delay` seconds of **silence** after the last call.
Every new call **resets the timer**. Only the last call in a burst executes.

```
Time →  0s    0.1s   0.2s   0.3s  ···  0.8s
Call →  ○      ○      ○      ○          ✓
        │      │      │      │          │
        reset  reset  reset  reset      └── runs (0.5s silence)
```

### Example — Debounce window resize

```python
from mvc import debounce

class DashboardView(BaseView):

    @debounce(0.3)  # wait 300ms after last resize
    def _on_resize(self) -> None:
        self._chart.reflow()
        self._table.adjust_columns()
```

### Example — Debounce model save

```python
class ConfigModel(BaseModel):

    @debounce(1.0)  # save 1 second after last change
    def auto_save(self) -> None:
        self._write_to_disk()
        self.bus_emit("config.saved")

    def set_option(self, key: str, value: str) -> None:
        self._options[key] = value
        self.auto_save()  # multiple rapid calls → one save
```

---

## Combining with Event Subscriptions

```python
class PackageView(BaseView):
    def init(self) -> None:
        self.bus_subscribe("packages.changed", self._refresh_list)

    @throttle(0.5)
    def _refresh_list(self, packages: list[str]) -> None:
        """Even if the model emits rapidly, UI updates at most every 500ms."""
        self._list_widget.clear()
        self._list_widget.addItems(packages)
```

---

## Thread Safety

Both decorators use `threading.Lock` internally. Safe to call from any
thread, including Qt worker threads and `BaseThread` subclasses.

```python
class DataExporter(BaseThread):
    @throttle(5.0)
    def _report_progress(self, pct: int) -> None:
        self.info.emit(f"Export progress: {pct}%")
```

---

## Key Differences

| | `@throttle` | `@debounce` |
|---|---|---|
| **When it runs** | Immediately on first call | After silence period |
| **Excess calls** | Dropped | Reset the timer |
| **Best for** | Rate-limiting (API, UI refresh) | Waiting for user to stop typing |
| **Latency** | Zero on first call | Always delayed |

---

## API Reference

### `@throttle(interval: float)`

| Parameter | Type | Description |
|---|---|---|
| `interval` | `float` | Minimum seconds between executions |

### `@debounce(delay: float)`

| Parameter | Type | Description |
|---|---|---|
| `delay` | `float` | Seconds of silence before execution |
