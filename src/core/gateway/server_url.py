"""Where this computer's agent talks to: the server URL the service gateway publishes.

Lab computers reach the department backend (or the Router in front of it) through the address
the gateway hands out in ``prod-server-config`` (``backend_url``). The web app therefore never
shows a backend address: ``enroll`` asks the gateway, and ``--url`` is only an override.
"""

from __future__ import annotations

import socket
from typing import Callable, Optional

from src.service_gateway import GatewayClient

from .labmango_gateway import LabMangoGatewayService


class ServerUrlUnavailable(RuntimeError):
    """The gateway could not be reached or published no server URL."""


def resolve_server_url(
    gateway_url: str,
    *,
    computer_name: Optional[str] = None,
    verify: bool | str = False,
    timeout: int = 10,
    client_factory: Callable[..., GatewayClient] = GatewayClient,
) -> str:
    """Log in to the gateway as this computer and return its published ``backend_url``."""
    name = computer_name or socket.gethostname()
    try:
        client = client_factory(
            base_url=gateway_url,
            auth_scheme="Bearer",
            verify=verify,
            allow_http_fallback=verify is False,
        )
        service = LabMangoGatewayService(client, name, f"AGENT_{name}")
        login = service.login(timeout=timeout)
        token = (login.data or {}).get("access") if login and login.success else None
        if not token:
            raise ServerUrlUnavailable("gateway login failed")
        client.auth_value = token.strip()
        config = service.get_prod_server_config(timeout=timeout)
    except ServerUrlUnavailable:
        raise
    except Exception as error:  # network, TLS, malformed response
        raise ServerUrlUnavailable(f"gateway unreachable: {type(error).__name__}") from error
    data = config.data if config and config.success and isinstance(config.data, dict) else {}
    url = str(data.get("backend_url") or "").strip()
    if not url:
        raise ServerUrlUnavailable("the gateway publishes no server URL (prod-server-config backend_url)")
    return url.rstrip("/")
