"""Typed results of the agent device API (``/agent/...``)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


def parse_datetime(value: Any) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp from the backend into an aware datetime (``None`` if absent)."""
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed


@dataclass(frozen=True)
class AgentInfo:
    backend_key: str
    server_time: Optional[datetime]
    capabilities: tuple[str, ...]
    endpoints: dict[str, str]

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities

    @classmethod
    def from_data(cls, data: dict) -> "AgentInfo":
        return cls(
            backend_key=str(data.get("backend_key", "")),
            server_time=parse_datetime(data.get("server_time")),
            capabilities=tuple(data.get("capabilities") or ()),
            endpoints=dict(data.get("endpoints") or {}),
        )


@dataclass(frozen=True)
class EnrolledAgent:
    agent_uid: str
    state: str
    enrolled_at: Optional[str]
    equipment_name: str = ""

    @classmethod
    def from_data(cls, data: dict) -> "EnrolledAgent":
        state = data.get("state")
        equipment = data.get("equipment") or {}
        return cls(
            agent_uid=str(data.get("agent_uid", "")),
            state=state.get("value", "") if isinstance(state, dict) else str(state or ""),
            enrolled_at=data.get("enrolled_at"),
            equipment_name=str(equipment.get("name", "")) if isinstance(equipment, dict) else "",
        )


@dataclass(frozen=True)
class Heartbeat:
    status: str
    last_seen_at: Optional[datetime]


@dataclass(frozen=True)
class BookingResult:
    """Outcome of validate / check-in / complete / extend.

    ``ok`` is the operation's flag (``is_eligible``, ``is_checked_in``, ``is_completed`` or
    ``is_extended``). When ``ok`` is false the backend deliberately returns no other fields.
    """

    ok: bool
    booking_code: str = ""
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    booked_for: Optional[str] = None

    @classmethod
    def from_data(cls, data: dict, flag: str) -> "BookingResult":
        ok = bool(data.get(flag, False))
        if not ok:
            return cls(ok=False)
        return cls(
            ok=True,
            booking_code=str(data.get("booking_code", "")),
            starts_at=parse_datetime(data.get("starts_at")),
            ends_at=parse_datetime(data.get("ends_at")),
            booked_for=data.get("booked_for"),
        )


@dataclass(frozen=True)
class MonitoringPolicy:
    generation_key: str
    max_devices: int
    max_body_bytes: int
    freshness_seconds: int
    interface_names: tuple[str, ...]
    etag: str = ""

    @classmethod
    def from_data(cls, data: dict, etag: str = "") -> "MonitoringPolicy":
        return cls(
            generation_key=str(data.get("generation_key", "")),
            max_devices=int(data.get("max_devices", 0)),
            max_body_bytes=int(data.get("max_body_bytes", 0)),
            freshness_seconds=int(data.get("freshness_seconds", 0)),
            interface_names=tuple(data.get("interface_names") or ()),
            etag=etag,
        )


@dataclass(frozen=True)
class ObservationAck:
    batch_key: str
    sequence: int
    disposition: str
    received_at: Optional[datetime]
    replayed: bool = False


@dataclass(frozen=True)
class SessionLogAck:
    id: int
    event_key: str
    created: bool  # False when the same event was already stored (200)


@dataclass
class ActivityReport:
    """Live activity of this computer. Only set fields are sent (``None`` = unchanged)."""

    status: Optional[str] = None  # offline | free | active | inactive | maintaining
    remote_user: Optional[str] = None
    remote_user_display_name: Optional[str] = None
    remote_computer: Optional[str] = None
    remote_ip: Optional[str] = None
    booking_code: Optional[str] = None

    def to_body(self) -> dict:
        body: dict[str, Any] = {}
        for name in ("status", "remote_user", "remote_user_display_name", "remote_computer", "booking_code"):
            value = getattr(self, name)
            if value is not None:
                body[name] = value[:255]
        if self.remote_ip is not None:
            # The backend accepts an IP address or null, never an empty string.
            body["remote_ip"] = self.remote_ip or None
        return body
