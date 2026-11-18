"""Test doubles shared by the test packages."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import requests


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
