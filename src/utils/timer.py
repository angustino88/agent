"""Repeating timer running a callback at a fixed interval."""
from __future__ import annotations

import threading
from typing import Any, Callable


class Timer:
    """Repeating timer that runs *func* at a specified interval in a daemon thread."""

    def __init__(
        self,
        interval: float,
        func: Callable[..., Any],
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
    ):
        self._func = func
        self._args = args or ()
        self._kwargs = kwargs or {}
        self._interval = interval
        self._thread: threading.Thread | None = None
        self._running = threading.Event()

    @property
    def interval(self) -> float:
        return self._interval

    @interval.setter
    def interval(self, value: float) -> None:
        self._interval = value

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    def start(self) -> None:
        """Start the timer.  No-op if already running."""
        if self._thread and self._thread.is_alive():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the timer and wait for the thread to finish."""
        self._running.clear()
        if self._thread:
            self._thread.join()
            self._thread = None

    def restart(self) -> None:
        """Stop then start the timer."""
        self.stop()
        self.start()

    def _run(self) -> None:
        while self._running.is_set():
            self._func(*self._args, **self._kwargs)
            # Use Event.wait instead of time.sleep so stop() is responsive
            if not self._running.wait(0):
                self._running.wait(self._interval)
                if not self._running.is_set():
                    break
