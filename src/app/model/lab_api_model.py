import threading
import uuid
import ipaddress
import requests
from datetime import datetime
from typing import Optional
from src.mvc.base_model import BaseModel
from src.mvc.task_schedule import task, Schedule
from src.utils.http_client import ClientRequest
from src.utils.datetime import iso_datetime
from src.service_gateway import GatewayClient
from src.core.api.lab_api_core_service import LabApiCoreService
from src.core.api.lab_api_service_gateway import LabApiServiceGateway
from src.core.agent_api import (
    ActivityReport,
    AgentApiClient,
    AgentIdentity,
    BookingResult,
    IdentityStore,
    SessionLogOutbox,
    errors as agent_errors,
    load_credentials,
)
from src.app.model.types.booking_info import BookingInfo
from src.app.model.types.booking_status import BookingStatus
from src.app.model.update_checker import UpdateChecker, PackageUpdate
from src.app.model.config.task_schedule_config import TaskScheduleConfig

class LabApiModel(BaseModel):
    """Orchestrates core and service-gateway API interactions."""

    def __init__(self):
        super().__init__()
        self._client_core = None
        self._client_service_gateway = None
        self._service_core = None
        self._service_gateway = None
        self._agent_store: Optional[IdentityStore] = None
        self._agent_client: Optional[AgentApiClient] = None
        self._session_log_outbox: Optional[SessionLogOutbox] = None
        self._agent_lock = threading.Lock()

    def init(self):
        """Initialize services and clients."""
        # Load dependencies
        self._app_config = self.model.config_model.app_config
        self._app_settings = self.model.config_model.app_settings
        self._app_config_dynamic = self.model.config_model.app_config_dynamic
        self._credential_config = self.model.config_model.credential_config
        self._logger = self.model.logging_model.system_logger
        self._computer_sku = self.model.computer_model.computer_name
        self._source = f"AGENT_{self._computer_sku}"

        # Initialize service-gateway client and service (GatewayClient handles HTTPS→HTTP fallback)
        self._client_service_gateway = GatewayClient(
            base_url=self._app_config.SERVICE_GATEWAY_URL,
            auth_scheme='Bearer',
            logger=self._logger if self._app_config_dynamic.app_debug_enabled else None,
            printer=print if self._app_config.IS_DEVELOPMENT else None,
            token_refresh_callback=self.refresh_service_gateway_token)

        self._service_gateway = LabApiServiceGateway(
            self._client_service_gateway,
            self._computer_sku,
            self._source
        )

        self.login_service_gateway()

        # Initialize core client and service
        self._client_core = ClientRequest(
            base_url=self._app_settings.prod_backend_url,
            auth_value=self._credential_config.prod_api_key,
            logger=self._logger if self._app_config_dynamic.app_debug_enabled else None,
            printer=print if self._app_config.IS_DEVELOPMENT else None
        )
        self._service_core = LabApiCoreService(
            self._client_core,
            self._computer_sku,
            self._source
        )

        # Update checker (needs service gateway & logger)
        self._update_checker = UpdateChecker(self._service_gateway, self._logger)

        # Signed agent device API (/agent/...): identity created by `LabMango enroll`
        self._agent_store = IdentityStore(self._app_config.AGENT_DIR)
        self._agent_client = AgentApiClient(
            "",
            timeout=5,
            logger=self._logger if self._app_config_dynamic.app_debug_enabled else None,
        )
        self._session_log_outbox = SessionLogOutbox(
            self._app_config.SESSION_LOG_OUTBOX_FILE, logger=self._logger
        )
        self.reload_agent_identity()

    @property
    def client(self) -> ClientRequest:
        return self._client_core

    @property
    def service(self) -> LabApiCoreService:
        return self._service_core

    @property
    def service_gateway_client(self) -> GatewayClient:
        return self._client_service_gateway

    @property
    def service_gateway(self) -> LabApiServiceGateway:
        return self._service_gateway

    @property
    def backend_url(self) -> str:
        return self._app_settings.prod_backend_url

    @property
    def frontend_url(self) -> str:
        return self._app_settings.prod_frontend_url

    @property
    def service_gateway_url(self) -> str:
        if self._client_service_gateway:
            return self._client_service_gateway.base_url
        return self._app_config.SERVICE_GATEWAY_URL

    @property
    def otp_master_code(self) -> str:
        return self._credential_config.otp_master_code

    def login_service_gateway(self):
        """Login to service gateway and set tokens."""
        try:
            response = self._service_gateway.login()
            if not response.success or not response.data:
                self._logger.warning("Failed to login to service gateway.")
                return False
            token = response.data.get("access")
            refresh = response.data.get("refresh")
            if token:
                self._client_service_gateway.auth_value = token.strip()
                self._logger.info("Service gateway access token set.")
            if refresh:
                self._client_service_gateway.refresh_token = refresh.strip()
                self._logger.info("Service gateway refresh token set.")
            return True
        except Exception as e:
            self._logger.error(f"Exception in login_service_gateway: {e}")
            return False

    @task(schedule=TaskScheduleConfig.REFRESH_SERVICE_GATEWAY_TOKEN, heavy=True)
    def refresh_service_gateway_token(self):
        """Refresh service-gateway token using the refresh endpoint."""
        try:
            refresh_token = self._client_service_gateway.refresh_token
            if not refresh_token:
                self._logger.warning("No refresh token available, need to login again.")
                return self.login_service_gateway()
            response = self._service_gateway.refresh_token(refresh_token)
            if not response.success or not response.data:
                self._logger.warning("Failed to refresh service gateway token, need to login again.")
                return self.login_service_gateway()
            token = response.data.get("access")
            new_refresh = response.data.get("refresh")
            if token:
                self._client_service_gateway.auth_value = token.strip()
                self._logger.info("Service gateway access token refreshed.")
            if new_refresh:
                self._client_service_gateway.refresh_token = new_refresh.strip()
                self._logger.info("Service gateway refresh token updated.")
            return True
        except Exception as e:
            self._logger.error(f"Exception in refresh_service_gateway_token: {e}")
            return self.login_service_gateway()
    
    @task(schedule=TaskScheduleConfig.SYNC_SERVICE_GATEWAY, heavy=True)
    def sync_service_gateway(self):
        """Sync OTP master code and prod config from service gateway."""
        self.sync_safe_mode()
        self.sync_otp_master_code()
        self.sync_prod_config()

    def sync_otp_master_code(self, raise_on_error: bool = False):
        """Fetch OTP master code from service gateway (with token retry)."""
        try:
            response = self._service_gateway.get_otp_master_code(timeout=3)
            if not response or not response.success or not response.data:
                msg = "Failed to fetch OTP master code from service gateway."
                self._logger.warning(msg)
                if raise_on_error:
                    raise RuntimeError(msg)
                return
            otp_code = response.data.get("otp_code")
            if otp_code and otp_code != self._credential_config.otp_master_code:
                self._credential_config.set_otp_master_code(otp_code.strip())
                self._logger.info("OTP master code updated from service gateway.")
        except Exception as e:
            msg = f"Exception in sync_otp_master_code: {e}"
            self._logger.error(msg)
            if raise_on_error:
                raise RuntimeError(msg) from e

    def sync_prod_config(self, raise_on_error: bool = False):
        """Fetch production server config from service gateway (with token retry)."""
        try:
            response = self._service_gateway.get_prod_server_config(timeout=3)
            if not response or not response.success or not response.data:
                msg = "Failed to fetch production config from service gateway."
                self._logger.warning(msg)
                if raise_on_error:
                    raise RuntimeError(msg)
                return
            data = response.data

            api_key = data.get("api_key")
            if api_key and api_key != self._credential_config.prod_api_key:
                self._credential_config.set_prod_api_key(api_key.strip())
                if self._client_core:
                    self._client_core.auth_value = api_key.strip()
                self._logger.info("API key updated from service gateway.")

            backend_url = data.get("backend_url")
            if backend_url and backend_url != self._app_settings.prod_backend_url:
                self._app_settings.set_prod_backend_url(backend_url.strip())
                if self._client_core:
                    self._client_core.base_url = backend_url.strip()
                self._logger.info("Backend URL updated from service gateway.")

            frontend_url = data.get("frontend_url")
            if frontend_url and frontend_url != self._app_settings.prod_frontend_url:
                self._app_settings.set_prod_frontend_url(frontend_url.strip())
                self._logger.info("Frontend URL updated from service gateway.")
        except Exception as e:
            msg = f"Exception in sync_prod_config: {e}"
            self._logger.error(msg)
            if raise_on_error:
                raise RuntimeError(msg) from e
    
    def sync_safe_mode(self, raise_on_error: bool = False) -> bool:
        """Fetch safe mode status from service gateway (with token retry) and update app settings."""
        try:
            response = self._service_gateway.get_safe_mode_status(timeout=3)
            if not response or not response.success or not response.data:
                msg = "Failed to fetch safe mode status from service gateway."
                self._logger.warning(msg)
                if raise_on_error:
                    raise RuntimeError(msg)
                return
            is_safe_mode = response.data.get("safe_mode_enabled", False)
            if is_safe_mode != self._app_settings.safe_mode:
                self._app_settings.set_safe_mode(bool(is_safe_mode))

        except Exception as e:
            msg = f"Exception in sync_safe_mode: {e}"
            self._logger.error(msg)
            if raise_on_error:
                raise RuntimeError(msg) from e
            return

    def check_package_update(self, current_version: str) -> PackageUpdate:
        return self._update_checker.check(current_version)

    def check_backend_alive(self) -> bool:
        if self._agent_client and self._agent_client.base_url:
            try:
                self._agent_client.get_info()
                return True
            except agent_errors.AgentApiError:
                return False
        try:
            requests.get(self.backend_url, verify=False, timeout=3)
            return True
        except requests.RequestException:
            return False

    def check_frontend_alive(self) -> bool:
        try:
            requests.get(self.frontend_url, verify=False, timeout=3)
            return True
        except requests.RequestException:
            return False

    def check_service_gateway_alive(self) -> bool:
        return self._client_service_gateway.check_alive(timeout=3) if self._client_service_gateway else False

    # ==================================================================
    # Agent device API (signed /agent/... routes)
    # ==================================================================

    @property
    def agent_api(self) -> AgentApiClient:
        return self._agent_client

    @property
    def agent_identity(self) -> Optional[AgentIdentity]:
        return self._agent_client.identity if self._agent_client else None

    @property
    def is_agent_enrolled(self) -> bool:
        return bool(self._agent_client and self._agent_client.is_enrolled)

    def reload_agent_identity(self) -> bool:
        """(Re)load the enrolled identity and key from disk; returns True when usable."""
        with self._agent_lock:
            identity, key = load_credentials(self._agent_store)
            if identity is None or not identity.is_enrolled:
                self._agent_client.set_credentials(None, None)
                self._logger.warning("[Agent] Not enrolled. Run `LabMango enroll --url ... --agent-uid ...`.")
                return False
            if key is None:
                self._agent_client.set_credentials(None, None)
                self._logger.error(f"[Agent] Key for agent {identity.agent_uid} is missing; re-enrollment needed.")
                return False
            self._agent_client.base_url = identity.backend_url
            self._agent_client.verify = identity.extra.get("tls_verify", True)
            self._agent_client.set_credentials(identity, key)
            self._logger.info(f"[Agent] Identity {identity.agent_uid} on {identity.backend_key} loaded.")
            return True

    def _require_agent(self) -> AgentApiClient:
        if not self.is_agent_enrolled and not self.reload_agent_identity():
            raise agent_errors.NotEnrolled("This computer is not enrolled with Lab Mango. Ask an administrator to enroll it.")
        return self._agent_client

    @task(schedule=TaskScheduleConfig.AGENT_HEARTBEAT, heavy=True)
    def send_agent_heartbeat(self):
        """Liveness for operators, then retry any queued session logs."""
        if not self.is_agent_enrolled and not self.reload_agent_identity():
            return False
        try:
            self._agent_client.heartbeat()
        except agent_errors.Unauthenticated as e:
            self._logger.error(f"[Agent] Heartbeat rejected (agent revoked or clock skew?): {e}")
            return False
        except agent_errors.AgentApiError as e:
            self._logger.warning(f"[Agent] Heartbeat failed: {e}")
            return False
        self.flush_session_logs()
        return True

    def report_activity(self, report: ActivityReport) -> bool:
        try:
            self._require_agent().report_activity(report)
            return True
        except agent_errors.AgentApiError as e:
            self._logger.warning(f"[Agent] Activity report failed: {e}")
            return False

    def queue_session_log(
        self,
        login_at: datetime,
        logout_at: datetime,
        active_seconds: float,
        remote_user: str,
        remote_ip: str = "",
        remote_host: str = "",
        booking_code: Optional[str] = None,
    ) -> str:
        """Persist a finished session for delivery; returns its event_key (idempotency key)."""
        event_key = str(uuid.uuid4())
        self._session_log_outbox.add({
            "event_key": event_key,
            "login_at": _aware_iso(login_at),
            "logout_at": _aware_iso(logout_at),
            "active_duration_seconds": max(0.0, float(active_seconds)),
            "remote_user": (remote_user or "-")[:255],
            "remote_ip": _ip_or_none(remote_ip),
            "remote_host": (remote_host or "")[:255] or None,
            "booking_code": booking_code or None,
            "agent_version": str(self._app_config.APP_VERSION)[:64],
        })
        return event_key

    def flush_session_logs(self) -> int:
        if not self.is_agent_enrolled:
            return 0
        return self._session_log_outbox.flush(self._agent_client)

    # ---- bookings ------------------------------------------------------

    @staticmethod
    def _to_booking_info(result: BookingResult, status: BookingStatus) -> BookingInfo:
        return BookingInfo(
            booking_code=result.booking_code,
            booking_creator=(result.booked_for or "").lower(),
            from_datetime=_local_minutes(result.starts_at),
            to_datetime=_local_minutes(result.ends_at),
            booking_status=status,
        )

    def get_booking_info(self, booking_code: str) -> BookingInfo:
        """Read-only eligibility check (does not check in).

        Raises LookupError when the code cannot be used on this computer now: unknown, not
        approved, cancelled, finished, other bench or outside its window (the backend gives one
        answer for all of these on purpose).
        """
        result = self._require_agent().validate_booking(booking_code)
        if not result.ok:
            raise LookupError("Booking is not valid for this computer at this time")
        return self._to_booking_info(result, BookingStatus.AVAILABLE)

    def check_booking_running(self, booking_code: str) -> Optional[BookingInfo]:
        """Re-read a running booking; ``None`` when it has ended, been completed or cancelled."""
        result = self._require_agent().validate_booking(booking_code)
        return self._to_booking_info(result, BookingStatus.IN_PROGRESS) if result.ok else None

    def check_in_booking(self, booking_code: str) -> BookingInfo:
        """Start (or resume) the booking for this login; safe to repeat."""
        result = self._require_agent().check_in_booking(booking_code)
        if not result.ok:
            raise PermissionError("Booking cannot be started on this computer now")
        return self._to_booking_info(result, BookingStatus.IN_PROGRESS)

    def complete_booking(self, booking_code: str) -> None:
        result = self._require_agent().complete_booking(booking_code)
        if not result.ok:
            raise RuntimeError("Booking could not be ended (it may already be finished)")

    def extend_booking(self, booking_code: str, new_end: datetime) -> BookingInfo:
        """Move the end of a running booking. Raises ValueError with a readable reason."""
        try:
            result = self._require_agent().extend_booking(booking_code, _aware_iso(new_end))
        except agent_errors.BookingExtensionRejected as e:
            raise ValueError(_extension_reason(e)) from e
        if not result.ok:
            raise RuntimeError("Booking could not be extended (no running booking on this computer)")
        return self._to_booking_info(result, BookingStatus.IN_PROGRESS)


