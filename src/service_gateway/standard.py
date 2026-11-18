"""Service Gateway — StandardGatewayService.

Provides the standard set of endpoints that every application using this
gateway pattern is expected to expose:

* ``login``                — authenticate and receive tokens
* ``refresh_token``        — exchange a refresh token for a new access token
* ``get_latest_package``   — fetch metadata for the latest software package
* ``check_package_update`` — ask the server whether the current version is outdated

Extend this class to add application-specific endpoints::

    class MyAppGatewayService(StandardGatewayService):
        base_path = "/api/my-app"

        def get_config(self, timeout=None) -> ClientResponse:
            return self._get("config", timeout=timeout)

        def push_event(self, payload: dict, timeout=None) -> ClientResponse:
            return self._post("events", body=payload, timeout=timeout)

The constructor accepts optional credentials and a *source* string. These
are injected into request bodies where the server expects them.
"""
from __future__ import annotations

from typing import Any, Optional

from ..utils.http_client import ClientResponse
from .gateway import GatewayClient
from .service import BaseGatewayService


class StandardGatewayService(BaseGatewayService):
    """Gateway service with standard, application-agnostic endpoints.

    Parameters
    ----------
    client:
        Shared :class:`GatewayClient` instance.
    username:
        Credential used as ``username`` in login requests.  May be a human
        account name, a device SKU, an API key, or any string the server
        accepts as a principal identifier.
    password:
        Optional password / secret paired with *username*.  When provided it
        is included in the ``login`` request body as ``"password"``.
    source:
        Caller/source tag injected into request bodies when present.
    """

    base_path: str = "/api"

    def __init__(
        self,
        client: GatewayClient,
        username: str = "",
        password: Optional[str] = None,
        source: str = "",
    ) -> None:
        super().__init__(client)
        self._username = username
        self._password = password
        self._source = source

    # ---- Identity ----------------------------------------------------------

    @property
    def username(self) -> str:
        """Principal identifier used in authentication requests."""
        return self._username

    @property
    def source(self) -> str:
        """Source tag sent in request payloads."""
        return self._source

    # ---- Standard endpoints ------------------------------------------------

    def login(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: Optional[int] = 10,
    ) -> ClientResponse:
        """Authenticate and return access / refresh tokens.

        Parameters
        ----------
        username:
            Override the stored username for this call only.
        password:
            Override the stored password for this call only.
        timeout:
            Request timeout in seconds.

        The server is expected to respond with a JSON object containing at
        least an ``"access"`` key and optionally a ``"refresh"`` key.
        """
        body: dict[str, Any] = {"username": username if username is not None else self._username}
        pw = password if password is not None else self._password
        if pw is not None:
            body["password"] = pw
        if self._source:
            body["source"] = self._source
        return self._post(
            "login",
            body=body,
            expected_status=(200,),
            timeout=timeout,
            allow_token_refresh=False,
        )

    def refresh_token(self, token: str, timeout: Optional[int] = 10) -> ClientResponse:
        """Exchange *token* for a new access (and optionally refresh) token.

        The server is expected to respond with a JSON object containing at
        least an ``"access"`` key.
        """
        body: dict[str, Any] = {"refresh": token}
        return self._post(
            "token/refresh",
            body=body,
            expected_status=(200,),
            timeout=timeout,
            allow_token_refresh=False,
        )

    def get_latest_package(self, timeout: Optional[int] = None) -> ClientResponse:
        """Return metadata for the latest available software package."""
        return self._get("package/latest", timeout=timeout)

    def get_package_list(self, timeout: Optional[int] = None) -> ClientResponse:
        """Return metadata for all available software packages."""
        return self._get("package/list", timeout=timeout)
    
    def check_package_update(
        self,
        current_version: str,
        timeout: Optional[int] = None,
    ) -> ClientResponse:
        """Ask the server whether *current_version* is outdated.

        The server is expected to respond with a JSON object that includes at
        least a ``"has_update"`` boolean.
        """
        body: dict[str, Any] = {"current_version": str(current_version)}
        return self._post(
            "package/update",
            body=body,
            expected_status=(200,),
            timeout=timeout,
        )
