from datetime import datetime, timedelta

from src.app.controller.remote_session.session_timer import SessionTimer
from src.app.model.types.booking import Booking, BookingStatus
from src.app.model.types.remote_session import RemoteSession


class FakeBackend:
    def __init__(self, booking):
        self.booking = booking
        self.calls = 0

    def get_running_booking(self, code):
        self.calls += 1
        return self.booking


def session(code="BOOKING-1", ends_at=None):
    return RemoteSession("pc", "tech", "ann", "Ann", "10.0.0.1", "laptop", booking_code=code, ends_at=ends_at)


def record(timer):
    events = {"expired": 0, "minutes": [], "ends_at": []}
    timer.expired.connect(lambda: events.__setitem__("expired", events["expired"] + 1))
    timer.minutes_left_changed.connect(events["minutes"].append)
    timer.ends_at_changed.connect(events["ends_at"].append)
    return events


def test_temporary_session_uses_the_given_duration():
    timer = SessionTimer(FakeBackend(None))
    events = record(timer)
    timer.start(session(code=None), temporary_duration=timedelta(minutes=10))
    timer.run()
    assert events["minutes"] == [10] and events["expired"] == 0


def test_extended_booking_moves_the_end():
    end = datetime.now() + timedelta(minutes=30)
    later = end + timedelta(minutes=30)
    backend = FakeBackend(Booking("BOOKING-1", "ann", None, later, BookingStatus.IN_PROGRESS))
    timer = SessionTimer(backend)
    events = record(timer)
    timer.start(session(ends_at=end))
    timer.recheck_now()
    timer.run()
    assert events["ends_at"] == [later] and timer.ends_at == later


def test_booking_ended_on_the_backend_expires_the_session():
    timer = SessionTimer(FakeBackend(None))
    events = record(timer)
    timer.start(session(ends_at=datetime.now() + timedelta(hours=1)))
    timer.recheck_now()
    timer.run()
    assert events["expired"] == 1 and timer.ends_at is None


def test_booking_is_rechecked_every_five_minutes_only():
    backend = FakeBackend(Booking("BOOKING-1", "ann", None, datetime.now() + timedelta(hours=1)))
    timer = SessionTimer(backend)
    timer.start(session(ends_at=datetime.now() + timedelta(hours=1)))
    for _ in range(SessionTimer.BOOKING_RECHECK_INTERVAL_S - 1):
        timer.run()
    assert backend.calls == 0
    timer.run()
    assert backend.calls == 1
