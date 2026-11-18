"""HTTP client with request logging and token refresh."""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from itertools import count
from typing import Any, Callable, Iterable, Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global monotonic counter shared by ALL ClientRequest instances
_GLOBAL_REQUEST_SEQ = count(1)


class ClientResponse:
    """Wrapper around a ``requests.Response`` with convenience properties."""

    __slots__ = ('_success', 'data', '_response')

    def __init__(self, success: bool, data: Any, response: Optional[requests.Response]):
        self._success = success
        self.data = data
        self._response = response

    @property
    def success(self) -> bool:
        return self._success

    @property
    def response(self) -> Optional[requests.Response]:
        return self._response

    @property
    def status_code(self) -> Optional[int]:
        return getattr(self._response, "status_code", None)

    @property
    def text(self) -> Optional[str]:
        return getattr(self._response, "text", None)

    @property
    def json(self) -> Any:
        if not self._response:
            return None
        try:
            return self._response.json()
        except Exception:
            return None

    @property
    def ok(self) -> bool:
        """Alias for :pyattr:`success`."""
        return self._success

    @property
    def headers(self) -> dict[str, str]:
        """Response headers (empty dict when no response)."""
        if self._response is not None:
            return dict(self._response.headers)
        return {}

    def __repr__(self) -> str:
        return (
            f"<ClientResponse success={self.success} "
            f"status={self.status_code} "
            f"data_type={type(self.data).__name__}>"
        )

    def __bool__(self) -> bool:
        return self._success


