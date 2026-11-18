from datetime import datetime, timedelta
import time
import logging
import sys
import uuid
from PySide6.QtCore import QTimer, QObject
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from .task_schedule import ScheduledTask, TaskState


class TaskRunner(QObject):
    def __init__(
        self,
        max_workers: int = 4,
        tick_interval_ms: int = 50
    ):
        super().__init__()
        self._tasks = []
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._timer = QTimer()
        self._timer.timeout.connect(self._run)
        self._tick_interval = tick_interval_ms
        self._running = False
        self._logger = logging.getLogger('TaskRunner')

    def add_task(self, task: ScheduledTask) -> ScheduledTask:
        self._tasks.append(task)
        return task

    def remove_task(self, task: ScheduledTask):
        if task in self._tasks:
            self._tasks.remove(task)

    def remove_task_by_id(self, task_id: str):
        self._tasks = [t for t in self._tasks if t.task_id != task_id]

    def get_task_by_id(self, task_id: str) -> Optional[ScheduledTask]:
        for t in self._tasks:
            if t.task_id == task_id:
                return t
        return None

    def start(self):
        if not self._running:
            self._timer.start(self._tick_interval)
            self._running = True

    def stop(self):
        if self._running:
            self._timer.stop()
            self._running = False
            self._executor.shutdown(wait=False)

    def check_task_health(self):
        health_report = {}
        now = datetime.now()
        for task in self._tasks:
            overdue = False
            if task.schedule and task.schedule.type != "once":
                overdue = now > task.next_run + timedelta(seconds=getattr(task.schedule, "tolerance_sec", 0))

            health_report[task.task_id] = {
                "func_name":   task.func.__name__,
                "state":       task.state.value,
                "running":     task.running,
                "retries":     task.retries,
                "priority":    task.priority,
                "last_run":    task.last_run,
                "last_success": task.last_success,
                "last_error":  task.last_error,
                "overdue":     overdue,
                "next_run":    task.next_run,
            }
        return health_report

    # ─── Logger resolution ────────────────────────────────────────────────
    def _resolve_logger(self, func) -> logging.Logger:
        """Prefer the central system_logger; fall back to instance or module logger."""
        system_logger = logging.getLogger('system_logger')
        if getattr(system_logger, 'handlers', None):
            return system_logger
        try:
            if hasattr(func, '__self__') and func.__self__ is not None:
                inst_logger = getattr(func.__self__, '_logger', None)
                if inst_logger is not None:
                    return inst_logger
        except Exception:
            pass
        return logging.getLogger(getattr(func, '__module__', None) or 'tasks')

    # ─── Silence decision ─────────────────────────────────────────────────
    @staticmethod
    def _is_silent(task: ScheduledTask) -> bool:
        """Suppress start/completed messages for periodic tasks in production."""
        explicit = getattr(task, 'log_silent', None)
        if explicit is not None:
            return explicit
        # Production (frozen exe): silence periodic tasks
        if getattr(sys, 'frozen', False):
            return bool(task.schedule and getattr(task.schedule, 'type', None) != 'once')
        # Development: verbose by default
        return False

    # ─── Task log helpers ─────────────────────────────────────────────
    @staticmethod
    def _task_label(task: ScheduledTask) -> str:
        """Return the bracketed task tag ``[Task:func_name]``.  

        The tag is used as a consistent prefix so every log line for a given
        task can be filtered by category.

        Example::

            [Task:refresh_physical_device_state]
        """
        name = getattr(task.func, '__name__', repr(task.func))
        return f"[Task:{name}]"

    @staticmethod
    def _level_num(task: ScheduledTask) -> int:
        """Return the numeric log level configured on the task."""
        try:
            return getattr(logging, getattr(task, 'log_level', 'debug').upper())
        except Exception:
            return logging.DEBUG

    # ─── Schedule advancement ─────────────────────────────────────────────
    def _advance_next_run(self, task: ScheduledTask) -> None:
        """Move to the next scheduled run or mark one-shot tasks finished."""
        if task.schedule is None or task.schedule.type == 'once':
            task.finished_flag = True
        else:
            task.next_run = task.schedule.next_run(last_run=task.last_run or datetime.now())

    # ─── Core task execution ──────────────────────────────────────────────
    def _run_task(self, task: ScheduledTask) -> None:
        # Prevent double-dispatch: mark running in the main thread before
        # handing off to the thread pool.
        task.running = True

        # Resolve log context once in the main thread so the closure can use it.
        label     = self._task_label(task)
        logger    = self._resolve_logger(task.func)
        level_num = self._level_num(task)
        silent    = self._is_silent(task)

        # Unique per-execution ID — ties RECEIVED → SUCCEEDED/FAILED together
        run_id    = uuid.uuid4().hex[:8]
        run_label = f"{label}[{run_id}]"

        # ── "received" logged in the main thread ────────────────────────
        if not silent:
            try:
                logger.log(level_num, f"{run_label} received")
            except Exception:
                pass

        def wrapper():
            # ── STARTED ───────────────────────────────────────────────────
            task._set_state(TaskState.STARTED)
            task.last_run = datetime.now()
            t_start = time.perf_counter()

            try:
                task.result     = task.func()
                task.last_success = datetime.now()
                task.last_error   = None
                task.retries      = 0
                dur_s = time.perf_counter() - t_start

                # Soft-timeout warning (task still succeeded, but took too long)
                if task.timeout and dur_s > task.timeout:
                    try:
                        logger.warning(
                            f"{run_label}  SOFT-TIMEOUT  duration={dur_s:.3f}s  limit={task.timeout}s"
                        )
                    except Exception:
                        pass

                # ── SUCCESS ───────────────────────────────────────────────
                task._set_state(TaskState.SUCCESS)
                if not silent:
                    try:
                        if task.result is not None:
                            logger.log(level_num,
                                f"{run_label} succeeded in {dur_s:.3f}s  result={task.result!r}"
                            )
                        else:
                            logger.log(level_num,
                                f"{run_label} succeeded in {dur_s:.3f}s"
                            )
                    except Exception:
                        pass

                self._advance_next_run(task)

            except Exception as exc:
                task.last_error = exc
                dur_s = time.perf_counter() - t_start

                try:
                    task.exception.emit(exc)
                except Exception:
                    pass

                if task.retries < task.max_retries:
                    # ── RETRY ─────────────────────────────────────────────
                    task.retries += 1
                    delay         = task._retry_delay_for_attempt()
                    task.next_run = datetime.now() + timedelta(seconds=delay)
                    task._set_state(TaskState.RETRY)
                    try:
                        logger.warning(
                            f"{run_label}  RETRY"
                            f"  attempt={task.retries}/{task.max_retries}  in={delay:.1f}s  error={exc!r}"
                        )
                    except Exception:
                        pass

                else:
                    # ── FAILURE ───────────────────────────────────────────
                    task._set_state(TaskState.FAILURE)
                    try:
                        logger.error(f"{run_label}  FAILED  error={exc!r}")
                        logger.debug(f"{run_label}  Traceback:", exc_info=True)
                    except Exception:
                        pass

                    if task.schedule is None or task.schedule.type == 'once':
                        task.finished_flag = True
                    else:
                        # Periodic task: advance schedule despite failure
                        self._advance_next_run(task)

            finally:
                task.running = False
                try:
                    task.finished.emit()
                except Exception:
                    pass

        if task.heavy:
            future = self._executor.submit(wrapper)
            def callback(fut):
                try:
                    fut.result()
                except Exception as e:
                    try:
                        task.exception.emit(e)
                    except Exception:
                        pass
            future.add_done_callback(callback)
        else:
            wrapper()

    def _run(self):
        now = datetime.now()
        # Sort by priority desc; skip running or already-finished tasks
        candidates = sorted(
            (t for t in self._tasks if not t.finished_flag and not t.running),
            key=lambda t: getattr(t, 'priority', 0),
            reverse=True,
        )
        for task in candidates:
            # Skip if not yet due (handles RETRY backoff and regular intervals)
            if task.next_run is not None and now < task.next_run:
                continue

            # For "once" tasks: drop if the tolerance window has passed
            if task.schedule and task.schedule.type == 'once':
                delta_sec = (now - task.next_run).total_seconds()
                if delta_sec > task.schedule.tolerance_sec:
                    task._set_state(TaskState.FAILURE)
                    task.finished_flag = True
                    try:
                        label = self._task_label(task)
                        self._logger.warning(
                            f"{label}  id={task.task_id}  MISSED"
                            f"  scheduled={task.next_run}  tolerance={task.schedule.tolerance_sec}s"
                        )
                    except Exception:
                        pass
                    continue

            self._run_task(task)