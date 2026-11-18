"""HTTP client for the backend's device API (``/agent/...``).

Every device request is signed with the enrolled Ed25519 key (``X-Agent-*`` headers). The signed
path is the path the backend sees: when the backend sits behind a Router prefix
(``https://host/api/dept_a``), Nginx strips the prefix, so the client signs ``/agent/...`` only.

The body is serialized once and the exact bytes that are signed are the bytes sent. Redirects are
never followed, so signatures and grants are never forwarded to another origin.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any, Callable, Iterable, Optional

import requests

from . import errors
from .identity import AgentIdentity
from .models import (
    ActivityReport,
    AgentInfo,
    BookingResult,
    EnrolledAgent,
    Heartbeat,
    MonitoringPolicy,
    ObservationAck,
    SessionLogAck,
    parse_datetime,
)
from .signing import AgentKey, new_nonce, request_message

PATH_INFO = "/agent/info"
PATH_ENROLLMENTS = "/agent/enrollments"
PATH_HEARTBEAT = "/agent/heartbeat"
PATH_ACTIVITY = "/agent/equipment/activity"
PATH_SESSION_LOGS = "/agent/session-logs"
PATH_MONITORING_POLICY = "/agent/monitoring-policy"
PATH_DEVICE_OBSERVATIONS = "/agent/device-observations/actions/report"
PATH_BOOKING_VALIDATE = "/agent/bookings/actions/validate"
PATH_BOOKING_CHECK_IN = "/agent/bookings/actions/check-in"
PATH_BOOKING_COMPLETE = "/agent/bookings/actions/complete"
PATH_BOOKING_EXTEND = "/agent/bookings/actions/extend"

_ERROR_BY_STATUS: dict[int, type[errors.AgentApiError]] = {
    401: errors.Unauthenticated,
    403: errors.Unauthenticated,
    409: errors.Conflict,
    413: errors.PayloadTooLarge,
    422: errors.ValidationFailed,
    429: errors.RateLimited,
}


class ApiResult:
    __slots__ = ("status", "data", "headers")

    def __init__(self, status: int, data: Any, headers: dict[str, str]):
        self.status = status
        self.data = data
        self.headers = headers


class AgentApiClient:
    """Thread-safe signed client. Create once; call :meth:`set_credentials` after enrollment."""

    def __init__(
        self,
        base_url: str,
        *,
        identity: Optional[AgentIdentity] = None,
        key: Optional[AgentKey] = None,
        timeout: float = 10.0,
        verify: bool | str = True,
        session: Optional[requests.Session] = None,
        logger: Any = None,
        clock: Callable[[], float] = time.time,
    ):
        self._base_url = (base_url or "").rstrip("/")
        self._identity = identity
        self._key = key
        self._timeout = timeout
        self._verify = verify
        self._session = session or requests.Session()
        self._logger = logger
        self._clock = clock
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ configuration

    @property
    def base_url(self) -> str:
        return self._base_url

    @base_url.setter
    def base_url(self, value: str) -> None:
        self._base_url = (value or "").rstrip("/")

    @property
    def verify(self) -> bool | str:
        return self._verify

    @verify.setter
    def verify(self, value: bool | str) -> None:
        self._verify = value

    @property
    def identity(self) -> Optional[AgentIdentity]:
        return self._identity

    @property
    def is_enrolled(self) -> bool:
        return bool(self._identity and self._identity.is_enrolled and self._key)

    def set_credentials(self, identity: Optional[AgentIdentity], key: Optional[AgentKey]) -> None:
        with self._lock:
            self._identity = identity
            self._key = key

    # ------------------------------------------------------------------ transport

    def _log(self, level: str, message: str) -> None:
        if self._logger is not None:
            try:
                getattr(self._logger, level, self._logger.info)(message)
            except Exception:
                pass

    def _signed_headers(self, method: str, path: str, body: bytes) -> dict[str, str]:
        with self._lock:
            identity, key = self._identity, self._key
        if identity is None or key is None or not identity.is_enrolled:
            raise errors.NotEnrolled("This computer is not enrolled with a Lab Mango backend.")
        timestamp = str(int(self._clock()))
        nonce = new_nonce()
        message = request_message(
            backend_id=identity.backend_key,
            agent_uid=identity.agent_uid,
            method=method,
            path=path,
            timestamp=timestamp,
            nonce=nonce,
            body=body,
        )
        return {
            "X-Agent-Id": identity.agent_uid,
            "X-Agent-Timestamp": timestamp,
            "X-Agent-Nonce": nonce,
            "X-Agent-Signature": key.sign(message),
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        signed: bool = True,
        headers: Optional[dict[str, str]] = None,
        expected: Iterable[int] = (200,),
        timeout: Optional[float] = None,
    ) -> ApiResult:
        method = method.upper()
        body = b"" if json_body is None else json.dumps(json_body, separators=(",", ":")).encode("utf-8")
        send_headers = {"Accept": "application/json"}
        if json_body is not None:
            send_headers["Content-Type"] = "application/json"
        if headers:
            send_headers.update(headers)
        if signed:
            send_headers.update(self._signed_headers(method, path, body))

        url = f"{self._base_url}{path}"
        started = time.monotonic()
        try:
            response = self._session.request(
                method,
                url,
                data=body if body else None,
                headers=send_headers,
                timeout=timeout or self._timeout,
                verify=self._verify,
                allow_redirects=False,
            )
        except requests.RequestException as error:
            self._log("warning", f"[AgentAPI] {method} {path} failed: {type(error).__name__}")
            raise errors.BackendUnreachable(f"{method} {path}: {type(error).__name__}") from error

        elapsed_ms = (time.monotonic() - started) * 1000
        self._log("info", f"[AgentAPI] {method} {path} status={response.status_code} time_ms={elapsed_ms:.0f}")

        payload: Any = None
        if response.content:
            try:
                payload = response.json()
            except ValueError:
                payload = None
        result_headers = dict(response.headers)
        if response.status_code in tuple(expected):
            data = payload.get("data", payload) if isinstance(payload, dict) else payload
            return ApiResult(response.status_code, data, result_headers)
        raise self._error(method, path, response.status_code, payload, result_headers)

    @staticmethod
    def _error(method: str, path: str, status: int, payload: Any, headers: dict[str, str]) -> errors.AgentApiError:
        body = payload.get("error") if isinstance(payload, dict) else None
        body = body if isinstance(body, dict) else {}
        code = str(body.get("code", "") or "")
        message = str(body.get("message", "") or "") or f"{method} {path} failed"
        retry_after: Optional[float] = None
        if status == 429:
            try:
                retry_after = float(headers.get("Retry-After", ""))
            except ValueError:
                retry_after = None
        if 300 <= status < 400:
            cls: type[errors.AgentApiError] = errors.AgentApiError
            message = f"{method} {path}: unexpected redirect (not followed)"
        elif status >= 500:
            cls = errors.ServerError
        else:
            cls = _ERROR_BY_STATUS.get(status, errors.AgentApiError)
        return cls(
            message[:300],
            status=status,
            code=code,
            details=body.get("details") if isinstance(body.get("details"), list) else [],
            request_id=str(body.get("request_id", "") or ""),
            retry_after=retry_after,
        )

    # ------------------------------------------------------------------ discovery & enrollment

    def get_info(self) -> AgentInfo:
        return AgentInfo.from_data(self.request("GET", PATH_INFO, signed=False).data or {})

    def enroll(
        self,
        *,
        grant: str,
        public_key: str,
        proof: str,
        key_storage: str,
        agent_version: str,
        fingerprint: str = "",
    ) -> EnrolledAgent:
        body = {
            "grant": grant,
            "public_key": public_key,
            "proof": proof,
            "key_storage": key_storage,
            "agent_version": agent_version[:64],
            "fingerprint": fingerprint[:128],
        }
        try:
            result = self.request("POST", PATH_ENROLLMENTS, json_body=body, signed=False, expected=(201,))
        except errors.AgentApiError as error:
            if error.status == 400:
                raise errors.EnrollmentRejected(str(error.args[0]), status=400, code=error.code) from None
            if error.status == 409:
                raise errors.EnrollmentConflict(str(error.args[0]), status=409, code=error.code) from None
            raise
        return EnrolledAgent.from_data(result.data or {})

    # ------------------------------------------------------------------ liveness & reporting

    def heartbeat(self) -> Heartbeat:
        data = self.request("POST", PATH_HEARTBEAT, json_body={}).data or {}
        return Heartbeat(status=str(data.get("status", "")), last_seen_at=parse_datetime(data.get("last_seen_at")))

    def report_activity(self, report: ActivityReport) -> dict:
        return self.request("PATCH", PATH_ACTIVITY, json_body=report.to_body()).data or {}

    def record_session_log(self, entry: dict) -> SessionLogAck:
        """``entry`` follows ``AgentSessionLogReport``; reuse the same ``event_key`` on retry."""
        result = self.request("POST", PATH_SESSION_LOGS, json_body=entry, expected=(200, 201))
        data = result.data or {}
        return SessionLogAck(
            id=int(data.get("id", 0) or 0),
            event_key=str(data.get("event_key", entry.get("event_key", ""))),
            created=result.status == 201,
        )

    def get_monitoring_policy(self, etag: str = "") -> Optional[MonitoringPolicy]:
        """Return the policy, or ``None`` when ``etag`` is still current (304)."""
        headers = {"If-None-Match": etag} if etag else None
        result = self.request("GET", PATH_MONITORING_POLICY, headers=headers, expected=(200, 304))
        if result.status == 304:
            return None
        return MonitoringPolicy.from_data(result.data or {}, etag=result.headers.get("ETag", ""))

    def report_device_observations(self, report: dict, idempotency_key: str | uuid.UUID) -> ObservationAck:
        """``report`` follows ``DeviceObservationReport``; reuse ``idempotency_key`` on retry."""
        result = self.request(
            "POST",
            PATH_DEVICE_OBSERVATIONS,
            json_body=report,
            headers={"Idempotency-Key": str(idempotency_key)},
        )
        data = result.data or {}
        disposition = data.get("disposition")
        return ObservationAck(
            batch_key=str(data.get("batch_key", "")),
            sequence=int(data.get("sequence", 0) or 0),
            disposition=disposition.get("value", "") if isinstance(disposition, dict) else str(disposition or ""),
            received_at=parse_datetime(data.get("received_at")),
            replayed=result.headers.get("Idempotency-Replayed", "").lower() == "true",
        )

    # ------------------------------------------------------------------ bookings

    def validate_booking(self, booking_code: str) -> BookingResult:
        data = self.request("POST", PATH_BOOKING_VALIDATE, json_body={"booking_code": booking_code}).data or {}
        return BookingResult.from_data(data, "is_eligible")

    def check_in_booking(self, booking_code: str) -> BookingResult:
        data = self.request("POST", PATH_BOOKING_CHECK_IN, json_body={"booking_code": booking_code}).data or {}
        return BookingResult.from_data(data, "is_checked_in")

    def complete_booking(self, booking_code: str) -> BookingResult:
        data = self.request("POST", PATH_BOOKING_COMPLETE, json_body={"booking_code": booking_code}).data or {}
        return BookingResult.from_data(data, "is_completed")

    def extend_booking(self, booking_code: str, ends_at: str) -> BookingResult:
        """``ends_at`` is an ISO 8601 timestamp with offset. Raises :class:`BookingExtensionRejected`."""
        try:
            data = self.request(
                "POST", PATH_BOOKING_EXTEND, json_body={"booking_code": booking_code, "ends_at": ends_at}
            ).data or {}
        except (errors.Conflict, errors.ValidationFailed) as error:
            detail = next((d for d in error.details if isinstance(d, dict) and d.get("code")), None)
            if detail is not None:
                raise errors.BookingExtensionRejected(
                    str(detail.get("message") or error.args[0]),
                    reason=str(detail.get("code")),
                    limit_at=parse_datetime(detail.get("limit_at")),
                    status=error.status,
                    code=error.code,
                    request_id=error.request_id,
                ) from None
            raise
        return BookingResult.from_data(data, "is_extended")