class ClientRequest:
    """Reusable HTTP client with logging, token refresh and convenience verbs."""

    _INSTANCE_SEQ_LOCK = threading.Lock()
    _INSTANCE_SEQ = 0

    def __init__(
        self,
        base_url: str,
        auth_value: str | None = None,
        auth_scheme: str = "Api-key",
        logger: Any = None,
        printer: Any = None,
        token_refresh_callback: Optional[Callable[[], bool]] = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._auth_value = auth_value
        self._auth_scheme = auth_scheme
        self._logger = logger
        self._printer = printer
        self._refresh_token: str | None = None
        self._token_refresh_callback = token_refresh_callback

        with ClientRequest._INSTANCE_SEQ_LOCK:
            self._instance_id = ClientRequest._INSTANCE_SEQ
            ClientRequest._INSTANCE_SEQ += 1

        self._lock = threading.Lock()
        self._log_lock = threading.Lock()
        self._session = requests.Session()

    # ---- Properties --------------------------------------------------------

    @property
    def base_url(self) -> str:
        return self._base_url

    @base_url.setter
    def base_url(self, value: str) -> None:
        self._base_url = (value or "").rstrip("/")

    @property
    def auth_value(self) -> str | None:
        return self._auth_value

    @auth_value.setter
    def auth_value(self, value: str | None) -> None:
        self._auth_value = value

    @property
    def auth_scheme(self) -> str:
        return self._auth_scheme

    @auth_scheme.setter
    def auth_scheme(self, value: str) -> None:
        self._auth_scheme = value

    @property
    def refresh_token(self) -> str | None:
        return self._refresh_token

    @refresh_token.setter
    def refresh_token(self, value: str | None) -> None:
        self._refresh_token = value

    # ---- Internals ---------------------------------------------------------

    def _next_req_id(self) -> str:
        global_id = next(_GLOBAL_REQUEST_SEQ)
        return f"{global_id}#c{self._instance_id}"

    def _get_headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self._auth_value and self._auth_scheme:
            h["Authorization"] = f"{self._auth_scheme} {self._auth_value}"
        return h

    @staticmethod
    def _format_ts() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    @staticmethod
    def _truncate(s: str, limit: int = 400) -> str:
        return s if len(s) <= limit else f"{s[:limit]}...(+{len(s) - limit} chars)"

    @staticmethod
    def _safe_json(obj: Any) -> str:
        try:
            return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)
        except Exception:
            return str(obj)

    def _emit(self, msg: str, level: str = "info") -> None:
        if self._logger:
            log_fn = getattr(self._logger, level, self._logger.info)
            try:
                log_fn(msg)
            except Exception:
                pass
        if self._printer:
            self._printer(msg)

    # ---- Logging -----------------------------------------------------------

    def _log_request(self, req_id: str, attempt: int, method: str, url: str, body: dict | None) -> None:
        ts = self._format_ts()
        body_repr = "{}" if body is None else self._truncate(self._safe_json(body))
        self._emit(
            f"[API SEND] ts={ts} id={req_id} attempt={attempt} "
            f"method={method.upper()} url={url} body={body_repr}",
            "info",
        )

    def _log_response(
        self,
        req_id: str,
        attempt: int,
        method: str,
        url: str,
        resp: ClientResponse,
        elapsed_ms: float,
    ) -> None:
        ts = self._format_ts()
        snippet = ""
        if not resp.success and resp.text:
            snippet = self._truncate(resp.text.replace("\n", " "), 300)
        self._emit(
            f"[API RECV] ts={ts} id={req_id} attempt={attempt} method={method.upper()} "
            f"status={resp.status_code} success={resp.success} time_ms={elapsed_ms:.1f} "
            f"{'err_snip=' + snippet if snippet else ''}",
            "info",
        )

    # ---- Response parsing --------------------------------------------------

    @staticmethod
    def _parse_response(r: requests.Response) -> Any:
        try:
            parsed = r.json()
            return parsed.get("data", parsed) if isinstance(parsed, dict) else parsed
        except Exception:
            return r.text

    # ---- Low-level send ----------------------------------------------------

    def _send_once(self, method: str, url: str, body: dict | None, timeout: int | None) -> ClientResponse:
        send_body = {} if (body is None and method.upper() in ("POST", "PUT", "PATCH", "DELETE")) else body
        r = self._session.request(
            method=method,
            url=url,
            data=json.dumps(send_body) if send_body is not None else None,
            headers=self._get_headers(),
            verify=False,
            timeout=timeout,
        )
        return ClientResponse(False, self._parse_response(r), r)

    # ---- Public request ----------------------------------------------------

    def request(
        self,
        method: str,
        endpoint: str,
        body: dict | None = None,
        expected_status: Iterable[int] = (200, 201, 204),
        timeout: int | None = 10,
        allow_token_refresh: bool = True,
    ) -> ClientResponse:
        """Send an HTTP request and return a :class:`ClientResponse`."""
        url = f"{self._base_url}{endpoint}"
        req_id = self._next_req_id()

        attempt = 1
        self._log_request(req_id, attempt, method, url, body)
        start = time.time()
        resp = self._send_once(method, url, body, timeout)
        resp._success = resp.status_code in expected_status
        elapsed_ms = (time.time() - start) * 1000
        self._log_response(req_id, attempt, method, url, resp, elapsed_ms)

        # Token-refresh retry (single attempt).
        # _lock ensures only one thread triggers a refresh at a time; other
        # threads that also received 401/403 will re-use the fresh token on
        # their own retry rather than issuing a redundant refresh.
        if (
            allow_token_refresh
            and resp.status_code in (401, 403)
            and self._token_refresh_callback
        ):
            with self._lock:
                try:
                    if self._token_refresh_callback():
                        attempt = 2
                        self._log_request(req_id, attempt, method, url, body)
                        start = time.time()
                        resp = self._send_once(method, url, body, timeout)
                        resp._success = resp.status_code in expected_status
                        elapsed_ms = (time.time() - start) * 1000
                        self._log_response(req_id, attempt, method, url, resp, elapsed_ms)
                except Exception:
                    pass

        return resp

    # ---- Convenience verbs -------------------------------------------------

    def get(self, endpoint: str, expected_status: Iterable[int] = (200,),
            timeout: int | None = 10, allow_token_refresh: bool = True) -> ClientResponse:
        return self.request("GET", endpoint, expected_status=expected_status,
                            timeout=timeout, allow_token_refresh=allow_token_refresh)

    def post(self, endpoint: str, body: dict | None = None, expected_status: Iterable[int] = (200, 201),
             timeout: int | None = 10, allow_token_refresh: bool = True) -> ClientResponse:
        return self.request("POST", endpoint, body=body, expected_status=expected_status,
                            timeout=timeout, allow_token_refresh=allow_token_refresh)

    def put(self, endpoint: str, body: dict | None = None, expected_status: Iterable[int] = (200, 204),
            timeout: int | None = 10, allow_token_refresh: bool = True) -> ClientResponse:
        return self.request("PUT", endpoint, body=body, expected_status=expected_status,
                            timeout=timeout, allow_token_refresh=allow_token_refresh)

    def patch(self, endpoint: str, body: dict | None = None, expected_status: Iterable[int] = (200, 204),
              timeout: int | None = 10, allow_token_refresh: bool = True) -> ClientResponse:
        return self.request("PATCH", endpoint, body=body, expected_status=expected_status,
                            timeout=timeout, allow_token_refresh=allow_token_refresh)

    def delete(self, endpoint: str, body: dict | None = None, expected_status: Iterable[int] = (200, 204),
               timeout: int | None = 10, allow_token_refresh: bool = True) -> ClientResponse:
        return self.request("DELETE", endpoint, body=body, expected_status=expected_status,
                            timeout=timeout, allow_token_refresh=allow_token_refresh)