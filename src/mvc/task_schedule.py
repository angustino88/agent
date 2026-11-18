import uuid
import croniter
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional, Literal, Callable
from PySide6.QtCore import QObject, Signal


class TaskState(str, Enum):
    """Celery-inspired task lifecycle states.

    Transitions::

        PENDING → STARTED → SUCCESS
                           → RETRY → STARTED  (retry loop)
                           → FAILURE
    """
    PENDING = 'PENDING'   # registered, waiting for next scheduled run
    STARTED = 'STARTED'   # currently executing
    SUCCESS = 'SUCCESS'   # last execution completed successfully
    FAILURE = 'FAILURE'   # permanently failed (retries exhausted or not configured)
    RETRY   = 'RETRY'     # failed, waiting to retry after backoff delay


def task(
    schedule=None,
    heavy: bool = True,
    task_id: Optional[str] = None,
    # ── Logging ──────────────────────────────────────────────
    log_level: str = "debug",
    timing: bool = True,
    silent: Optional[bool] = None,
    # ── Retry ────────────────────────────────────────────────
    max_retries: int = 0,
    retry_delay: float = 0.0,
    retry_backoff: bool = False,
    # ── Execution ────────────────────────────────────────────
    timeout: Optional[float] = None,
    priority: int = 0,
):
    """Celery-style task decorator.

    Marks a method as a managed task and attaches scheduling, retry, timeout,
    priority and logging metadata.  The ``TaskEngine`` scans controllers for
    decorated methods and registers them with the ``TaskRunner``.

    Args:
        schedule:       ``Schedule`` instance or ``None`` for a one-shot task.
        heavy:          Run in a background thread when ``True`` (default).
        task_id:        Human-readable task name (default: function name).
        log_level:      Python log level for start/completed messages.
        timing:         Include execution duration in log output.
        silent:         Suppress start/completed logs.
                        ``None`` = auto: verbose in dev, silent for periodic
                        tasks in production (frozen exe).
        max_retries:    Maximum automatic retry attempts on failure (0 = off).
        retry_delay:    Base delay in seconds before the first retry.
        retry_backoff:  Use exponential backoff (doubles delay each attempt).
        timeout:        Soft-timeout in seconds; logs a WARNING if exceeded.
        priority:       Dispatch priority — higher value runs first (default 0).

    Example::

        @task(
            schedule=Schedule(type="interval", every=1, unit="minutes"),
            max_retries=3,
            retry_delay=5.0,
            retry_backoff=True,
            timeout=30.0,
            priority=10,
        )
        def sync_data(self):
            ...
    """
    def decorator(func):
        func._is_task           = True
        func._task_schedule     = schedule
        func._task_heavy        = heavy
        func._task_id           = task_id or func.__name__
        func._task_log_level    = log_level
        func._task_log_timing   = timing
        func._task_log_silent   = silent
        func._task_max_retries  = max_retries
        func._task_retry_delay  = retry_delay
        func._task_retry_backoff = retry_backoff
        func._task_timeout      = timeout
        func._task_priority     = priority
        return func
    return decorator


ScheduleType = Literal["interval", "daily", "weekly", "once", "cron"]

@dataclass
class Schedule:
    type: ScheduleType
    every: Optional[int] = None         # For interval (e.g. 5 minutes)
    unit: Optional[str] = None          # "seconds", "minutes", "hours", "days"
    at: Optional[str] = None            # For daily/weekly: "08:30"
    weekday: Optional[str] = None       # For weekly: "monday"
    datetime_str: Optional[str] = None  # For once: "2025-12-25T09:00:00"
    cron: Optional[str] = None          # For cron syntax
    tolerance_sec: int = 60             # catch-up tolerance for "once"
    run_at_start: bool = False          # run once immediately on startup

    def next_run(self, last_run: Optional[datetime] = None) -> datetime:
        now = datetime.now()

        if self.type == "interval":
            delta = timedelta(**{self.unit: self.every})
            return (last_run or now) + delta

        elif self.type == "daily":
            hour, minute = map(int, self.at.split(":"))
            next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_time <= now:
                next_time += timedelta(days=1)
            return next_time

        elif self.type == "weekly":
            hour, minute = map(int, self.at.split(":"))
            days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
            target_idx = days.index(self.weekday.lower())
            current_idx = now.weekday()
            days_ahead = (target_idx - current_idx) % 7
            next_time = (now + timedelta(days=days_ahead)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            # If same weekday but time already passed, schedule for next week
            if next_time <= now:
                next_time += timedelta(weeks=1)
            return next_time

        elif self.type == "once":
            return datetime.fromisoformat(self.datetime_str)

        elif self.type == "cron":
            return croniter.croniter(self.cron, now).get_next(datetime)

        else:
            raise ValueError(f"Unknown schedule type: {self.type}")

class ScheduledTask(QObject):
    exception     = Signal(Exception)   # emitted on every uncaught exception
    finished      = Signal()            # emitted when a run (or final retry) completes
    state_changed = Signal(str)         # emitted with TaskState.value on transitions

    def __init__(
        self,
        func: Callable,
        schedule: Optional[Schedule] = None,
        heavy: bool = True,
        task_id: Optional[str] = None,
        # ── Logging ──────────────────────────────────────────────
        log_level: str = "debug",
        log_timing: bool = True,
        log_silent: Optional[bool] = None,
        # ── Retry ────────────────────────────────────────────────
        max_retries: int = 0,
        retry_delay: float = 0.0,
        retry_backoff: bool = False,
        # ── Execution ────────────────────────────────────────────
        timeout: Optional[float] = None,
        priority: int = 0,
    ):
        super().__init__()
        self.func     = func
        self.schedule = schedule
        self.heavy    = heavy

        # Identity
        self.task_id = task_id or str(uuid.uuid4())

        # Scheduling
        self.finished_flag = False
        self.next_run = (
            datetime.now()
            if (schedule and schedule.run_at_start)
            else (schedule.next_run() if schedule else None)
        )

        # State machine
        self.state:        TaskState          = TaskState.PENDING
        self.result:       Any                = None
        self.running:      bool               = False
        self.retries:      int                = 0
        self.last_run:     Optional[datetime] = None
        self.last_success: Optional[datetime] = None
        self.last_error:   Optional[Exception] = None

        # Logging
        self.log_level  = log_level
        self.log_timing = log_timing
        self.log_silent = log_silent

        # Retry
        self.max_retries    = max_retries
        self.retry_delay    = retry_delay
        self.retry_backoff  = retry_backoff

        # Execution
        self.timeout  = timeout
        self.priority = priority

    def _set_state(self, new_state: TaskState) -> None:
        """Transition to *new_state* and emit ``state_changed``."""
        self.state = new_state
        try:
            self.state_changed.emit(new_state.value)
        except Exception:
            pass

    def _retry_delay_for_attempt(self) -> float:
        """Return retry wait (seconds) for the current attempt.

        Called *after* incrementing ``self.retries``.
        With backoff: delay * 2^(attempt-1) — e.g. 5s → 5s, 10s, 20s.
        """
        if self.retry_backoff and self.retries > 0:
            return self.retry_delay * (2 ** (self.retries - 1))
        return self.retry_delay