"""Department backend (Lab Mango): the signed agent API ``/agent/...``.

The agent authenticates with the identity created by ``LabMango enroll`` (agent UID + Ed25519 key);
there is no shared API key. This model owns that identity and every backend call the app makes:
heartbeat, live activity, remote session logs, bookings and device observations.
"""

from __future__ import annotations

import ipaddress
import os
import threading
import time
import uuid
from datetime import datetime
from typing import Optional

import requests

from src.app.model.config.task_schedule_config import TaskScheduleConfig
from src.app.model.types.activity_status import ActivityStatus
from src.app.model.types.booking import Booking, BookingStatus
from src.app.model.types.remote_session import RemoteSession
from src.core.agent_api import (
    ActivityReport,
    AgentApiClient,
    AgentIdentity,
    BookingResult,
    IdentityStore,
    SessionLogOutbox,
    load_credentials,
)
from src.core.agent_api import errors as agent_errors
from src.core.licensing import CheckResult, result_body
from src.core.monitoring import DeviceObservationReporter
from src.mvc.base_model import BaseModel
from src.mvc.task_schedule import task


class BackendModel(BaseModel):
    def __init__(self):
        super().__init__()
        self._store: Optional[IdentityStore] = None
        self._client: Optional[AgentApiClient] = None
        self._session_logs: Optional[SessionLogOutbox] = None
        self._lock = threading.Lock()
        self._capabilities: tuple[str, ...] = ()
        self._capabilities_read_at = 0.0
        self._license_checks_etag = ""
        self._pending_license_reports: dict[str, tuple[str, dict]] = {}  # check key -> (idempotency key, body)

    def init(self):
        self._app_config = self.model.config_model.app_config
        self._app_settings = self.model.config_model.app_settings
        self._logger = self.model.logging_model.system_logger
        debug = self.model.config_model.app_config_dynamic.app_debug_enabled

        self._store = IdentityStore(self._app_config.AGENT_DIR)
        self._client = AgentApiClient(
            "", timeout=5, verify=self._app_settings.tls_verify, logger=self._logger if debug else None
        )
        self._session_logs = SessionLogOutbox(self._app_config.SESSION_LOG_OUTBOX_FILE, logger=self._logger)
        self.reload_identity()

    # ------------------------------------------------------------------ identity

    @property
    def client(self) -> AgentApiClient:
        return self._client

    @property
    def identity(self) -> Optional[AgentIdentity]:
        return self._client.identity if self._client else None

    @property
    def is_enrolled(self) -> bool:
        return bool(self._client and self._client.is_enrolled)

    @property
    def backend_url(self) -> str:
        return self.identity.backend_url if self.identity else ""

    @property
    def frontend_url(self) -> str:
        return self._app_settings.frontend_url

    def reload_identity(self) -> bool:
        """(Re)load the enrolled identity and key from disk; returns True when usable."""
        with self._lock:
            identity, key = load_credentials(self._store)
            if identity is None or not identity.is_enrolled:
                self._client.set_credentials(None, None)
                self._logger.warning("[Backend] Not enrolled. Run `LabMango enroll --url ... --agent-uid ...`.")
                return False
            if key is None:
                self._client.set_credentials(None, None)
                self._logger.error(f"[Backend] Key of agent {identity.agent_uid} is missing; enroll again.")
                return False
            self._client.base_url = identity.backend_url
            self._client.verify = self._app_settings.tls_verify
            self._client.set_credentials(identity, key)
            self._logger.info(f"[Backend] Agent {identity.agent_uid} on {identity.backend_key}.")
            return True

    def _enrolled_client(self) -> AgentApiClient:
        if not self.is_enrolled and not self.reload_identity():
            raise agent_errors.NotEnrolled(
                "This computer is not enrolled with Lab Mango. Ask an administrator to enroll it."
            )
        return self._client

    # ------------------------------------------------------------------ health

    def check_alive(self) -> bool:
        if not self.backend_url:
            return False
        try:
            self._client.get_info()
            return True
        except agent_errors.AgentApiError:
            return False

    def check_frontend_alive(self) -> bool:
        try:
            requests.get(self.frontend_url, verify=self._app_settings.tls_verify, timeout=3)
            return True
        except requests.RequestException:
            return False

    @task(schedule=TaskScheduleConfig.AGENT_HEARTBEAT, heavy=True)
    def send_heartbeat(self) -> bool:
        """Liveness for operators, then deliver any queued session logs."""
        if not self.is_enrolled and not self.reload_identity():
            return False
        try:
            self._client.heartbeat()
        except agent_errors.Unauthenticated as e:
            self._logger.error(f"[Backend] Heartbeat rejected (agent revoked, or clock off by > 5 min): {e}")
            return False
        except agent_errors.AgentApiError as e:
            self._logger.warning(f"[Backend] Heartbeat failed: {e}")
            return False
        self.flush_session_logs()
        return True

    # ------------------------------------------------------------------ activity & session logs

    def report_activity(self, status: ActivityStatus, session: Optional[RemoteSession]) -> bool:
        """``PATCH /agent/equipment/activity``. The backend derives inactive/offline times itself."""
        report = ActivityReport(
            status=status.value,
            booking_code=(session.booking_code or "") if session else "",
            remote_user=session.remote_user.lower() if session else "",
            remote_user_display_name=session.remote_user_display_name if session else "",
            remote_computer=session.remote_computer if session else "",
            remote_ip=session.remote_ip if session else "",
        )
        try:
            self._enrolled_client().report_activity(report)
            return True
        except agent_errors.AgentApiError as e:
            self._logger.warning(f"[Backend] Activity report failed: {e}")
            return False

    def queue_session_log(
        self, session: RemoteSession, login_at: datetime, logout_at: datetime, active_seconds: float
    ) -> str:
        """Persist a finished session for delivery (``POST /agent/session-logs``); returns its event key."""
        event_key = str(uuid.uuid4())
        self._session_logs.add(
            {
                "event_key": event_key,
                "login_at": _aware_iso(login_at),
                "logout_at": _aware_iso(logout_at),
                "active_duration_seconds": max(0.0, float(active_seconds)),
                "remote_user": (session.remote_user or "-")[:255],
                "remote_ip": _ip_or_none(session.remote_ip),
                "remote_host": (session.remote_computer or "")[:255] or None,
                "booking_code": session.booking_code or None,
                "agent_version": str(self._app_config.APP_VERSION)[:64],
            }
        )
        return event_key

    def flush_session_logs(self) -> int:
        return self._session_logs.flush(self._client) if self.is_enrolled else 0

    # ------------------------------------------------------------------ bookings

    def validate_booking(self, booking_code: str) -> Booking:
        """Read-only eligibility check (does not check in).

        Raises LookupError when the code cannot be used on this computer now: unknown, not
        approved, cancelled, finished, another bench or outside its window. The backend gives one
        answer for all of these on purpose.
        """
        result = self._enrolled_client().validate_booking(booking_code)
        if not result.ok:
            raise LookupError("Booking cannot be used on this computer now")
        return _booking(result, BookingStatus.RESERVED)

    def get_running_booking(self, booking_code: str) -> Optional[Booking]:
        """The booking while it is still running here; ``None`` once completed, cancelled or ended."""
        result = self._enrolled_client().validate_booking(booking_code)
        return _booking(result, BookingStatus.IN_PROGRESS) if result.ok else None

    def check_in_booking(self, booking_code: str) -> Booking:
        """Start (or resume) the booking for this login; safe to repeat."""
        result = self._enrolled_client().check_in_booking(booking_code)
        if not result.ok:
            raise PermissionError("Booking cannot be started on this computer now")
        return _booking(result, BookingStatus.IN_PROGRESS)

    def complete_booking(self, booking_code: str) -> None:
        if not self._enrolled_client().complete_booking(booking_code).ok:
            raise RuntimeError("Booking could not be ended (it may already be finished)")

    def extend_booking(self, booking_code: str, ends_at: datetime) -> Booking:
        """Move the end of a running booking. Raises ValueError with a readable reason."""
        try:
            result = self._enrolled_client().extend_booking(booking_code, _aware_iso(ends_at))
        except agent_errors.BookingExtensionRejected as e:
            raise ValueError(_extension_reason(e)) from e
        if not result.ok:
            raise RuntimeError("Booking could not be extended (no running booking on this computer)")
        return _booking(result, BookingStatus.IN_PROGRESS)

    # ------------------------------------------------------------------ capabilities

    CAPABILITIES_TTL_S = 3600

    def supports(self, capability: str) -> bool:
        """Whether this backend serves a capability (``GET /agent/info``, cached for an hour)."""
        if time.monotonic() - self._capabilities_read_at > self.CAPABILITIES_TTL_S or not self._capabilities:
            try:
                self._capabilities = self._client.get_info().capabilities
                self._capabilities_read_at = time.monotonic()
            except agent_errors.AgentApiError:
                return capability in self._capabilities
        return capability in self._capabilities

    # ------------------------------------------------------------------ license checks

    def fetch_license_checks(self) -> Optional[list]:
        """Raw check configurations for this computer, ``None`` when unchanged since the last fetch."""
        items, self._license_checks_etag = self._enrolled_client().get_license_checks(self._license_checks_etag)
        return items

    def report_license_check(self, result: CheckResult) -> bool:
        """Send one check run (a newer run replaces an unsent older one); retried on the next call."""
        body = result_body(result, sequence=int(time.time() * 1000))
        with self._lock:
            self._pending_license_reports[result.check_key] = (str(uuid.uuid4()), body)
        return self.flush_license_reports()

    def flush_license_reports(self) -> bool:
        if not self.is_enrolled:
            return False
        with self._lock:
            pending = dict(self._pending_license_reports)
        ok = True
        for check_key, (idempotency_key, body) in pending.items():
            try:
                self._client.report_license_check(check_key, body, idempotency_key)
            except (agent_errors.Unauthenticated, agent_errors.NotEnrolled) as e:
                self._logger.info(f"[Licenses] Report for {check_key} deferred: {e}")
                ok = False
                continue
            except agent_errors.AgentApiError as e:
                if not e.is_retryable:
                    # 404: the check no longer runs here; 409/422: the backend refuses this run for good.
                    self._logger.warning(f"[Licenses] Report for {check_key} dropped: {e}")
                    with self._lock:
                        if self._pending_license_reports.get(check_key, (None,))[0] == idempotency_key:
                            del self._pending_license_reports[check_key]
                    continue
                self._logger.info(f"[Licenses] Report for {check_key} deferred: {e}")
                ok = False
                continue
            with self._lock:
                if self._pending_license_reports.get(check_key, (None,))[0] == idempotency_key:
                    del self._pending_license_reports[check_key]
        return ok

    # ------------------------------------------------------------------ device monitoring

    def device_observation_reporter(self, collector_key: str) -> DeviceObservationReporter:
        return DeviceObservationReporter(
            self._client,
            os.path.join(self._app_config.AGENT_DIR, f"observations_{collector_key}.json"),
            collector_key=collector_key,
            logger=self._logger,
        )


# ---------------------------------------------------------------------- helpers


def _booking(result: BookingResult, status: BookingStatus) -> Booking:
    return Booking(
        booking_code=result.booking_code,
        booked_for=(result.booked_for or "").lower(),
        starts_at=_local_minutes(result.starts_at),
        ends_at=_local_minutes(result.ends_at),
        status=status,
    )


def _aware_iso(value: datetime) -> str:
    """Naive datetimes are local wall-clock time; send them with their UTC offset."""
    return (value.astimezone() if value.tzinfo is None else value).isoformat()


def _local_minutes(value: Optional[datetime]) -> Optional[datetime]:
    """Backend times → naive local time (the UI and session timer work in local time)."""
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


def _extension_reason(error: agent_errors.BookingExtensionRejected) -> str:
    message = _EXTENSION_REASONS.get(error.reason, str(error.args[0]))
    limit = _local_minutes(error.limit_at)
    return f"{message}\nLimit: {limit:%Y-%m-%d %H:%M}" if limit else message
