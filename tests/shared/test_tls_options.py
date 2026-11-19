"""TLS options of the shared HTTP clients (utils.http_client, service_gateway)."""

import pytest

try:
    from src.service_gateway.gateway import GatewayClient
    from src.utils.http_client import ClientRequest
except ImportError as error:  # src.utils imports Windows-only modules at package level
    pytest.skip(f"shared modules not importable here: {error}", allow_module_level=True)


class _Session:
    def __init__(self):
        self.kwargs = []

    def request(self, **kwargs):
        import requests

        self.kwargs.append(kwargs)
        response = requests.Response()
        response.status_code = 200
        response._content = b"{}"
        return response


def test_client_request_keeps_unverified_default_for_existing_consumers():
    client = ClientRequest("https://h")
    client._session = _Session()
    client.get("/x")
    assert client.verify is False and client._session.kwargs[0]["verify"] is False


def test_client_request_passes_ca_bundle():
    client = ClientRequest("https://h", verify="C:/ca.pem")
    client._session = _Session()
    client.get("/x")
    assert client._session.kwargs[0]["verify"] == "C:/ca.pem"


def test_gateway_falls_back_to_http_by_default():
    assert GatewayClient("http://gw:8000").candidates == ["https://gw:8000", "http://gw:8000"]


def test_gateway_without_fallback_uses_https_only_and_verifies():
    gateway = GatewayClient("http://gw:8000", verify=True, allow_http_fallback=False)
    assert gateway.candidates == ["https://gw:8000"]
    assert gateway._client.verify is True
