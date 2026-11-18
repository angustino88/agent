"""Service Gateway — RetryPolicy.

Declarative, configurable retry strategy for :class:`~.gateway.GatewayClient`.

Example usage::

    from src.service_gateway import GatewayClient, RetryPolicy

    client = GatewayClient(
        base_url="https://my-backend.example.com",
        retry_policy=RetryPolicy(
            max_retries=3,
            backoff_factor=0.5,
            retry_on_status=(429, 502, 503, 504),
        ),
    )
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RetryPolicy:
    """Declarative retry strategy for :class:`~.gateway.GatewayClient`.

    Parameters
    ----------
    max_retries:
        Maximum number of additional attempts after the first try.
        ``0`` (the default) disables the retry loop; the built-in single
        protocol-switch attempt in :class:`GatewayClient` still applies.
    backoff_factor:
        Base delay in seconds between retries.  The actual wait before attempt
        *n* (1-based) is ``backoff_factor * 2^(n-2)`` so the sequence is:
        ``factor × 1``, ``factor × 2``, ``factor × 4``, … . Set to ``0`` for
        no delay.
    retry_on_status:
        HTTP status codes returned by the server that should trigger a retry.
        Defaults to the standard transient-error codes: 429 (rate limited),
        502 / 503 / 504 (gateway / service unavailable).
    retry_on_connection_error:
        When ``True``, transport-level failures
        (:class:`~.exceptions.GatewayConnectionError`,
        :class:`~.exceptions.GatewayTimeoutError`) also enter the retry loop,
        on top of the single protocol-switch attempt already built into
        :class:`GatewayClient`.

    Examples
    --------
    Aggressive retry for a flaky internal service::

        RetryPolicy(max_retries=5, backoff_factor=0.3)

    Rate-limit aware, no delay::

        RetryPolicy(max_retries=2, backoff_factor=0, retry_on_status=(429,))

    Disable retries entirely (default behaviour)::

        RetryPolicy()            # max_retries=0 → no-op
    """

    max_retries: int = 0
    backoff_factor: float = 1.0
    retry_on_status: tuple[int, ...] = (429, 502, 503, 504)
    retry_on_connection_error: bool = True

    def should_retry_response(self, status_code: int | None) -> bool:
        """Return ``True`` when *status_code* is in :attr:`retry_on_status`."""
        return bool(status_code and status_code in self.retry_on_status)

    def sleep(self, attempt: int) -> None:
        """Block for the back-off duration before *attempt* (1-based, ≥ 2).

        No sleep is performed for the very first attempt (``attempt == 1``).
        """
        if self.backoff_factor > 0 and attempt > 1:
            delay = self.backoff_factor * (2 ** (attempt - 2))
            time.sleep(delay)
