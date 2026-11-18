import json

import pytest

from src.core.agent_api import (
    AgentApiClient,
    AlreadyEnrolled,
    FileKeyStore,
    IdentityStore,
    enroll,
    errors,
    load_credentials,
)
from src.core.agent_api.signing import b64url_decode, enrollment_message
from cryptography.hazmat.primitives.serialization import load_der_public_key

from .conftest import AGENT_UID, FakeSession

INFO = {
    "data": {
        "backend_key": "dept_a",
        "server_time": "2026-11-18T07:00:00Z",
        "capabilities": ["enrollment", "request_signature_v1", "heartbeat"],
        "endpoints": {},
    }
}
ENROLLED = {
    "data": {
        "agent_uid": AGENT_UID,
        "state": {"value": "active", "label": "Active"},
        "enrolled_at": "2026-11-18T07:00:01Z",
    }
}


@pytest.fixture
def store(tmp_path):
    return IdentityStore(tmp_path / "agent", key_store=FileKeyStore(tmp_path / "agent" / "keys"))


def _factory(session):
    return lambda url, **kw: AgentApiClient(url, session=session, **{k: v for k, v in kw.items() if k != "session"})


def _enroll(store, session, **overrides):
    args = dict(
        backend_url="https://b/api/dept_a/",
        agent_uid=AGENT_UID.upper(),
        grant="eg_secret",
        agent_version="2.7.0",
        client_factory=_factory(session),
    )
    args.update(overrides)
    return enroll(store, **args)


def test_enrolls_with_valid_proof_and_never_persists_the_grant(store, tmp_path):
    session = FakeSession().queue(200, INFO).queue(201, ENROLLED)

    identity = _enroll(store, session)

    body = json.loads(session.sent[1].body)
    assert identity.is_enrolled and identity.agent_uid == AGENT_UID and identity.backend_url == "https://b/api/dept_a"
    message = enrollment_message(
        backend_id="dept_a", agent_uid=AGENT_UID, grant="eg_secret", public_key_der=b64url_decode(body["public_key"])
    )
    load_der_public_key(b64url_decode(body["public_key"])).verify(b64url_decode(body["proof"]), message)
    assert body["key_storage"] == "software"
    on_disk = "".join(p.read_text() for p in tmp_path.rglob("*") if p.is_file())
    assert "eg_secret" not in on_disk
    loaded, key = load_credentials(store)
    assert loaded == identity and key.public_key_b64url == body["public_key"]


def test_lost_response_retry_reuses_the_journaled_key(store):
    first = FakeSession().queue(200, INFO)  # enrollment POST then fails: no canned response
    with pytest.raises(errors.BackendUnreachable):
        _enroll(store, first)
    assert store.load().state == "pending"

    second = FakeSession().queue(200, INFO).queue(201, ENROLLED)
    _enroll(store, second)

    assert json.loads(first.sent[1].body)["public_key"] == json.loads(second.sent[1].body)["public_key"]


def test_refuses_when_already_enrolled(store):
    _enroll(store, FakeSession().queue(200, INFO).queue(201, ENROLLED))
    with pytest.raises(AlreadyEnrolled):
        _enroll(store, FakeSession().queue(200, INFO))


def test_rejected_grant_maps_to_enrollment_rejected(store):
    session = (
        FakeSession()
        .queue(200, INFO)
        .queue(400, {"error": {"code": "invalid", "message": "Enrollment grant is invalid."}})
    )
    with pytest.raises(errors.EnrollmentRejected):
        _enroll(store, session)


def test_bad_grant_shape_is_rejected_before_any_request(store):
    session = FakeSession()
    with pytest.raises(errors.EnrollmentRejected):
        _enroll(store, session, grant="not-a-grant")
    assert session.sent == []


def test_backend_without_signature_support_is_refused(store):
    info = {"data": {**INFO["data"], "capabilities": ["enrollment"]}}
    with pytest.raises(errors.AgentApiError, match="request_signature_v1"):
        _enroll(store, FakeSession().queue(200, info))


def test_mismatched_key_is_never_used(store, tmp_path):
    _enroll(store, FakeSession().queue(200, INFO).queue(201, ENROLLED))
    from src.core.agent_api import AgentKey

    store.save_key(AGENT_UID, AgentKey.generate())
    identity, key = load_credentials(store)
    assert identity.is_enrolled and key is None
