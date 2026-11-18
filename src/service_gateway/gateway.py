"""Service Gateway — GatewayClient.

A thin wrapper around :class:`~src.utils.http_client.ClientRequest` that adds:

* **HTTPS-first protocol selection** — builds two URL candidates (HTTPS, HTTP)
  from whatever scheme (or no scheme) is given in *base_url*.
* **Automatic protocol fallback** — if a request raises a transport-level
  :class:`requests.RequestException`, the client switches to the next
  candidate URL and retries once.
* **Configurable retry policy** — optional :class:`~.retry.RetryPolicy` adds
  exponential back-off retries on transient server errors (429, 503 …) and/or
  on connection failures, on top of the protocol-switch retry.
* **Health-check across all candidates** — :meth:`check_alive` tries each
  URL in order and updates the active URL to the first reachable one.
* **Resource management** — :meth:`close` releases the underlying session.

All HTTP verbs delegate to the underlying :class:`ClientRequest` so the
public interface is identical from the caller's perspective.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable, Optional
from urllib.parse import urlsplit, urlunsplit

import requests

from ..utils.http_client import ClientRequest, ClientResponse
from .exceptions import GatewayConnectionError, GatewayProtocolExhaustedError, GatewayTimeoutError
from .retry import RetryPolicy


class GatewayClient:
    """Protocol-aware HTTP client with HTTPS-first / HTTP fallback.

    Parameters
    ----------
    base_url:
        Configured URL for the gateway.  May be provided with or without a
        scheme (e.g. ``"http://host:8080"`` or just ``"host:8080"``).  The
        client always *tries HTTPS first* regardless of the configured scheme.
    auth_value:
        Initial bearer / API-key token value.
    auth_scheme:
        Token prefix used in the ``Authorization`` header.
    logger:
        Optional logger; must expose ``.info(msg)`` and ``.warning(msg)``.
    printer:
        Optional callable used for development-mode stdout output.
    token_refresh_callback:
        Called when the server returns 401/403; should return ``True`` on
        success so the original request can be retried.
    retry_policy:
        Optional back-off policy for transient failures.
    verify:
        TLS certificate verification (``False``, ``True`` or a CA bundle path).
        Defaults to ``False`` for backward compatibility.
    allow_http_fallback:
        When ``True`` (default, backward compatible) the client falls back to
        plain HTTP if HTTPS fails.  Set ``False`` once the gateway serves valid
        TLS so credentials are never sent unencrypted.
    """

    def __init__(
        self,
        base_url: str,
        auth_value: Optional[str] = None,
        auth_scheme: str = "Api-key",
        logger: Any = None,
        printer: Any = None,
        token_refresh_callback: Optional[Callable[[], bool]] = None,
        retry_policy: Optional[RetryPolicy] = None,
        verify: bool | str = False,
        allow_http_fallback: bool = True,
    ) -> None:
        self._candidates: list[str] = self._build_candidates(base_url)
        if not allow_http_fallback:
            self._candidates = [c for c in self._candidates if not c.startswith("http://")]
        if not self._candidates:
            raise ValueError(f"GatewayClient: invalid base_url {base_url!r}")
        self._verify = verify

        self._client = ClientRequest(
            base_url=self._candidates[0],
            auth_value=auth_value,
            auth_scheme=auth_scheme,
            logger=logger,
            printer=printer,
            token_refresh_callback=token_refresh_callback,
            verify=verify,
        )
        self._logger = logger
        self._retry_policy = retry_policy

    # ---- Candidate management ---------------------------------------------

    @property
    def candidates(self) -> list[str]:
        """Ordered list of URL candidates (HTTPS first, then HTTP)."""
        return list(self._candidates)

    def reset_to_primary(self) -> None:
        """Reset the active URL back to the primary (first) candidate.

        Useful after a protocol switch to restore HTTPS preference once the
        primary endpoint is reachable again.
        """
        primary = self._candidates[0]
        if (self._client.base_url or "").rstrip("/") != primary.rstrip("/"):
            self._client.base_url = primary
            self._log_warning(f"[GatewayClient] Reset to primary URL: {primary}")
    @staticmethod
    def _build_candidates(url: str) -> list[str]:
        """Return ``[https_url, http_url]`` from any protocol variant.

        If only a single candidate is distinguishable (e.g. ``localhost``
        without a port that can't be separated from the scheme) the list will
        have one entry.
        """
        raw = (url or "").strip().rstrip("/")
        if not raw:
            return []

        split = urlsplit(raw)
        if not split.netloc and split.path:
            # bare "host:port" — prepend a scheme so urlsplit can parse netloc
            split = urlsplit(f"https://{raw}")

        if not split.netloc:
            return [raw]

        https = urlunsplit(
            ("https", split.netloc, split.path, split.query, split.fragment)
        ).rstrip("/")
        http = urlunsplit(
            ("http", split.netloc, split.path, split.query, split.fragment)
        ).rstrip("/")

        seen: list[str] = []
        for u in (https, http):
            if u and u not in seen:
                seen.append(u)
        return seen

    def _try_switch_protocol(self) -> bool:
        """Switch the active URL to the next candidate; return ``True`` if switched."""
        current = (self._client.base_url or "").rstrip("/")
        for candidate in self._candidates:
            if candidate.rstrip("/") != current:
                self._client.base_url = candidate
                self._log_warning(
                    f"[GatewayClient] Protocol switch: {current} → {candidate}"
                )
                return True
        return False

    def _log_warning(self, msg: str) -> None:
        if self._logger:
            try:
                self._logger.warning(msg)
            except Exception:
                pass

    # ---- Properties (delegates to underlying ClientRequest) ---------------

    @property
    def base_url(self) -> str:
        """Currently active base URL."""
        return self._client.base_url

    @base_url.setter
    def base_url(self, value: str) -> None:
        self._client.base_url = value

    @property
    def auth_value(self) -> Optional[str]:
        return self._client.auth_value

    @auth_value.setter
    def auth_value(self, value: Optional[str]) -> None:
        self._client.auth_value = value

    @property
    def auth_scheme(self) -> str:
        return self._client.auth_scheme

    @auth_scheme.setter
    def auth_scheme(self, value: str) -> None:
        self._client.auth_scheme = value

    @property
    def refresh_token(self) -> Optional[str]:
        return self._client.refresh_token

    @refresh_token.setter
    def refresh_token(self, value: Optional[str]) -> None:
        self._client.refresh_token = value

    # ---- Core request with protocol fallback ------------------------------

    def _request_with_fallback(
        self,
        method: str,
        endpoint: str,
        body: Optional[dict],
        expected_status: Iterable[int],
        timeout: Optional[int],
        allow_token_refresh: bool,
    ) -> ClientResponse:
        """Single attempt with one protocol-switch retry on transport failure."""
        try:
            return self._client.request(
                method, endpoint, body=body,
                expected_status=expected_status,
                timeout=timeout,
                allow_token_refresh=allow_token_refresh,
            )
        except requests.Timeout as exc:
            if not self._try_switch_protocol():
                raise GatewayTimeoutError(
                    f"Request timed out and no alternate candidate available: {exc}"
                ) from exc
            self._log_warning(
                f"[GatewayClient] Timeout ({exc.__class__.__name__}); "
                f"retrying on {self._client.base_url}"
            )
            try:
                return self._client.request(
                    method, endpoint, body=body,
                    expected_status=expected_status,
                    timeout=timeout,
                    allow_token_refresh=allow_token_refresh,
                )
            except requests.Timeout as exc2:
                raise GatewayTimeoutError(
                    f"All candidates timed out. Last error: {exc2}"
                ) from exc2
        except requests.RequestException as exc:
            if not self._try_switch_protocol():
                raise GatewayConnectionError(str(exc)) from exc
            self._log_warning(
                f"[GatewayClient] Transport failure ({exc.__class__.__name__}); "
                f"retrying on {self._client.base_url}"
            )
            try:
                return self._client.request(
                    method, endpoint, body=body,
                    expected_status=expected_status,
                    timeout=timeout,
                    allow_token_refresh=allow_token_refresh,
                )
            except requests.RequestException as exc2:
                raise GatewayProtocolExhaustedError(
                    f"All protocol candidates exhausted. Last error: {exc2}"
                ) from exc2

    def request(
        self,
        method: str,
        endpoint: str,
        body: Optional[dict] = None,
        expected_status: Iterable[int] = (200, 201, 204),
        timeout: Optional[int] = 10,
        allow_token_refresh: bool = True,
    ) -> ClientResponse:
        """Send an HTTP request with automatic protocol fallback and retry.

        On a transport-level error the client switches protocol and retries
        once (built-in behaviour).  When a :class:`~.retry.RetryPolicy` was
        provided at construction, additional retries with exponential back-off
        are applied for transient server errors (e.g. 429, 503) and optionally
        for connection failures.
        """
        policy = self._retry_policy
        max_attempts = 1 + (policy.max_retries if policy else 0)
        last_exc: Optional[Exception] = None
        last_resp: Optional[ClientResponse] = None

        for attempt in range(1, max_attempts + 1):
            if policy and attempt > 1:
                policy.sleep(attempt)
                self._log_warning(
                    f"[GatewayClient] Retry attempt {attempt}/{max_attempts} "
                    f"for {method.upper()} {endpoint}"
                )
            try:
                resp = self._request_with_fallback(
                    method, endpoint, body, expected_status, timeout, allow_token_refresh
                )
                if policy and policy.should_retry_response(resp.status_code) and attempt < max_attempts:
                    last_resp = resp
                    continue
                return resp
            except (GatewayConnectionError, GatewayTimeoutError) as exc:
                if not policy or not policy.retry_on_connection_error or attempt >= max_attempts:
                    raise
                last_exc = exc
                continue

        if last_exc:
            raise last_exc
        return last_resp  # type: ignore[return-value]

    # ---- Convenience verbs ------------------------------------------------

    def get(
        self,
        endpoint: str,
        expected_status: Iterable[int] = (200,),
        timeout: Optional[int] = 10,
        allow_token_refresh: bool = True,
    ) -> ClientResponse:
        return self.request(
            "GET", endpoint,
            expected_status=expected_status,
            timeout=timeout,
            allow_token_refresh=allow_token_refresh,
        )

    def post(
        self,
        endpoint: str,
        body: Optional[dict] = None,
        expected_status: Iterable[int] = (200, 201),
        timeout: Optional[int] = 10,
        allow_token_refresh: bool = True,
    ) -> ClientResponse:
        return self.request(
            "POST", endpoint, body=body,
            expected_status=expected_status,
            timeout=timeout,
            allow_token_refresh=allow_token_refresh,
        )

    def put(
        self,
        endpoint: str,
        body: Optional[dict] = None,
        expected_status: Iterable[int] = (200, 204),
        timeout: Optional[int] = 10,
        allow_token_refresh: bool = True,
    ) -> ClientResponse:
        return self.request(
            "PUT", endpoint, body=body,
            expected_status=expected_status,
            timeout=timeout,
            allow_token_refresh=allow_token_refresh,
        )

    def patch(
        self,
        endpoint: str,
        body: Optional[dict] = None,
        expected_status: Iterable[int] = (200, 204),
        timeout: Optional[int] = 10,
        allow_token_refresh: bool = True,
    ) -> ClientResponse:
        return self.request(
            "PATCH", endpoint, body=body,
            expected_status=expected_status,
            timeout=timeout,
            allow_token_refresh=allow_token_refresh,
        )

    def delete(
        self,
        endpoint: str,
        body: Optional[dict] = None,
        expected_status: Iterable[int] = (200, 204),
        timeout: Optional[int] = 10,
        allow_token_refresh: bool = True,
    ) -> ClientResponse:
        return self.request(
            "DELETE", endpoint, body=body,
            expected_status=expected_status,
            timeout=timeout,
            allow_token_refresh=allow_token_refresh,
        )

    # ---- Health check -----------------------------------------------------

    def check_alive(self, timeout: int = 3) -> bool:
        """Return ``True`` if any candidate URL is reachable.

        Tries each candidate in order (HTTPS first).  Updates the active URL
        to the first reachable one so subsequent requests use it immediately.
        """
        current = (self._client.base_url or "").rstrip("/")
        for url in self._candidates:
            try:
                requests.get(url, verify=self._verify, timeout=timeout)
                if url.rstrip("/") != current:
                    self._client.base_url = url
                    self._log_warning(
                        f"[GatewayClient] Health check: active URL updated {current!r} → {url!r}"
                    )
                return True
            except requests.Timeout:
                self._log_warning(f"[GatewayClient] Health check timed out: {url}")
            except requests.RequestException as exc:
                self._log_warning(f"[GatewayClient] Health check failed: {url} — {exc}")
        return False

    # ---- Resource management ---------------------------------------------

    def close(self) -> None:
        """Release the underlying :class:`requests.Session` and any pooled connections.

        Call this when the gateway client is no longer needed (e.g. on
        application shutdown) to avoid resource leaks.  The instance should
        not be used after calling ``close()``.
        """
        try:
            self._client._session.close()
        except Exception:
            pass

    def __enter__(self) -> "GatewayClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
