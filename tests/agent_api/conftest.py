"""Fake HTTP session that records requests and replays canned responses."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest
import requests

from src.core.agent_api import AgentApiClient, AgentKey
from src.core.agent_api.identity import AgentIdentity, IdentityState

AGENT_UID = "6f1c2b8e-4a5d-4c2e-9f10-1234567890ab"
BACKEND_KEY = "dept_a"


@dataclass
class Sent:
    method: str
    url: str
    body: bytes
    headers: dict
    kwargs: dict


@dataclass
class FakeSession:
    responses: list = field(default_factory=list)
    sent: list = field(default_factory=list)

    def queue(self, status: int, payload: Any = None, headers: dict | None = None) -> "FakeSession":
        self.responses.append((status, payload, headers or {}))
        return self

    def request(self, method, url, data=None, headers=None, **kwargs):
        self.sent.append(Sent(method, url, data or b"", dict(headers or {}), kwargs))
        if not self.responses:
            raise requests.ConnectionError("no canned response")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        status, payload, extra = item
        response = requests.Response()
        response.status_code = status
        response._content = b"" if payload is None else json.dumps(payload).encode()
        response.headers.update(extra)
        return response


@pytest.fixture
def key() -> AgentKey:
    return AgentKey.generate()


@pytest.fixture
def identity(key) -> AgentIdentity:
    return AgentIdentity(
        agent_uid=AGENT_UID,
        backend_url="https://backend.example/api/dept_a",
        backend_key=BACKEND_KEY,
        key_storage="software",
        public_key_sha256=key.public_key_sha256,
        state=IdentityState.ENROLLED,
    )


@pytest.fixture
def session() -> FakeSession:
    return FakeSession()


@pytest.fixture
def client(identity, key, session) -> AgentApiClient:
    return AgentApiClient(identity.backend_url, identity=identity, key=key, session=session, clock=lambda: 1_700_000_000)
