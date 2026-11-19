from dataclasses import dataclass
from typing import Optional

from .login_event import LoginEvent
from .login_mode import LoginMode


@dataclass(frozen=True)
class LoginInfo:
    username: str
    user_display_name: str
    technical_user: str
    booking_code: Optional[str]
    login_event: LoginEvent
    login_mode: LoginMode
