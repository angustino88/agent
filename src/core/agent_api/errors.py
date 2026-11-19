"""Typed failures of the agent API client.

The backend error envelope is ``{"error": {"code", "message", "details", "request_id"}}``.
Messages from the backend are kept short and never include request bodies (they may hold codes).
"""

from __future__ import annotations

from typing import Any, Optional


class AgentApiError(Exception):
    """Base class. ``status`` is ``None`` when no HTTP response was received."""

    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        code: str = "",
        details: Optional[list] = None,
        request_id: str = "",
        retry_after: Optional[float] = None,
    ):
        super().__init__(message)
        self.status = status
        self.code = code
        self.details = details or []
        self.request_id = request_id
        self.retry_after = retry_after

    @property
    def is_retryable(self) -> bool:
        """Outcome unknown or transient: keep the same write intent and retry later."""
        return self.status is None or self.status == 429 or self.status >= 500

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.status is not None:
            parts.append(f"status={self.status}")
        if self.code:
            parts.append(f"code={self.code}")
        if self.request_id:
            parts.append(f"request_id={self.request_id}")
        return " ".join(parts)


class NotEnrolled(AgentApiError):
    """No usable identity/key on this computer; run ``enroll`` first."""


class BackendUnreachable(AgentApiError):
    """Connection failure or timeout; the request outcome is unknown."""


class Unauthenticated(AgentApiError):
    """401: bad/stale/replayed signature, or the agent is not active (revoked/decommissioned)."""


class EnrollmentRejected(AgentApiError):
    """400 on enrollment: grant invalid/expired/used or proof rejected."""


class EnrollmentConflict(AgentApiError):
    """409 on enrollment: key already enrolled or the equipment already has a live agent."""


class BackendMismatch(AgentApiError):
    """The backend at the URL is not the one this identity is enrolled with."""


class ValidationFailed(AgentApiError):
    """422: unknown field or invalid value."""


class Conflict(AgentApiError):
    """409 outside enrollment (e.g. equipment deleted, event id reused with other content)."""


class RateLimited(AgentApiError):
    """429; ``retry_after`` holds the server hint in seconds when present."""


class PayloadTooLarge(AgentApiError):
    """413."""


class ServerError(AgentApiError):
    """5xx; outcome unknown."""


class BookingExtensionRejected(AgentApiError):
    """Extension refused. ``reason`` is one of already_ended, not_later, too_short,
    needs_approval, bench_not_in_service, bench_not_free; ``limit_at`` is the bound."""

    def __init__(self, message: str, *, reason: str, limit_at: Any = None, **kwargs: Any):
        super().__init__(message, **kwargs)
        self.reason = reason
        self.limit_at = limit_at
