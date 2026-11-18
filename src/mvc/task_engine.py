import inspect
from .task_schedule import ScheduledTask
from .task_runner import TaskRunner


class TaskEngine:
    def __init__(self, max_workers: int = 4):
        self.runner = TaskRunner(max_workers=max_workers)

    def register_task(self, obj):
        """Register a ``@task`` function or scan *obj* for all ``@task`` methods."""
        # Single task function
        if callable(obj) and getattr(obj, "_is_task", False):
            self._add_scheduled_task(obj)
            return

        # Controller: scan all methods
        for _, method in inspect.getmembers(obj, predicate=callable):
            if getattr(method, "_is_task", False):
                self._add_scheduled_task(method)

    def _add_scheduled_task(self, func):
        """Wrap *func* in a ``ScheduledTask`` and register it with the runner."""
        sched_task = ScheduledTask(
            func=func,
            schedule=getattr(func, "_task_schedule"),
            heavy=getattr(func, "_task_heavy"),
            task_id=getattr(func, "_task_id"),
            log_level=getattr(func, "_task_log_level", "debug"),
            log_timing=getattr(func, "_task_log_timing", True),
            log_silent=getattr(func, "_task_log_silent", None),
            max_retries=getattr(func, "_task_max_retries", 0),
            retry_delay=getattr(func, "_task_retry_delay", 0.0),
            retry_backoff=getattr(func, "_task_retry_backoff", False),
            timeout=getattr(func, "_task_timeout", None),
            priority=getattr(func, "_task_priority", 0),
        )
        self.runner.add_task(sched_task)