def _aware_iso(value: datetime) -> str:
    """Naive datetimes are local wall-clock time; send them with their UTC offset."""
    if value.tzinfo is None:
        value = value.astimezone()
    return value.isoformat()


def _local_minutes(value: Optional[datetime]) -> Optional[datetime]:
    """Backend times → naive local time (the UI and session monitor work in local time)."""
    if value is None:
        return None
    return value.astimezone().replace(tzinfo=None, second=0, microsecond=0)


def _ip_or_none(value: Optional[str]) -> Optional[str]:
    try:
        return str(ipaddress.ip_address((value or "").strip()))
    except ValueError:
        return None


_EXTENSION_REASONS = {
    "already_ended": "The booking has already ended.",
    "not_later": "The new end time must be later than the current end.",
    "too_short": "Extend by at least 10 minutes.",
    "needs_approval": "Bookings longer than 4 hours need approval in the web app.",
    "bench_not_in_service": "The bench is not in service.",
    "bench_not_free": "Another booking starts on this bench before that time.",
}


def _extension_reason(error: "agent_errors.BookingExtensionRejected") -> str:
    message = _EXTENSION_REASONS.get(error.reason, str(error.args[0]))
    limit = _local_minutes(error.limit_at)
    return f"{message}\nLimit: {limit:%Y-%m-%d %H:%M}" if limit else message
