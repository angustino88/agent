"""Lab Mango endpoints of the service gateway (login, configuration, OTP, updates)."""

from .labmango_gateway import LabMangoGatewayService
from .server_url import ServerUrlUnavailable, resolve_server_url

__all__ = ["LabMangoGatewayService", "ServerUrlUnavailable", "resolve_server_url"]
