import time
import getpass
import threading
from pyad import pyad, aduser
from typing import Optional, Set
from datetime import datetime
from dataclasses import dataclass, field
from requests.exceptions import ConnectTimeout
from src.mvc.slot_guard import slot_guard
from src.mvc.task_schedule import task, Schedule
from src.mvc.base_controller import BaseController
from src.app.model.types.login_mode import LoginMode
from src.app.model.types.login_info import LoginInfo
from src.app.model.types.login_event import LoginEvent
from src.app.model.types.booking_info import BookingInfo
from src.app.model.types.approval_status import ApprovalStatus
from src.app.model.types.booking_status import BookingStatus
from src.app.model.types.user_attributes import UserAttributes
from src.app.model.config.task_schedule_config import TaskScheduleConfig
from src.app.controller.login.login_event_monitor import LoginEventMonitor
from src.core.otp.otp_manager import OTPManager
from src.utils.remote_desktop import RemoteDesktop


@dataclass
class LoginState:
    success: bool = False
    mode: LoginMode = None
    booking_info: BookingInfo = None
    user_attr: UserAttributes = None
    login_time: datetime = field(default_factory=datetime.now)
    logout_time: datetime = field(default_factory=datetime.now)


class LoginCtrl(BaseController):
    BOOKING_PREFIX = "BOOKING-"
    _ADMIN_CACHE_TTL = 300  # seconds
    COMPANY_NAME = "Company"  # Used in build config and version info

    def __init__(self):
        super().__init__()
        pyad.set_defaults(domain="DC=,DC=com")
        self._login_state = LoginState()
        self._login_event: LoginEvent = LoginEvent.SCREEN_LOGOUT
        self._last_login_event: LoginEvent = LoginEvent.SCREEN_LOGOUT
        self._admins: Set[str] = set()
        self._admins_loaded_at: float = 0.0
        self._otp_manager: Optional[OTPManager] = None
        self._login_event_monitor = LoginEventMonitor()
        self._login_event_monitor.event.connect(self._on_login_event)

    def init(self):
        self._logger = self.model.logging_model.system_logger
        self._message_box = self.view.message_box
        self._login_view = self.view.login_view
        self._main_window_view = self.view.main_window_view
        self._lab_api_model = self.model.lab_api_model
        self._client = self.model.lab_api_model.client
        self._lab_computer = self.model.computer_model.computer_name
        self._otp_manager = OTPManager(
            primary_sender=self._lab_api_model.service,
            secondary_sender=self._lab_api_model.service_gateway
        )
        self._login_view.ui.login_btn.clicked.connect(self.login)
        self._login_view.ui.cancel_btn.clicked.connect(self.cancel)
        self.view.temp_login_view.ui.verify_btn.clicked.connect(self.verify_otp)
        self.view.temp_login_view.ui.resend_label.linkActivated.connect(self.resend_otp)

    # ===================== Internal helpers =====================

    def _exception_handler(self, e: Exception):
        self._message_box.error(str(e), parent=self._login_view)

    def _load_admins(self, force=False):
        """Load admin usernames (cached)."""
        if not force and (time.time() - self._admins_loaded_at) < self._ADMIN_CACHE_TTL and self._admins:
            return
        try:
            resp = self._lab_api_model.service.get_admin_usernames(timeout=3)
            self._admins = set(resp.data) if resp.success and isinstance(resp.data, list) else set()
            self._admins_loaded_at = time.time()
        except Exception as e:
            if not self._admins:
                self._admins = {"adminlab"}  # fallback
            self._logger.warning(f"Admin load failed: {e}")

    def _load_user_attributes(self, username: str):
        if not username:
            raise ValueError("Username is empty")
        self._load_admins()
        search_bases = [
            None,
            f"DC=apac,DC={self.COMPANY_NAME},DC=com",
            f"DC=de,DC={self.COMPANY_NAME},DC=com",
            f"DC=emea,DC={self.COMPANY_NAME},DC=com",
        ]

        last_exc: Exception | None = None
        ad_user = None

        for base in search_bases:
            try:
                if base is None:
                    ad_user = aduser.ADUser.from_cn(username)
                else:
                    ad_user = aduser.ADUser.from_cn(username, search_base=base)
                break  # success
            except Exception as e:
                last_exc = e
                ad_user = None

        if ad_user is None:
            if username in self._admins:
                self._login_state.user_attr = UserAttributes(username=username, user_displayname=username)
                return
            raise LookupError(f"Username does not exist: {username}") from last_exc

        self._login_state.user_attr = UserAttributes.from_aduser(ad_user)

    def _load_booking_info(self, booking_code: str):
        if not booking_code:
            raise ValueError("Booking code is empty")
        try:
            booking_info = self._lab_api_model.get_booking_info(booking_code)
        except ConnectTimeout:
            raise ConnectionError("Connection timed out")
        self._validate_booking(booking_info)
        self._login_state.booking_info = booking_info

    def _validate_booking(self, booking_info):
        if booking_info.booking_status not in (BookingStatus.AVAILABLE, BookingStatus.IN_PROGRESS):
            raise PermissionError(f"Booking status not accepted: {booking_info.booking_status}")
        if booking_info.approval_status != ApprovalStatus.APPROVED:
            raise PermissionError(f"Booking not approved: {booking_info.approval_status}")
        if self._lab_computer != booking_info.booking_computer:
            raise PermissionError(
                f"Booking computer mismatch: expected {self._lab_computer}, got {booking_info.booking_computer}"
            )
        now = datetime.now()
        if not (booking_info.from_datetime <= now <= booking_info.to_datetime):
            raise PermissionError(
                "Booking datetime invalid:\n"
                f"Current: {now:%Y-%m-%d %H:%M:%S}\n"
                f"Window: {booking_info.from_datetime} - {booking_info.to_datetime}"
            )

    def _build_login_info(self, username, displayname, booking_code, mode: LoginMode) -> LoginInfo:
        return LoginInfo(
            username=username,
            user_displayname=displayname,
            technical_user=getpass.getuser().lower(),
            booking_code=booking_code,
            login_action=self._login_event,
            login_mode=mode
        )

    def _resolve_mode(self, username: str, is_booking: bool) -> LoginMode:
        if username in self._admins:
            return LoginMode.ADMIN_BOOKING if is_booking else LoginMode.ADMIN
        return LoginMode.USER_BOOKING if is_booking else LoginMode.TEMP

    def _log_login_success(self, login_info: LoginInfo, booking_info):
        # Core login
        self._logger.info(
            "[LoginSuccess] user=%s mode=%s action=%s technical_user=%s computer=%s booking=%s",
            login_info.username,
            login_info.login_mode,
            login_info.login_action,
            login_info.technical_user,
            self._lab_computer,
            booking_info.booking_code if booking_info else "-"
        )
        # Booking details
        if booking_info:
            self._logger.info(
                "[BookingAttached] code=%s creator=%s project=%s computer=%s status=%s "
                "window=%s->%s duration_min=%s",
                booking_info.booking_code,
                booking_info.booking_creator,
                getattr(booking_info, "booking_project", ""),
                booking_info.booking_computer,
                booking_info.booking_status,
                booking_info.from_datetime,
                booking_info.to_datetime,
                int((booking_info.to_datetime - booking_info.from_datetime).total_seconds() // 60)
            )

    def _finalize_login(self, login_info: LoginInfo, booking_info):
        self._login_state.success = True
        self._login_state.mode = login_info.login_mode
        self._login_state.login_time = datetime.now()
        self._log_login_success(login_info, booking_info)
        self._login_view.close_screen()
        self._main_window_view.set_admin_enabled(
            login_info.login_mode in (LoginMode.ADMIN, LoginMode.ADMIN_BOOKING)
        )
        self.bus_emit("session:start", (login_info, booking_info))

    def _start_otp_flow(self, username: str):
        """Initiate OTP dialog (async send)."""
        self._otp_manager.cleanup_expired()
        threading.Thread(target=self._otp_manager.send_otp, args=(username,), daemon=True).start()
        self.view.temp_login_view.clear_otp()
        self.view.temp_login_view.exec()

    def _backends_up(self) -> bool:
        """Check if any backend reachable (tolerant)."""
        try:
            if self._lab_api_model.check_backend_alive():
                return True
        except Exception:
            pass
        try:
            if self._lab_api_model.check_service_gateway_alive():
                return True
        except Exception:
            pass
        return False

    # ===================== Login event handling =====================

    def _handle_login_event(self, event: LoginEvent):
        self._logger.info(f"[LoginEvent] event={event}")
        self._login_view.show_screen()

    def _handle_logout_event(self, event: LoginEvent):
        self._logger.info(f"[LogoutEvent] event={event}")
        if self._login_state.success:
            self._login_state.success = False
            self._logger.info(f"[LogoutSuccess] user={getattr(self._login_state.user_attr,'username',None)}")
            self.bus_emit("session:end")
        self._login_view.close_screen()

    def _on_login_event(self, event: LoginEvent):
        self._login_event = event
        if event in (LoginEvent.REMOTE_LOGIN, LoginEvent.SCREEN_LOGIN):
            self._handle_login_event(event)
        elif event in (LoginEvent.REMOTE_LOGOUT, LoginEvent.SCREEN_LOGOUT):
            self._handle_logout_event(event)
        else:
            self._logger.warning(f"Unknown login event: {event}")

    # ===================== Public / scheduled =====================

    @task(schedule=TaskScheduleConfig.LOGIN_STATE_MONITOR, heavy=True)
    def monitor_login_state(self):
        self._login_event_monitor.run()

    # ===================== Slots =====================

    @slot_guard(on_exception=_exception_handler)
    def login(self):
        login_input = (self._login_view.get_login_input() or "").strip()
        self._login_state = LoginState()
        self._main_window_view.set_admin_enabled(True)

        # Booking path
        if login_input.startswith(self.BOOKING_PREFIX):
            booking_code = login_input
            self._load_booking_info(booking_code)
            username = self._login_state.booking_info.booking_creator
            self._load_user_attributes(username)
            mode = self._resolve_mode(username, is_booking=True)
            info = self._build_login_info(
                username,
                getattr(self._login_state.user_attr, "user_displayname", username),
                booking_code,
                mode
            )
            self._finalize_login(info, self._login_state.booking_info)
            return

        # User path
        username = login_input.lower()
        self._load_user_attributes(username)
        username = self._login_state.user_attr.username  # normalized
        if self._backends_up():
            self._start_otp_flow(username)
            return

        # Offline fallback login
        mode = self._resolve_mode(username, is_booking=False)
        info = self._build_login_info(
            self._login_state.user_attr.username,
            self._login_state.user_attr.user_displayname,
            None,
            mode
        )
        self._finalize_login(info, None)

    @slot_guard(on_exception=_exception_handler)
    def verify_otp(self):
        otp = self.view.temp_login_view.get_otp()
        username = self._login_state.user_attr.username
        valid = (
            otp == self._lab_api_model.otp_master_code
            or self._otp_manager.validate_otp(username, otp)
        )
        if not valid:
            self._message_box.error("Invalid OTP. Please try again.", parent=self.view.temp_login_view)
            return

        mode = self._resolve_mode(username, is_booking=False)
        info = self._build_login_info(
            self._login_state.user_attr.username,
            self._login_state.user_attr.user_displayname,
            None,
            mode
        )
        self.view.temp_login_view.close()
        self._finalize_login(info, None)

    @slot_guard(on_exception=_exception_handler)
    def resend_otp(self, link=None):
        username = getattr(self._login_state.user_attr, "username", None)
        if not username:
            raise ValueError("No user context for OTP resend.")
        threading.Thread(target=self._otp_manager.send_otp, args=(username,), daemon=True).start()

    @slot_guard(on_exception=_exception_handler)
    def cancel(self):
        RemoteDesktop.disconnect()
        self._login_view.close_screen()

    @slot_guard(on_exception=_exception_handler)
    def close_screen(self):
        self._login_view.close_screen()