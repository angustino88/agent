# Task Scheduling

> Declarative cron-like task scheduling built on Qt timers. Decorate methods
> with `@task` and assign a `Schedule` — the framework handles timing,
> thread dispatch, and health monitoring.

---

## Imports

```python
from mvc import task, Schedule, ScheduledTask, TaskRunner, TaskEngine
```

---

## Quick Start — `@task` Decorator

Mark any method in a `BaseController`, `BaseModel`, or `BaseView` subclass:

```python
from mvc import BaseController, task, Schedule

class MonitorController(BaseController):

    @task(schedule=Schedule(type="interval", every=30, unit="seconds"))
    def check_health(self) -> None:
        status = self.get(ServiceModel).ping()
        self.bus_emit("health.status", status)
```

The `TaskEngine` (mixed into every root component) automatically scans for
`@task`-decorated methods and registers them with the `TaskRunner`.

---

## Schedule Types

### Interval — repeat every N units

```python
Schedule(type="interval", every=5, unit="minutes")
Schedule(type="interval", every=30, unit="seconds")
Schedule(type="interval", every=2, unit="hours")
Schedule(type="interval", every=1, unit="days")
```

### Daily — run once per day at a specific time

```python
Schedule(type="daily", at="08:30")
Schedule(type="daily", at="23:00")
```

### Weekly — run on a specific weekday

```python
Schedule(type="weekly", weekday="monday", at="09:00")
Schedule(type="weekly", weekday="friday", at="17:30")
```

### Once — run at a specific datetime

```python
Schedule(type="once", datetime_str="2025-12-25T09:00:00")
```

With catch-up tolerance (default 60s):

```python
Schedule(type="once", datetime_str="2025-12-25T09:00:00", tolerance_sec=300)
```

### Cron — full cron syntax (requires `croniter`)

```python
Schedule(type="cron", cron="*/5 * * * *")     # every 5 minutes
Schedule(type="cron", cron="0 8 * * MON-FRI") # weekdays at 8am
Schedule(type="cron", cron="0 0 1 * *")       # first of every month
```

---

## Run at Startup

Add `run_at_start=True` to execute once immediately when the runner starts:

```python
@task(schedule=Schedule(type="interval", every=60, unit="seconds", run_at_start=True))
def sync_data(self) -> None:
    self.get(DataModel).sync()
```

---

## Heavy vs. Light Tasks

By default, tasks run on a thread pool (`heavy=True`). Set `heavy=False`
for quick tasks that can run on the Qt main thread:

```python
@task(
    schedule=Schedule(type="interval", every=1, unit="seconds"),
    heavy=False,  # runs on main thread — safe for UI updates
)
def update_clock(self) -> None:
    self._view._clock_label.setText(datetime.now().strftime("%H:%M:%S"))
```

---

## Custom Task ID

```python
@task(
    schedule=Schedule(type="interval", every=10, unit="minutes"),
    task_id="token-refresh",
)
def refresh_token(self) -> None:
    self.get(ServiceGatewayModel).refresh_token()
```

Retrieve by ID later:

```python
task = self.runner.get_task_by_id("token-refresh")
```

---

## Manual Task Registration

For tasks that aren't methods on MVC components:

```python
def standalone_cleanup():
    shutil.rmtree("/tmp/cache", ignore_errors=True)

sched_task = ScheduledTask(
    func=standalone_cleanup,
    schedule=Schedule(type="daily", at="03:00"),
    heavy=True,
    task_id="nightly-cleanup",
)

runner.add_task(sched_task)
```

---

## Task Lifecycle

```python
runner = self.runner  # available on any root component

runner.start()                           # start the timer
runner.stop()                            # stop all tasks

runner.add_task(scheduled_task)          # register dynamically
runner.remove_task(scheduled_task)       # unregister
runner.remove_task_by_id("my-task")     # unregister by ID
```

---

## Error Handling

Each `ScheduledTask` emits a Qt signal on exception:

```python
task = ScheduledTask(func=my_func, schedule=sched)
task.exception.connect(lambda e: log.error("Task failed: %s", e))
task.finished.connect(lambda: log.info("Task completed"))
```

---

## Health Monitoring

```python
report = runner.check_task_health()
# Returns:
# {
#     "token-refresh": {
#         "last_run": datetime(2025, 6, 20, 14, 30),
#         "last_success": datetime(2025, 6, 20, 14, 30),
#         "last_error": None,
#         "running": False,
#         "next_run": datetime(2025, 6, 20, 14, 40),
#     },
#     ...
# }
```

---

## Practical Example — Periodic Sync

```python
class SyncController(BaseController):

    @task(schedule=Schedule(
        type="interval", every=5, unit="minutes", run_at_start=True
    ))
    def sync_packages(self) -> None:
        """Fetch latest package list from server every 5 minutes."""
        packages = self.get(ServiceGatewayModel).fetch_packages()
        self.get(PackageModel).update(packages)
        self.bus_emit("sync.completed", len(packages))

    @task(schedule=Schedule(type="daily", at="02:00"), task_id="cleanup")
    def nightly_cleanup(self) -> None:
        """Run cache cleanup at 2 AM."""
        self.get(CacheModel).purge_expired()

    @task(schedule=Schedule(type="cron", cron="0 */6 * * *"))
    def check_updates(self) -> None:
        """Check for app updates every 6 hours."""
        update = self.get(UpdateModel).check()
        if update:
            self.bus_emit("update.available", update)
```

---

## API Reference

### `@task(schedule=None, heavy=True, task_id=None)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `schedule` | `Schedule \| None` | `None` | When/how often to run |
| `heavy` | `bool` | `True` | Run on thread pool (True) or main thread (False) |
| `task_id` | `str \| None` | `None` | Custom identifier |

### `Schedule` (dataclass)

| Field | Type | Default | Description |
|---|---|---|---|
| `type` | `ScheduleType` | — | `"interval"`, `"daily"`, `"weekly"`, `"once"`, `"cron"` |
| `every` | `int \| None` | `None` | For interval type |
| `unit` | `str \| None` | `None` | `"seconds"`, `"minutes"`, `"hours"`, `"days"` |
| `at` | `str \| None` | `None` | Time string `"HH:MM"` |
| `weekday` | `str \| None` | `None` | `"monday"` through `"sunday"` |
| `datetime_str` | `str \| None` | `None` | ISO format for `"once"` |
| `cron` | `str \| None` | `None` | Cron expression |
| `tolerance_sec` | `int` | `60` | Catch-up window for `"once"` |
| `run_at_start` | `bool` | `False` | Run immediately on start |

### `TaskRunner`

| Method | Returns | Description |
|---|---|---|
| `add_task(task)` | `ScheduledTask` | Register a task |
| `remove_task(task)` | `None` | Unregister |
| `remove_task_by_id(id)` | `None` | Unregister by ID |
| `get_task_by_id(id)` | `ScheduledTask \| None` | Lookup |
| `start()` | `None` | Start runner |
| `stop()` | `None` | Stop all tasks |
| `check_task_health()` | `dict` | Health report |
