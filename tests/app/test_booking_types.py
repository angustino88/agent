import pytest

from src.app.model.types.booking import BookingStatus, parse_booking_code


@pytest.mark.parametrize(
    "typed, code",
    [
        ("BOOKING-3fa9c2d1e07b4c", "BOOKING-3fa9c2d1e07b4c"),
        ("  booking-3fa9c2d1e07b4c ", "BOOKING-3fa9c2d1e07b4c"),
        ("BOOKING-AB12", "BOOKING-AB12"),  # matched exactly by the backend: case is kept
        ("jdoe", None),
        ("BOOKING-", None),
    ],
)
def test_parse_booking_code(typed, code):
    assert parse_booking_code(typed) == code


def test_booking_status_values_match_the_backend():
    assert [s.value for s in BookingStatus] == ["reserved", "in_progress", "completed", "cancelled", "expired"]
