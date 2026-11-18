"""Login screen: booking code (backend check-in) or username + OTP (temporary or admin login)."""

from __future__ import annotations

import getpass
import threading
from dataclasses import dataclass
from typing import Optional

from pyad import aduser, pyad

from src.app.controller.login.login_event_monitor import LoginEventMonitor
from src.app.model.config.task_schedule_config import TaskScheduleConfig
from src.app.model.types.booking import Booking, parse_booking_code
from src.app.model.types.login_event import LoginEvent
from src.app.model.types.login_info import LoginInfo
from src.app.model.types.login_mode import LoginMode
from src.app.model.types.user_attributes import UserAttributes
from src.core.agent_api.errors import BackendUnreachable
from src.core.otp.otp_manager import OTPManager
from src.mvc.base_controller import BaseController
from src.mvc.slot_guard import slot_guard
from src.mvc.task_schedule import task
from src.utils.remote_desktop import RemoteDesktop


@dataclass
class _PendingLogin:
    user: Optional[UserAttributes] = None
    booking: Optional[Booking] = None
    is_logged_in: bool = False


class LoginCtrl(BaseController):
    def __init__(self):
        super().__init__()
        self._pending = _PendingLogin()
        self._login_event = LoginEvent.SCREEN_LOGOUT
        self._otp_manager: Optional[OTPManager] = None
        self._login_event_monitor = LoginEventMonitor()
        self._login_event_monitor.event.connect(self._on_login_event)

    def init(self):
        self._app_settings = self.model.config_model.app_settings
        pyad.set_defaults(domain=self._app_settings.ad_default_domain)
        self._logger = self.model.logging_model.system_logger
        self._message_box = self.view.message_box
        self._login_view = self.view.login_view
        self._temporary_login_view = self.view.temp_login_view
        self._main_window_view = self.view.main_window_view
        self._backend_model = self.model.backend_model
        self._gateway_model = self.model.gateway_model
        self._computer_name = self.model.computer_model.computer_name
        self._otp_manager = OTPManager(primary_sender=self._gateway_model.service)

        self._login_view.ui.login_btn.clicked.connect(self.login)
        self._login_view.ui.cancel_btn.clicked.connect(self.cancel)
        self._temporary_login_view.ui.verify_btn.clicked.connect(self.verify_otp)
        self._temporary_login_view.ui.resend_label.linkActivated.connect(self.resend_otp)

    # ------------------------------------------------------------------ helpers

    def _show_error(self, e: Exception):
        self._message_box.error(str(e), parent=self._login_view)

    @property
    def _admin_usernames(self) -> set[str]:
        return self._app_settings.admin_usernames

    def _lookup_user(self, username: str) -> UserAttributes:
        """Find the user in Active Directory; configured administrators may log in without an entry."""
        if not username:
            raise ValueError("Enter a username or a booking code.")
        last_error: Exception | None = None
        for search_base in (None, *self._app_settings.ad_search_bases):
            try:
                ad_user = (
                    aduser.ADUser.from_cn(username)
                    if search_base is None
                    else aduser.ADUser.from_cn(username, search_base=search_base)
                )
                return UserAttributes.from_aduser(ad_user)
            except Exception as e:
                last_error = e
        if username in self._admin_usernames:
            return UserAttributes(username=username, user_display_name=username)
        raise LookupError(f"Unknown user: {username}") from last_error

    def _validate_booking(self, booking_code: str) -> Booking:
        """Read-only: the backend decides (approved, this computer's bench, inside the window) and
        answers every refusal the same way, so no reason is available."""
        try:
            booking = self._backend_model.validate_booking(booking_code)
        except LookupError:
            raise PermissionError(
                "This booking code cannot be used on this computer now.\n"
                "Check the code, that the booking is approved, and its start time."
            ) from None
        except BackendUnreachable:
            raise ConnectionError("The Lab Mango backend is unreachable.") from None
        if not booking.booked_for:
            raise PermissionError("The booking has no user.")
        return booking

    def _check_in(self, booking_code: str) -> Booking:
        try:
            return self._backend_model.check_in_booking(booking_code)
        except BackendUnreachable:
            raise ConnectionError("The Lab Mango backend is unreachable.") from None

    def _login_mode(self, username: str, has_booking: bool) -> LoginMode:
        if username in self._admin_usernames:
            return LoginMode.ADMIN_BOOKING if has_booking else LoginMode.ADMIN
        return LoginMode.USER_BOOKING if has_booking else LoginMode.TEMPORARY

    def _complete_login(self, user: UserAttributes, booking: Optional[Booking]) -> None:
        mode = self._login_mode(user.username, booking is not None)
        info = LoginInfo(
            username=user.username,
            user_display_name=user.user_display_name or user.username,
            technical_user=getpass.getuser().lower(),
            booking_code=booking.booking_code if booking else None,
            login_event=self._login_event,
            login_mode=mode,
        )
        self._pending.is_logged_in = True
        self._logger.info(
            f"[Login] user={info.username} mode={mode.value} event={info.login_event.value} "
            f"technical_user={info.technical_user} computer={self._computer_name} "
            f"booking={info.booking_code or '-'}"
            + (f" window={booking.starts_at}->{booking.ends_at}" if booking else "")
        )
        self._login_view.close_screen()
        self._main_window_view.set_admin_enabled(mode.is_admin)
        self.bus_emit("session:start", (info, booking))

    def _send_otp_async(self, username: str) -> None:
        threading.Thread(target=self._otp_manager.send_otp, args=(username,), daemon=True).start()

    def _any_service_reachable(self) -> bool:
        for check in (self._backend_model.check_alive, self._gateway_model.check_alive):
            try:
                if check():
                    return True
            except Exception:
                pass
        return False

    # ------------------------------------------------------------------ OS login events

    def _on_login_event(self, event: LoginEvent):
        self._login_event = event
        if event in (LoginEvent.REMOTE_LOGIN, LoginEvent.SCREEN_LOGIN):
            self._logger.info(f"[Login] OS event {event.value}")
            self._login_view.show_screen()
        elif event in (LoginEvent.REMOTE_LOGOUT, LoginEvent.SCREEN_LOGOUT):
            self._logger.info(f"[Login] OS event {event.value}")
            if self._pending.is_logged_in:
                self._pending.is_logged_in = False
                self.bus_emit("session:end")
            self._login_view.close_screen()

    @task(schedule=TaskScheduleConfig.LOGIN_EVENT_MONITOR, heavy=True)
    def monitor_login_events(self):
        self._login_event_monitor.run()

    # ------------------------------------------------------------------ slots

    @slot_guard(on_exception=_show_error)
    def login(self):
        text = (self._login_view.get_login_input() or "").strip()
        self._pending = _PendingLogin()
        self._main_window_view.set_admin_enabled(True)

        booking_code = parse_booking_code(text)
        if booking_code:
            booking = self._validate_booking(booking_code)
            user = self._lookup_user(booking.booked_for)
            booking = self._check_in(booking_code)
            self._complete_login(user, booking)
            return

        user = self._lookup_user(text.lower())
        self._pending.user = user
        if self._any_service_reachable():
            self._otp_manager.cleanup_expired()
            self._send_otp_async(user.username)
            self._temporary_login_view.clear_otp()
            self._temporary_login_view.exec()
            return
        # Offline: Lab Mango cannot send a code, so the login is accepted without one.
        self._logger.warning(f"[Login] Offline login without OTP for {user.username}")
        self._complete_login(user, None)

    @slot_guard(on_exception=_show_error)
    def verify_otp(self):
        user = self._pending.user
        if user is None:
            raise ValueError("Start the login again.")
        otp = self._temporary_login_view.get_otp()
        master_code = self._gateway_model.otp_master_code
        if not ((master_code and otp == master_code) or self._otp_manager.validate_otp(user.username, otp)):
            self._message_box.error("Invalid code. Please try again.", parent=self._temporary_login_view)
            return
        self._temporary_login_view.close()
        self._complete_login(user, None)

    @slot_guard(on_exception=_show_error)
    def resend_otp(self, _link=None):
        if self._pending.user is None:
            raise ValueError("Start the login again.")
        self._send_otp_async(self._pending.user.username)

    @slot_guard(on_exception=_show_error)
    def cancel(self):
        RemoteDesktop.disconnect()
        self._login_view.close_screen()

    @slot_guard(on_exception=_show_error)
    def close_screen(self):
        self._login_view.close_screen()
