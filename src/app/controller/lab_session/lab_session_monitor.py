from datetime import datetime, timedelta
from PySide6.QtCore import QObject, Signal
from src.app.model.types.session_status import SessionStatus
from src.app.model.types.session_info import SessionInfo
from src.app.model.types.booking_status import BookingStatus

class LabSessionMonitor(QObject):
    """
    Monitors a lab session's expiration and remaining time.
    Supports:
    - Booking-based sessions
    - Custom end-time sessions
    - Temporary sessions (default duration)
    """
    expired = Signal()
    timeleft = Signal(int)
    new_expired_datetime = Signal(datetime)
    exception = Signal(Exception)

    RECHECK_BOOKING_INTERVAL = 5*60  # seconds (5 minutes)
    DEFAULT_DURATION = timedelta(minutes=10)  # default duration for temporary sessions

    def __init__(self, lab_api_model, default_duration: timedelta | None = None):
        super().__init__()
        self._has_started = False
        self._expired_datetime: datetime | None = None
        self._seconds_left: int = 0
        self._recheck_counter: int = 0
        self._booking_code: str | None = None
        self._lab_api_model = lab_api_model
        self._default_duration = default_duration or self.DEFAULT_DURATION

    def start(self, session_info: SessionInfo, duration: timedelta | None = None):
        """
        Start monitoring a session.

        Behavior:
        - If session_info has booking_code + to_datetime → treat as a booked session.
        - If session_info has only to_datetime → custom end time session.
        - If session_info is None → temporary session with default duration.
        - If duration is provided → overrides default duration where applicable.
        """
        if session_info is None:
            # Treat as a temporary session if no session info is provided
            self._booking_code = None
            self._expired_datetime = datetime.now() + (duration or self._default_duration)
        else:
            self._booking_code = session_info.booking_code
            self._expired_datetime = session_info.to_datetime or datetime.now() + (duration or self._default_duration)
        self._seconds_left = 0
        self._recheck_counter = 0
        self._has_started = True

    def stop(self):
        """Stop monitoring and reset session state."""
        self._has_started = False
        self._booking_code = None
        self._expired_datetime = None
        self._seconds_left = 0
        self._recheck_counter = 0

    def trigger_recheck_booking(self):
        """Force booking info recheck on next cycle."""
        self._recheck_counter = self.RECHECK_BOOKING_INTERVAL
    
    def recheck_booking(self):
        self._recheck_counter = self.RECHECK_BOOKING_INTERVAL
        self._recheck_booking()

    def run(self):
        """Perform a monitoring cycle. Should be called periodically (e.g., via QTimer)."""
        if not self._has_started:
            return
        try:
            self._recheck_booking()
            self._calculate_timeleft()
        except Exception as e:
            self.exception.emit(e)

    def _recheck_booking(self):
        """Recheck booking info every 5 minutes."""
        if not (self._booking_code and self._lab_api_model):
            return

        if self._recheck_counter >= self.RECHECK_BOOKING_INTERVAL:  # assuming run() is called once per second
            self._recheck_counter = 0
            # None = the booking was completed, cancelled or has ended on the backend
            booking_info = self._lab_api_model.check_booking_running(self._booking_code)
            self._update_expired_datetime(booking_info)
        else:
            self._recheck_counter += 1

    def _update_expired_datetime(self, booking_info):
        """Update expiration time based on booking status."""
        if booking_info is not None and booking_info.booking_status == BookingStatus.IN_PROGRESS:
            if booking_info.to_datetime != self._expired_datetime:
                self._expired_datetime = booking_info.to_datetime
                self.new_expired_datetime.emit(self._expired_datetime)
        else:
            # Session ended earlier
            self._expired_datetime = datetime.now()

    def _calculate_timeleft(self):
        """Calculate remaining time and emit signals if needed."""
        if not self._expired_datetime:
            return

        now = datetime.now()
        if now >= self._expired_datetime:
            self.expired.emit()
            self.stop()
            return

        current_seconds_left = int((self._expired_datetime - now).total_seconds())
        if abs(self._seconds_left - current_seconds_left) > 60:
            self._seconds_left = current_seconds_left
            minutes_left = (current_seconds_left + 59) // 60  # round up
            self.timeleft.emit(minutes_left)
