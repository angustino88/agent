"""Shared fixtures: an enrolled identity, its key, and a client on a fake HTTP session."""

import pytest

from src.core.agent_api import AgentApiClient, AgentKey
from src.core.agent_api.identity import AgentIdentity, IdentityState

from .fakes import AGENT_UID, BACKEND_KEY, FakeSession


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
    return AgentApiClient(
        identity.backend_url, identity=identity, key=key, session=session, clock=lambda: 1_700_000_000
    )
