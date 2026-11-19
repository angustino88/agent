from typing import Optional
from ...service_gateway.gateway import GatewayClient
from ...service_gateway.standard import StandardGatewayService
from ...utils.http_client import ClientResponse


class LabMangoGatewayService(StandardGatewayService):
    """Lab Mango service-gateway client.

    Extends :class:`StandardGatewayService` with LabMango-specific endpoints
    while inheriting the standard ones (``login``, ``refresh_token``,
    ``get_latest_package``, ``check_package_update``).

    Parameters
    ----------
    client:
        :class:`GatewayClient` configured for the service gateway URL.
    computer_name:
        Name of this computer, sent as ``username`` when authenticating with
        the gateway.
    source:
        Source tag included in request payloads, e.g. ``"AGENT_PC-001"``.
    """

    base_path = "/api/lab-mango"

    def __init__(
        self,
        client: GatewayClient,
        computer_name: str,
        source: str,
    ) -> None:
        super().__init__(client, username=computer_name, source=source)

    @property
    def computer_name(self) -> str:
        """Alias for :pyattr:`username`."""
        return self._username

    # ---- App-specific endpoints -------------------------------------------

    def get_prod_server_config(
        self,
        timeout: Optional[int] = None,
    ) -> ClientResponse:
        """Fetch production server configuration (frontend URL, …)."""
        return self._get("prod-server-config", timeout=timeout)

    def get_otp_master_code(
        self,
        timeout: Optional[int] = None,
    ) -> ClientResponse:
        """Fetch the current OTP master code from the service gateway."""
        return self._get("otp-master-code", timeout=timeout)

    def get_safe_mode_status(
        self,
        timeout: Optional[int] = None,
    ) -> ClientResponse:
        """Fetch the current safe-mode enabled flag."""
        return self._get("safe-mode-status", timeout=timeout)

    def send_otp_event(
        self,
        username: str,
        otp: str,
        timeout: Optional[int] = None,
    ) -> ClientResponse:
        """Send an OTP event for *username* to the service gateway."""
        body = {"username": username, "otp": otp}
        return self._post("send-otp", body=body, expected_status=(200,), timeout=timeout)
