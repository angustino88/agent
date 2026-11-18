# Observable Fields & Batch Updates

> Reactive field system in `BaseModel`. Automatically emits change events
> when fields are modified, with a `batch()` context manager to defer
> notifications until multiple changes are complete.

---

## Imports

```python
from mvc import BaseModel, BaseMainModel
```

---

## `set_field()` — Reactive Attribute Setter

Sets an attribute on the model and automatically emits a change event.
Returns `True` if the value actually changed.

```python
class ConfigModel(BaseModel):
    def init(self) -> None:
        self._theme = "dark"
        self._language = "en"

    def set_theme(self, theme: str) -> None:
        # Emits "ConfigModel.theme.changed" with value "light"
        changed = self.set_field("_theme", theme)
        if changed:
            log.info("Theme changed to %s", theme)
```

### Event naming convention

By default, `set_field("_name", value)` emits:

```
{ClassName}.name.changed
```

The leading underscore is stripped. Examples:
- `set_field("_theme", "dark")` → emits `"ConfigModel.theme.changed"`
- `set_field("_packages", [...])` → emits `"PackageModel.packages.changed"`
- `set_field("count", 42)` → emits `"MyModel.count.changed"`

### Custom event name

```python
# Override the auto-generated event name
self.set_field("_theme", "dark", event="settings.theme.updated")
```

### Force emit (even if value unchanged)

```python
self.set_field("_data", data, force=True)
```

---

## `notify()` — Emit Without Changing

Fire an event without modifying any attribute:

```python
class PackageModel(BaseModel):
    def refresh(self) -> None:
        self._packages = self._fetch_all()
        # Notify subscribers that packages were refreshed
        self.notify("packages", self._packages)
        # Emits "PackageModel.packages.changed"
```

### Custom event name

```python
self.notify("status", "ready", event="app.status.updated")
```

---

## `batch()` — Deferred Event Emission

Groups multiple field changes into one atomic update. All events are
**collected and deferred** until the `batch()` block exits, then emitted
in order.

### Problem: Without batch

```python
def update_settings(self, theme: str, lang: str, font_size: int) -> None:
    self.set_field("_theme", theme)          # emits immediately
    self.set_field("_language", lang)        # emits immediately
    self.set_field("_font_size", font_size)  # emits immediately
    # → 3 separate events, 3 UI refreshes
```

### Solution: With batch

```python
def update_settings(self, theme: str, lang: str, font_size: int) -> None:
    with self.batch():
        self.set_field("_theme", theme)          # deferred
        self.set_field("_language", lang)        # deferred
        self.set_field("_font_size", font_size)  # deferred
    # → all 3 events emitted here, in order
```

### Subscribing to batched changes

From the view or controller side, nothing changes — handlers fire normally,
just grouped together at the end of the batch:

```python
class SettingsView(BaseView):
    def init(self) -> None:
        self.bus_subscribe("ConfigModel.theme.changed", self._on_theme)
        self.bus_subscribe("ConfigModel.language.changed", self._on_lang)

    def _on_theme(self, theme: str) -> None:
        self._apply_theme(theme)

    def _on_lang(self, lang: str) -> None:
        self._apply_language(lang)
```

---

## Practical Example — Bulk Data Import

```python
class DataModel(BaseModel):
    def init(self) -> None:
        self._rows: list[dict] = []
        self._row_count = 0
        self._status = "idle"

    def import_csv(self, path: str) -> None:
        with self.batch():
            self.set_field("_status", "importing")
            rows = self._parse_csv(path)
            self.set_field("_rows", rows)
            self.set_field("_row_count", len(rows))
            self.set_field("_status", "ready")
        # All 4 events emitted here — view gets one coherent update
```

---

## Nested Batches

Batch contexts can nest. Events are only emitted when the **outermost**
batch exits:

```python
def complex_update(self) -> None:
    with self.batch():                        # outer
        self.set_field("_a", 1)
        with self.batch():                    # inner — no-op
            self.set_field("_b", 2)
            self.set_field("_c", 3)
        # inner exits — nothing emitted yet
        self.set_field("_d", 4)
    # outer exits — all 4 events emitted
```

---

## API Reference

### `BaseModel.set_field(name, value, *, event=None, force=False) -> bool`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | — | Attribute name (e.g. `"_theme"`) |
| `value` | `Any` | — | New value |
| `event` | `str \| None` | `None` | Custom event name (auto-generated if omitted) |
| `force` | `bool` | `False` | Emit even if value unchanged |

**Returns**: `True` if value changed (or `force=True`)

### `BaseModel.notify(field, value=None, *, event=None) -> None`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `field` | `str` | — | Field name (used to generate event name) |
| `value` | `Any` | `None` | Payload sent with the event |
| `event` | `str \| None` | `None` | Custom event name |

### `BaseModel.batch()` — Context Manager

No parameters. Returns a context manager that defers `emit()` calls until exit.
