import json

import pytest

from src.core.agent_api import errors
from src.core.monitoring import DeviceObservationReporter, ObservedDevice


POLICY = {
    "data": {
        "generation_key": "11111111-1111-1111-1111-111111111111",
        "max_devices": 3,
        "max_body_bytes": 262144,
        "freshness_seconds": 120,
        "interface_names": ["USB"],
    }
}


def ack(sequence=1, disposition="applied"):
    return {
        "data": {
            "batch_key": "k",
            "sequence": sequence,
            "disposition": {"value": disposition, "label": ""},
            "received_at": "2026-11-18T07:00:00Z",
        }
    }


class Clock:
    def __init__(self, now=1_700_000_000.0):
        self.now = now

    def __call__(self):
        return self.now


def device(key="usb:a", serial="SN1"):
    return ObservedDevice(observation_key=key, interface_name="USB", name="Probe", serial_number=serial)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def reporter(tmp_path, client, clock):
    return DeviceObservationReporter(client, tmp_path / "usb.json", collector_key="usb", clock=clock)


def bodies(session):
    return [json.loads(s.body) for s in session.sent if s.url.endswith("/report")]


def test_sends_a_complete_snapshot_with_clock_based_sequence(reporter, session):
    session.queue(200, POLICY, {"ETag": '"e"'}).queue(200, ack())
    assert reporter.report([device()]).disposition == "applied"
    body = bodies(session)[0]
    assert body["is_complete"] is True and body["collector_key"] == "usb"
    assert body["sequence"] == 1_700_000_000_000
    assert body["devices"] == [device().to_body()]
    assert session.sent[1].headers["Idempotency-Key"]


def test_unchanged_devices_are_resent_only_when_freshness_requires(reporter, session, clock):
    session.queue(200, POLICY).queue(200, ack())
    reporter.report([device()])
    clock.now += 30
    assert reporter.report([device()]) is None  # nothing new, still fresh
    clock.now += 31  # half of freshness_seconds passed
    session.queue(200, ack(2))
    assert reporter.report([device()]) is not None
    assert bodies(session)[1]["sequence"] > bodies(session)[0]["sequence"]


def test_a_change_is_sent_immediately(reporter, session, clock):
    session.queue(200, POLICY).queue(200, ack())
    reporter.report([device()])
    clock.now += 1
    session.queue(200, ack(2))
    reporter.report([])  # unplugged: empty complete snapshot disconnects it on the backend
    assert bodies(session)[1]["devices"] == []


def test_transient_failure_resends_the_same_batch(reporter, session, tmp_path, client, clock):
    session.queue(200, POLICY).queue(503, {"error": {"code": "unavailable", "message": "down"}})
    with pytest.raises(errors.ServerError):
        reporter.report([device()])
    # a restart keeps the pending batch on disk
    again = DeviceObservationReporter(client, tmp_path / "usb.json", collector_key="usb", clock=clock)
    session.queue(200, POLICY).queue(200, ack())
    again.report([device()])
    first, second = [s for s in session.sent if s.url.endswith("/report")]
    assert first.body == second.body
    assert first.headers["Idempotency-Key"] == second.headers["Idempotency-Key"]


def test_rejected_batch_is_dropped_and_a_new_snapshot_follows(reporter, session, clock):
    session.queue(200, POLICY).queue(409, {"error": {"code": "observation_conflict", "message": "taken"}})
    assert reporter.report([device()]) is None
    clock.now += 1
    session.queue(200, ack(5))
    assert reporter.report([device()]) is not None
    keys = [s.headers["Idempotency-Key"] for s in session.sent if s.url.endswith("/report")]
    assert keys[0] != keys[1]


def test_too_many_devices_are_not_reported_as_a_truncated_snapshot(reporter, session):
    session.queue(200, POLICY)
    many = [device(f"usb:{i}", f"S{i}") for i in range(4)]
    assert reporter.report(many) is None
    assert bodies(session) == []


def test_new_generation_forces_a_snapshot(reporter, session, clock):
    session.queue(200, POLICY, {"ETag": '"1"'}).queue(200, ack())
    reporter.report([device()])
    new_policy = {"data": {**POLICY["data"], "generation_key": "22222222-2222-2222-2222-222222222222"}}
    session.queue(200, new_policy, {"ETag": '"2"'})
    reporter.refresh_policy()
    clock.now += 1
    session.queue(200, ack(2))
    assert reporter.report([device()]) is not None
    assert bodies(session)[1]["generation_key"].startswith("2222")
