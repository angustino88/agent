"""Counts down a remote session and follows its booking on the backend."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from PySide6.QtCore import QObject, Signal

from src.app.model.types.remote_session import RemoteSession


class SessionTimer(QObject):
    """Call :meth:`run` once per second while a session is open.

    * ``minutes_left_changed(int)``: remaining minutes, rounded up (at most once per minute).
    * ``ends_at_changed(datetime)``: the booking end moved (extended in the web app or here).
    * ``expired()``: the end was reached, or the booking was completed/cancelled on the backend.
    """

    expired = Signal()
    minutes_left_changed = Signal(int)
    ends_at_changed = Signal(datetime)
    exception = Signal(Exception)

    BOOKING_RECHECK_INTERVAL_S = 5 * 60
    TEMPORARY_SESSION = timedelta(minutes=10)

    def __init__(self, backend_model):
        super().__init__()
        self._backend_model = backend_model
        self._running = False
        self._booking_code: Optional[str] = None
        self._ends_at: Optional[datetime] = None
        self._seconds_left = 0
        self._ticks_since_recheck = 0

    @property
    def ends_at(self) -> Optional[datetime]:
        return self._ends_at

    def start(self, session: RemoteSession, temporary_duration: Optional[timedelta] = None) -> None:
        """A booked session ends with its booking; any other session after ``temporary_duration``."""
        self._booking_code = session.booking_code or None
        self._ends_at = session.ends_at or datetime.now() + (temporary_duration or self.TEMPORARY_SESSION)
        self._seconds_left = 0
        self._ticks_since_recheck = 0
        self._running = True

    def stop(self) -> None:
        self._running = False
        self._booking_code = None
        self._ends_at = None
        self._seconds_left = 0
        self._ticks_since_recheck = 0

    def recheck_now(self) -> None:
        """Re-read the booking on the next tick."""
        self._ticks_since_recheck = self.BOOKING_RECHECK_INTERVAL_S

    def run(self) -> None:
        if not self._running:
            return
        try:
            self._recheck_booking()
            self._count_down()
        except Exception as e:
            self.exception.emit(e)

    def _recheck_booking(self) -> None:
        if not self._booking_code:
            return
        self._ticks_since_recheck += 1
        if self._ticks_since_recheck < self.BOOKING_RECHECK_INTERVAL_S:
            return
        self._ticks_since_recheck = 0
        booking = self._backend_model.get_running_booking(self._booking_code)
        if booking is None:
            self._ends_at = datetime.now()  # completed, cancelled or ended on the backend
        elif booking.ends_at and booking.ends_at != self._ends_at:
            self._ends_at = booking.ends_at
            self.ends_at_changed.emit(booking.ends_at)

    def _count_down(self) -> None:
        if self._ends_at is None:
            return
        now = datetime.now()
        if now >= self._ends_at:
            self.expired.emit()
            self.stop()
            return
        seconds_left = int((self._ends_at - now).total_seconds())
        if abs(self._seconds_left - seconds_left) > 60:
            self._seconds_left = seconds_left
            self.minutes_left_changed.emit((seconds_left + 59) // 60)
