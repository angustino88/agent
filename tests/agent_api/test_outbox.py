from src.core.agent_api import SessionLogOutbox


def entry(key):
    return {
        "event_key": key,
        "login_at": "2026-11-18T06:00:00+00:00",
        "logout_at": "2026-11-18T07:00:00+00:00",
        "active_duration_seconds": 60.0,
        "remote_user": "ann",
    }


def test_acknowledged_logs_are_removed_and_transient_failures_kept(tmp_path, client, session):
    box = SessionLogOutbox(tmp_path / "outbox.json")
    for k in ("a", "b", "c"):
        box.add(entry(k))
    session.queue(201, {"data": {"id": 1, "event_key": "a"}})
    session.queue(422, {"error": {"code": "validation_failed", "message": "bad"}})
    session.queue(503, {"error": {"code": "unavailable", "message": "down"}})

    assert box.flush(client) == 1

    assert [e["event_key"] for e in box.pending()] == ["c"]
    assert box.dropped == 1
    assert [s.body for s in session.sent][0].startswith(b'{"event_key":"a"')


def test_outbox_is_bounded_and_deduplicates(tmp_path):
    box = SessionLogOutbox(tmp_path / "outbox.json", max_entries=2)
    for k in ("a", "b", "b", "c"):
        box.add(entry(k))
    assert [e["event_key"] for e in box.pending()] == ["b", "c"]
    assert box.dropped == 1
