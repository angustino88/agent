"""Service Gateway — BaseGatewayService.

Every endpoint group in a gateway service inherits from this base class.
It holds a :class:`~service_gateway.gateway.GatewayClient` reference and exposes
protected HTTP helpers that automatically prepend ``base_path`` to every
relative URL.

Usage::

    class MyAppService(BaseGatewayService):
        base_path = "/api/v2/my-app"

        def get_status(self, timeout=None) -> ClientResponse:
            return self._get("status", timeout=timeout)

        def create_item(self, data: dict, timeout=None) -> ClientResponse:
            return self._post("items", body=data, timeout=timeout)
"""
from __future__ import annotations

from typing import Iterable, Iterator, Optional

from ..utils.http_client import ClientResponse
from .gateway import GatewayClient


class BaseGatewayService:
    """Base class for all gateway service endpoint groups.

    Parameters
    ----------
    client:
        A :class:`GatewayClient` instance shared by all service objects that
        talk to the same remote gateway.

    Class Attributes
    ----------------
    base_path:
        API path prefix prepended to every relative endpoint passed to the
        ``_get``/``_post``/… helpers.  Override in subclasses::

            class MyService(BaseGatewayService):
                base_path = "/api/my-app"
    """

    base_path: str = "/api"

    def __init__(self, client: GatewayClient) -> None:
        self._client = client

    # ---- Internal helpers -------------------------------------------------

    def _endpoint(self, path: str) -> str:
        """Join ``base_path`` with *path*, handling leading slashes cleanly."""
        return f"{self.base_path.rstrip('/')}/{path.lstrip('/')}"

    def _get(
        self,
        path: str,
        expected_status: Iterable[int] = (200,),
        timeout: Optional[int] = 10,
        allow_token_refresh: bool = True,
    ) -> ClientResponse:
        return self._client.get(
            self._endpoint(path),
            expected_status=expected_status,
            timeout=timeout,
            allow_token_refresh=allow_token_refresh,
        )

    def _post(
        self,
        path: str,
        body: Optional[dict] = None,
        expected_status: Iterable[int] = (200, 201),
        timeout: Optional[int] = 10,
        allow_token_refresh: bool = True,
    ) -> ClientResponse:
        return self._client.post(
            self._endpoint(path),
            body=body,
            expected_status=expected_status,
            timeout=timeout,
            allow_token_refresh=allow_token_refresh,
        )

    def _put(
        self,
        path: str,
        body: Optional[dict] = None,
        expected_status: Iterable[int] = (200, 204),
        timeout: Optional[int] = 10,
        allow_token_refresh: bool = True,
    ) -> ClientResponse:
        return self._client.put(
            self._endpoint(path),
            body=body,
            expected_status=expected_status,
            timeout=timeout,
            allow_token_refresh=allow_token_refresh,
        )

    def _patch(
        self,
        path: str,
        body: Optional[dict] = None,
        expected_status: Iterable[int] = (200, 204),
        timeout: Optional[int] = 10,
        allow_token_refresh: bool = True,
    ) -> ClientResponse:
        return self._client.patch(
            self._endpoint(path),
            body=body,
            expected_status=expected_status,
            timeout=timeout,
            allow_token_refresh=allow_token_refresh,
        )

    def _delete(
        self,
        path: str,
        body: Optional[dict] = None,
        expected_status: Iterable[int] = (200, 204),
        timeout: Optional[int] = 10,
        allow_token_refresh: bool = True,
    ) -> ClientResponse:
        return self._client.delete(
            self._endpoint(path),
            body=body,
            expected_status=expected_status,
            timeout=timeout,
            allow_token_refresh=allow_token_refresh,
        )

    # ---- Error handling helpers -------------------------------------------

    def _raise_for_status(
        self,
        resp: ClientResponse,
        context: str = "",
    ) -> ClientResponse:
        """Raise :class:`~.exceptions.GatewayResponseError` when *resp* is not successful.

        Returns *resp* unchanged on success so callers can chain the call::

            data = self._raise_for_status(self._get("status")).data

        Parameters
        ----------
        resp:
            Response to check.
        context:
            Optional description prepended to the error message
            (e.g. the endpoint name) to make the error easier to trace.

        Raises
        ------
        GatewayResponseError
            When ``resp.success`` is ``False``.
        """
        if not resp.success:
            from .exceptions import GatewayResponseError
            msg = f"Unexpected status {resp.status_code}"
            if context:
                msg = f"{context}: {msg}"
            raise GatewayResponseError(msg, status_code=resp.status_code or 0, response=resp)
        return resp

    # ---- Pagination helpers -----------------------------------------------

    def _paginate(
        self,
        path: str,
        *,
        results_key: str = "results",
        next_key: str = "next",
        timeout: Optional[int] = 10,
    ) -> Iterator[list]:
        """Yield successive pages from a cursor/link-based paginated endpoint.

        The server is expected to return a JSON object with a ``results_key``
        list and an optional ``next_key`` URL.  Iteration stops when
        ``next_key`` is absent / ``None`` or the results list is empty.

        For page-number-based APIs, override this method in the subclass or
        call ``_get`` directly with an incrementing ``page`` query parameter.

        Example::

            for page in self._paginate("items"):
                for item in page:
                    process(item)

        Parameters
        ----------
        path:
            Relative endpoint path (``base_path`` is prepended automatically).
        results_key:
            Key in the response JSON object that contains the list of items.
        next_key:
            Key in the response JSON object that holds the URL for the next
            page (``None`` / absent \u2192 last page).
        timeout:
            Per-request timeout in seconds.
        """
        endpoint = self._endpoint(path)
        while endpoint:
            resp = self._client.get(endpoint, timeout=timeout)
            if not resp.success:
                break
            data = resp.data
            if isinstance(data, list):
                # Flat array response — treat as a single page
                if data:
                    yield data
                break
            if not isinstance(data, dict):
                break
            items: list = data.get(results_key, [])
            if not items:
                break
            yield items
            raw_next = data.get(next_key)
            # next_key may be a full URL or a relative path
            if not raw_next:
                break
            # If next is a full URL use it directly; otherwise treat as relative path
            endpoint = raw_next if raw_next.startswith(("http://", "https://")) else self._endpoint(raw_next)
