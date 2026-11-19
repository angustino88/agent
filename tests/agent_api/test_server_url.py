"""enroll gets the server URL from the service gateway, so the web app never shows a backend address."""

from types import SimpleNamespace

import pytest

try:
    from src.core.gateway import ServerUrlUnavailable, resolve_server_url
except ImportError as error:  # src.utils imports Windows-only modules at package level
    pytest.skip(f"shared modules not importable here: {error}", allow_module_level=True)

from src.agent_cli import build_parser  # noqa: E402


class FakeClient:
    def __init__(self, routes, **kwargs):
        self.routes, self.kwargs, self.auth_value, self.calls = routes, kwargs, None, []


def factory(login=None, config=None):
    routes = {"login": login, "prod-server-config": config}

    def make(**kwargs):
        return FakeClient(routes, **kwargs)

    return make


@pytest.fixture(autouse=True)
def fake_service(monkeypatch):
    from src.core.gateway import server_url

    class Service:
        def __init__(self, client, username, source):
            self.client, self.username, self.source = client, username, source

        def login(self, timeout=None):
            return self.client.routes["login"]

        def get_prod_server_config(self, timeout=None):
            assert self.client.auth_value == "token"
            return self.client.routes["prod-server-config"]

    monkeypatch.setattr(server_url, "LabMangoGatewayService", Service)


def ok(data):
    return SimpleNamespace(success=True, data=data)


def test_returns_the_published_backend_url():
    make = factory(ok({"access": "token"}), ok({"backend_url": "https://api.labmango.example/api/dept_a/"}))
    assert resolve_server_url("http://gw", computer_name="LAB-PC-07", client_factory=make) == (
        "https://api.labmango.example/api/dept_a"
    )


@pytest.mark.parametrize(
    "login,config",
    [
        (SimpleNamespace(success=False, data=None), None),
        (ok({"access": "token"}), ok({"frontend_url": "https://labmango.example"})),
    ],
)
def test_missing_login_or_url_is_reported(login, config):
    with pytest.raises(ServerUrlUnavailable):
        resolve_server_url("http://gw", computer_name="PC", client_factory=factory(login, config))


def test_enroll_no_longer_requires_url():
    args = build_parser().parse_args(["enroll", "--agent-uid", "00000000-0000-4000-8000-000000000001"])
    assert args.url is None and args.gateway_url is None
