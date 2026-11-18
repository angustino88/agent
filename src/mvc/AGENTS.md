# MVC Framework — AGENTS.md

Shared PySide6 MVC framework. Used as a git submodule across multiple projects.
This file guides agents working **inside** this submodule (extending or fixing the framework itself).

> **If you are working in a consumer project** (not this repo), read the consumer project's
> `.github/instructions/mvc-usage.instructions.md` instead.

---

## What this module is

A standalone MVC framework providing:
- `BaseController / BaseMainController` — orchestration, `execute(Command)`, sub-controller factory `_make()`
- `BaseModel / BaseMainModel` — state, observable fields, batch emit, command pipeline
- `BaseView / BaseMainView` — UI binding, `ViewState`, flash notifications
- `Router` — lazy MVC stack construction keyed by path string
- `EventBus` — pub/sub with priority, wildcards, weak refs, throttle/debounce
- `slot_guard` — exception-safe `@Slot` decorator
- `Lifecycle` + `State` — `CREATED → INITIALIZED → RUNNING → STOPPED` state machine
- `TaskEngine` / `TaskRunner` — background task scheduling
- `Command` / `MacroCommand` — command pattern with undo/redo
- `WidgetConsole` / `MessageBoxConsole` — themed output widgets

Full API docs in `docs/` subdirectory.

---

## Rules for modifying this module

- **No project-specific imports** — this module must remain generic and reusable.
- **No circular imports** — all base classes use `TYPE_CHECKING` guards for forward refs.
- **Backward compatibility** — this module is a shared submodule; breaking the public API breaks all consumer projects.
- Before adding a new public method, check if any existing consumer project uses the same name differently.
- New features must have a corresponding `docs/*.md` guide added or updated.
- All public methods must have docstrings.
- Use `TYPE_CHECKING` guards for all cross-class type hints to avoid circular imports.

## Two-pass construction (do not break)

```
Router.resolve(path)
  → _build(route)
      1. model  = ModelClass(**model_kwargs)         # __init__ only
      2. view   = ViewClass(**view_kwargs)            # __init__ only
      3. ctrl   = ControllerClass(**ctrl_kwargs)      # __init__ only
      4. ctrl.bind(model, view, bus)
      5. model.bind(ctrl)
      6. view.bind(ctrl)
      7. ctrl.init()   ← all wiring happens here, never in __init__
```

`__init__` must **never** reference sibling components. `init()` is the only place that may.

---

## File ownership

| File | Change carefully — impacts |
|---|---|
| `base_controller.py` | Every sub-controller in every consumer project |
| `base_model.py` | Every sub-model |
| `base_view.py` | Every sub-view |
| `router.py` | App startup / MVC stack lifecycle |
| `slot_guard.py` | Every Qt slot in every consumer project |
| `event_bus.py` | All inter-component communication |
| `lifecycle.py` | All teardown paths |
