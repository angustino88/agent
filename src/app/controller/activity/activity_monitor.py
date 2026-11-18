"""Derives this computer's live activity status from the session and the mouse cursor."""

import time

import pyautogui
from PySide6.QtCore import QObject, Signal

from src.app.model.types.activity_status import ActivityStatus
from src.app.model.types.remote_session import RemoteSession


class ActivityMonitor(QObject):
    """Call :meth:`run` once per second.

    ``status_changed`` emits ``(ActivityStatus, inactive_minutes)`` when the status changes, and
    again every ``RESEND_INTERVAL_S`` so the backend's activity stays fresh.
    """

    status_changed = Signal(tuple)
    exception = Signal(Exception)

    CURSOR_MOVE_THRESHOLD_PX = 100
    INACTIVE_AFTER_S = 60
    RESEND_INTERVAL_S = 5 * 60

    def __init__(self):
        super().__init__()
        self._status = ActivityStatus.OFFLINE
        self._session: RemoteSession | None = None
        self._last_cursor = pyautogui.position()
        self._last_tick = time.monotonic()
        self._idle_seconds = 0.0
        self._inactive_seconds_total = 0.0
        self._ticks_since_send = 0

    @property
    def inactive_seconds_total(self) -> float:
        """Time spent inactive since the session started (idle beyond the threshold, plus the threshold)."""
        return self._inactive_seconds_total

    @property
    def status(self) -> ActivityStatus:
        return self._status

    def on_session_started(self, session: RemoteSession | None) -> None:
        self._session = session
        self._inactive_seconds_total = 0.0
        self._reset_idle()

    def on_session_ended(self) -> None:
        self._session = None
        self._reset_idle()

    def run(self) -> None:
        try:
            self._tick()
        except Exception as e:
            self.exception.emit(e)

    # ------------------------------------------------------------------ internals

    def _reset_idle(self) -> None:
        self._idle_seconds = 0.0
        self._last_tick = time.monotonic()

    def _update_idle(self) -> None:
        now = time.monotonic()
        cursor = pyautogui.position()
        moved = (
            abs(cursor[0] - self._last_cursor[0]) > self.CURSOR_MOVE_THRESHOLD_PX
            or abs(cursor[1] - self._last_cursor[1]) > self.CURSOR_MOVE_THRESHOLD_PX
        )
        if moved:
            self._last_cursor = cursor
            self._idle_seconds = 0.0
        else:
            elapsed = now - self._last_tick
            was_inactive = self._idle_seconds > self.INACTIVE_AFTER_S
            self._idle_seconds += elapsed
            if self._idle_seconds > self.INACTIVE_AFTER_S:
                # count the threshold once, when the computer becomes inactive
                self._inactive_seconds_total += elapsed if was_inactive else self._idle_seconds
        self._last_tick = now

    def _evaluate(self) -> ActivityStatus:
        if self._session is None:
            self._reset_idle()
            return ActivityStatus.FREE
        if self._session.is_maintenance:
            self._reset_idle()
            return ActivityStatus.MAINTAINING
        self._update_idle()
        return ActivityStatus.INACTIVE if self._idle_seconds > self.INACTIVE_AFTER_S else ActivityStatus.ACTIVE

    def _tick(self) -> None:
        status = self._evaluate()
        self._ticks_since_send += 1
        if status != self._status or self._ticks_since_send >= self.RESEND_INTERVAL_S:
            self._status = status
            self._ticks_since_send = 0
            self.status_changed.emit((status, int(self._idle_seconds // 60)))
