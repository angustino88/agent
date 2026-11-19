from enum import Enum


class LoginMode(str, Enum):
    ADMIN = "admin"
    ADMIN_BOOKING = "admin_booking"
    USER_BOOKING = "user_booking"
    TEMPORARY = "temporary"

    @property
    def is_admin(self) -> bool:
        return self in (LoginMode.ADMIN, LoginMode.ADMIN_BOOKING)

    @property
    def has_booking(self) -> bool:
        return self in (LoginMode.ADMIN_BOOKING, LoginMode.USER_BOOKING)
