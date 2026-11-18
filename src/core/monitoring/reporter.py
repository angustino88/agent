"""Report device observations for one collector (``POST /agent/device-observations/actions/report``).

Every report is a *complete* snapshot of the connected devices: the backend disconnects devices a
complete snapshot omits, and complete snapshots may skip sequence numbers, so a lost report or a
lost state file never leaves the backend wrong for longer than one cycle.

* A snapshot is sent when the device set changes, and otherwise at least every half
  ``freshness_seconds`` so the backend keeps the connections fresh.
* The batch (``Idempotency-Key`` + exact body) is persisted before sending and resent unchanged
  until acknowledged; the backend replays the original answer for a duplicate.
* Sequences come from the wall clock in milliseconds (never below the last one sent), so they keep
  increasing after a reinstall without any stored state.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from ..agent_api import errors
from ..agent_api.client import AgentApiClient
from ..agent_api.identity import atomic_write
from ..agent_api.models import MonitoringPolicy, ObservationAck
from .devices import ObservedDevice

_MAX_SEQUENCE = 9007199254740991


class DeviceObservationReporter:
    def __init__(
        self,
        client: AgentApiClient,
        state_path: str | Path,
        *,
        collector_key: str,
        logger: Any = None,
        clock: Callable[[], float] = time.time,
    ):
        self._client = client
        self._path = Path(state_path)
        self._collector_key = collector_key
        self._logger = logger
        self._clock = clock
        self._lock = threading.Lock()
        self._policy: Optional[MonitoringPolicy] = None
        self._state = self._load()

    # ------------------------------------------------------------------ state

    def _load(self) -> dict:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(self._path, json.dumps(self._state, indent=2))  # key order kept: resends are byte-identical

    def _log(self, level: str, message: str) -> None:
        if self._logger is not None:
            getattr(self._logger, level, self._logger.info)(f"[DeviceObservations:{self._collector_key}] {message}")

    @property
    def policy(self) -> Optional[MonitoringPolicy]:
        return self._policy

    # ------------------------------------------------------------------ policy

    def refresh_policy(self) -> MonitoringPolicy:
        """Fetch the policy (cheap ``304`` when unchanged). A new generation forces a snapshot."""
        etag = self._policy.etag if self._policy else ""
        fresh = self._client.get_monitoring_policy(etag)
        if fresh is not None:
            if self._policy is None or fresh.generation_key != self._policy.generation_key:
                self._state.pop("fingerprint", None)
            self._policy = fresh
        assert self._policy is not None
        return self._policy

    # ------------------------------------------------------------------ reporting

    def report(self, devices: Sequence[ObservedDevice], *, force: bool = False) -> Optional[ObservationAck]:
        """Send a complete snapshot when due. Returns the acknowledgment, or ``None`` when nothing was sent.

        Raises :class:`~src.core.agent_api.errors.AgentApiError` for transient failures; the pending
        batch is kept and resent on the next call.
        """
        with self._lock:
            pending = self._state.get("pending")
            if pending:
                ack = self._send(pending)
                if ack is not None and pending.get("fingerprint") == self._fingerprint(devices) and not force:
                    return ack

            policy = self._policy or self.refresh_policy()
            connected = [d for d in devices if d.state == "connected"]
            if len(connected) > policy.max_devices:
                self._log("warning", f"{len(connected)} devices exceed the limit of {policy.max_devices}; not reported")
                return None
            fingerprint = self._fingerprint(connected)
            if not force and not self._due(fingerprint, policy):
                return None

            sequence = min(_MAX_SEQUENCE, max(int(self._state.get("sequence", 0)) + 1, int(self._clock() * 1000)))
            body = {
                "generation_key": policy.generation_key,
                "collector_key": self._collector_key,
                "sequence": sequence,
                "collected_at": datetime.fromtimestamp(self._clock(), tz=timezone.utc).isoformat(),
                "is_complete": True,
                "devices": [d.to_body() for d in sorted(connected, key=lambda d: d.observation_key)],
            }
            if policy.max_body_bytes and len(json.dumps(body, separators=(",", ":"))) > policy.max_body_bytes:
                self._log("warning", "snapshot exceeds the backend body limit; not reported")
                return None
            batch = {"idempotency_key": str(uuid.uuid4()), "body": body, "fingerprint": fingerprint}
            self._state["pending"] = batch
            self._state["sequence"] = sequence
            self._save()
            return self._send(batch)

    def _due(self, fingerprint: str, policy: MonitoringPolicy) -> bool:
        if self._state.get("fingerprint") != fingerprint:
            return True
        interval = max(1, policy.freshness_seconds // 2)
        return self._clock() - float(self._state.get("sent_at", 0)) >= interval

    def _send(self, batch: dict) -> Optional[ObservationAck]:
        """Send one persisted batch. Clears it on acknowledgment or terminal rejection."""
        try:
            ack = self._client.report_device_observations(batch["body"], batch["idempotency_key"])
        except errors.Conflict as error:
            # observation_conflict (sequence taken) or snapshot_required: drop and resend a fresh snapshot
            if error.code == "request_in_progress":
                raise
            self._log("warning", f"batch rejected, will send a new snapshot: {error}")
            self._clear(batch, sent=False)
            return None
        except errors.ValidationFailed as error:
            self._log("error", f"batch rejected as invalid: {error}")
            self._clear(batch, sent=False)
            return None
        if ack.disposition == "stale":
            self._log("warning", f"sequence {ack.sequence} was stale; the next snapshot uses a newer one")
        self._clear(batch, sent=True)
        return ack

    def _clear(self, batch: dict, *, sent: bool) -> None:
        self._state.pop("pending", None)
        if sent:
            self._state["fingerprint"] = batch.get("fingerprint")
            self._state["sent_at"] = self._clock()
        else:
            self._state.pop("fingerprint", None)
        self._save()

    @staticmethod
    def _fingerprint(devices: Sequence[ObservedDevice]) -> str:
        rows = sorted(json.dumps(d.to_body(), sort_keys=True) for d in devices if d.state == "connected")
        return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()
