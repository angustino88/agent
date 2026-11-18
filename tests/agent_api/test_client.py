import json

import pytest

from src.core.agent_api import ActivityReport, AgentApiClient, errors
from src.core.agent_api.signing import b64url_decode, request_message
from cryptography.hazmat.primitives.serialization import load_der_public_key

from .conftest import AGENT_UID, BACKEND_KEY


def _verify(sent, key, path):
    h = sent.headers
    message = request_message(
        backend_id=BACKEND_KEY,
        agent_uid=h["X-Agent-Id"],
        method=sent.method,
        path=path,
        timestamp=h["X-Agent-Timestamp"],
        nonce=h["X-Agent-Nonce"],
        body=sent.body,
    )
    load_der_public_key(b64url_decode(key.public_key_b64url)).verify(b64url_decode(h["X-Agent-Signature"]), message)


def test_signs_backend_path_not_router_prefix_and_sends_signed_bytes(client, session, key):
    session.queue(200, {"data": {"status": "ok", "last_seen_at": "2026-11-18T07:00:00Z"}})

    beat = client.heartbeat()

    sent = session.sent[0]
    assert sent.url == "https://backend.example/api/dept_a/agent/heartbeat"
    assert sent.headers["X-Agent-Id"] == AGENT_UID
    assert sent.headers["X-Agent-Timestamp"] == "1700000000"
    assert len(b64url_decode(sent.headers["X-Agent-Nonce"])) >= 16
    _verify(sent, key, "/agent/heartbeat")
    assert sent.kwargs["allow_redirects"] is False
    assert beat.status == "ok" and beat.last_seen_at.year == 2026


def test_each_request_uses_a_fresh_nonce(client, session):
    session.queue(200, {"data": {}}).queue(200, {"data": {}})
    client.heartbeat()
    client.heartbeat()
    assert session.sent[0].headers["X-Agent-Nonce"] != session.sent[1].headers["X-Agent-Nonce"]


def test_unenrolled_client_refuses_to_send(session):
    client = AgentApiClient("https://b", session=session)
    with pytest.raises(errors.NotEnrolled):
        client.heartbeat()
    assert session.sent == []


def test_activity_sends_only_set_fields_and_null_for_empty_ip(client, session):
    session.queue(200, {"data": {}})
    client.report_activity(ActivityReport(status="free", remote_ip=""))
    assert json.loads(session.sent[0].body) == {"status": "free", "remote_ip": None}
    assert session.sent[0].method == "PATCH"


@pytest.mark.parametrize(
    "status, cls",
    [(401, errors.Unauthenticated), (409, errors.Conflict), (422, errors.ValidationFailed), (429, errors.RateLimited), (503, errors.ServerError)],
)
def test_error_envelope_maps_to_typed_errors(client, session, status, cls):
    session.queue(status, {"error": {"code": "x", "message": "nope", "details": [], "request_id": "r1"}}, {"Retry-After": "7"})
    with pytest.raises(cls) as caught:
        client.heartbeat()
    assert caught.value.code == "x" and caught.value.request_id == "r1"
    if status == 429:
        assert caught.value.retry_after == 7.0
    assert caught.value.is_retryable == (status in (429, 503))


def test_redirect_is_an_error_not_followed(client, session):
    session.queue(302, None, {"Location": "https://elsewhere/"})
    with pytest.raises(errors.AgentApiError, match="redirect"):
        client.heartbeat()


def test_connection_failure_is_backend_unreachable(client, session):
    with pytest.raises(errors.BackendUnreachable) as caught:
        client.heartbeat()
    assert caught.value.is_retryable


def test_booking_refusal_has_no_details(client, session):
    session.queue(200, {"data": {"is_eligible": False}})
    assert client.validate_booking("BOOKING-1").ok is False


def test_check_in_parses_window(client, session):
    session.queue(200, {"data": {"is_checked_in": True, "booking_code": "B", "starts_at": "2026-11-18T07:00:00Z",
                                 "ends_at": "2026-11-18T08:00:00+00:00", "booked_for": "ann"}})
    result = client.check_in_booking("B")
    assert result.ok and result.booked_for == "ann" and result.ends_at.hour == 8


def test_extension_rejection_carries_reason_and_limit(client, session):
    session.queue(409, {"error": {"code": "bench_not_free", "message": "Bench busy", "request_id": "r",
                                  "details": [{"field": "ends_at", "code": "bench_not_free", "message": "busy",
                                               "limit_at": "2026-11-18T09:00:00Z"}]}})
    with pytest.raises(errors.BookingExtensionRejected) as caught:
        client.extend_booking("B", "2026-11-18T10:00:00+00:00")
    assert caught.value.reason == "bench_not_free" and caught.value.limit_at.hour == 9


def test_monitoring_policy_etag_round_trip(client, session):
    session.queue(200, {"data": {"generation_key": "g", "max_devices": 5, "max_body_bytes": 100,
                                 "freshness_seconds": 60, "interface_names": ["usb"]}}, {"ETag": '"abc"'})
    session.queue(304)
    policy = client.get_monitoring_policy()
    assert policy.etag == '"abc"' and policy.interface_names == ("usb",)
    assert client.get_monitoring_policy(policy.etag) is None
    assert session.sent[1].headers["If-None-Match"] == '"abc"'


def test_observations_send_idempotency_key_and_detect_replay(client, session):
    session.queue(200, {"data": {"batch_key": "k", "sequence": 1, "disposition": {"value": "applied", "label": "A"},
                                 "received_at": "2026-11-18T07:00:00Z"}}, {"Idempotency-Replayed": "true"})
    ack = client.report_device_observations({"devices": []}, "11111111-1111-1111-1111-111111111111")
    assert session.sent[0].headers["Idempotency-Key"] == "11111111-1111-1111-1111-111111111111"
    assert ack.replayed and ack.disposition == "applied"


def test_session_log_200_means_already_stored(client, session):
    session.queue(200, {"data": {"id": 3, "event_key": "e"}})
    assert client.record_session_log({"event_key": "e"}).created is False
