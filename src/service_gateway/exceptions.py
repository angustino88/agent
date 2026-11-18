"""Service Gateway — exception hierarchy."""
from __future__ import annotations

from typing import Any


class GatewayError(Exception):
    """Base for all service gateway errors."""


class GatewayAuthError(GatewayError):
    """Raised when authentication or token refresh fails."""


class GatewayConnectionError(GatewayError):
    """Raised when a transport-level error occurs (timeout, refused, …)."""


class GatewayTimeoutError(GatewayConnectionError):
    """Raised when every attempted URL candidate times out."""


class GatewayProtocolExhaustedError(GatewayConnectionError):
    """Raised when every protocol candidate (HTTPS then HTTP) has been tried
    and all failed with a transport error."""


class GatewayResponseError(GatewayError):
    """Raised when the server returns an unexpected (non-success) HTTP status.

    The request was delivered successfully (no transport error), but the
    response status was not in the ``expected_status`` set and the caller
    opted into exception-based error handling via
    :meth:`~service_gateway.service.BaseGatewayService._raise_for_status`.

    Attributes
    ----------
    status_code:
        HTTP status code returned by the server.
    response:
        The raw response object that triggered the error (a
        :class:`~src.utils.http_client.ClientResponse` instance).
    """

    def __init__(self, message: str, status_code: int, response: Any = None) -> None:
        super().__init__(message)
        self.status_code: int = status_code
        self.response: Any = response

