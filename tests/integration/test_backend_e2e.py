"""End-to-end check against a running lab-mango backend. Skipped unless configured.

Seed a computing equipment on a bench, an enrollment grant and a booking that started a minute
ago and lasts an hour, then run::

    LABMANGO_E2E_URL=http://127.0.0.1:8000 LABMANGO_E2E_AGENT_UID=<uuid> \
    LABMANGO_E2E_GRANT=eg_... LABMANGO_E2E_BOOKING_CODE=<code> pytest tests/integration -q
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.core.agent_api import (
    ActivityReport,
    AgentApiClient,
    AgentKey,
    FileKeyStore,
    IdentityStore,
    SessionLogOutbox,
    enroll,
    errors,
    load_credentials,
)

ENV = {name: os.environ.get(f"LABMANGO_E2E_{name}") for name in ("URL", "AGENT_UID", "GRANT", "BOOKING_CODE")}
pytestmark = pytest.mark.skipif(not all(ENV.values()), reason="LABMANGO_E2E_* not set")


def test_full_agent_lifecycle(tmp_path):
    store = IdentityStore(tmp_path, key_store=FileKeyStore(tmp_path / "keys"))
    verify = not ENV["URL"].startswith("http://")
    enroll(
        store,
        backend_url=ENV["URL"],
        agent_uid=ENV["AGENT_UID"],
        grant=ENV["GRANT"],
        agent_version="e2e",
        verify=verify,
    )
    identity, key = load_credentials(store)
    client = AgentApiClient(identity.backend_url, identity=identity, key=key, verify=verify)
    code = ENV["BOOKING_CODE"]

    assert client.heartbeat().last_seen_at is not None
    client.report_activity(ActivityReport(status="active", remote_user="e2e", remote_ip="", booking_code=code))

    assert client.validate_booking(f"{code}-UNKNOWN").ok is False
    checked_in = client.check_in_booking(code)
    assert checked_in.ok and client.check_in_booking(code).ok  # repeatable
    extended = client.extend_booking(code, (checked_in.ends_at + timedelta(minutes=30)).isoformat())
    assert extended.ends_at > checked_in.ends_at
    with pytest.raises(errors.BookingExtensionRejected) as rejected:
        client.extend_booking(code, (checked_in.starts_at + timedelta(hours=10)).isoformat())
    assert rejected.value.reason == "needs_approval"

    now = datetime.now(timezone.utc)
    outbox = SessionLogOutbox(tmp_path / "outbox.json")
    log = {
        "event_key": str(uuid.uuid4()),
        "login_at": (now - timedelta(minutes=5)).isoformat(),
        "logout_at": now.isoformat(),
        "active_duration_seconds": 120.0,
        "remote_user": "e2e",
        "booking_code": code,
    }
    outbox.add(log)
    assert outbox.flush(client) == 1 and outbox.pending() == []
    assert client.record_session_log(log).created is False  # idempotent replay

    assert client.complete_booking(code).ok
    assert client.validate_booking(code).ok is False

    policy = client.get_monitoring_policy()
    assert client.get_monitoring_policy(policy.etag) is None
    report = {
        "generation_key": policy.generation_key,
        "collector_key": "e2e",
        "sequence": 1,
        "collected_at": now.isoformat(),
        "is_complete": True,
        "devices": [],
    }
    batch = uuid.uuid4()
    assert client.report_device_observations(report, batch).replayed is False
    assert client.report_device_observations(report, batch).replayed is True

    impostor = AgentApiClient(identity.backend_url, identity=identity, key=AgentKey.generate(), verify=verify)
    with pytest.raises(errors.Unauthenticated):
        impostor.heartbeat()
