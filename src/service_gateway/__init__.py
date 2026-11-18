"""Service Gateway — public API.

Re-exports the most commonly used symbols so consumers can write::

    from src.service_gateway import GatewayClient, StandardGatewayService
    from src.service_gateway import BaseGatewayService
    from src.service_gateway import GatewayError, GatewayConnectionError
"""

from .exceptions import (
    GatewayAuthError,
    GatewayConnectionError,
    GatewayError,
    GatewayProtocolExhaustedError,
    GatewayResponseError,
    GatewayTimeoutError,
)
from .gateway import GatewayClient
from .models import LoginResult, PackageInfo, PackageUpdateResult, TokenRefreshResult
from .retry import RetryPolicy
from .service import BaseGatewayService
from .standard import StandardGatewayService

__all__ = [
    # Core
    "GatewayClient",
    "BaseGatewayService",
    "StandardGatewayService",
    "RetryPolicy",
    # Models
    "LoginResult",
    "TokenRefreshResult",
    "PackageInfo",
    "PackageUpdateResult",
    # Exceptions
    "GatewayError",
    "GatewayAuthError",
    "GatewayConnectionError",
    "GatewayTimeoutError",
    "GatewayProtocolExhaustedError",
    "GatewayResponseError",
]
