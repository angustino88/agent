"""The devices this computer must report: the expected devices of the monitoring policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from .devices import HardwareId, ObservedDevice, normalize_hardware_id


@dataclass(frozen=True)
class ExpectedDevice:
    equipment_uid: str
    name: str
    hardware_ids: tuple[HardwareId, ...]


@dataclass(frozen=True)
class WatchList:
    expected: tuple[ExpectedDevice, ...] = ()

    @classmethod
    def from_policy(cls, items: Iterable[dict]) -> "WatchList":
        expected = []
        for item in items or ():
            if not isinstance(item, dict):
                continue
            ids = tuple(
                HardwareId(
                    str(h.get("kind", "")), normalize_hardware_id(str(h.get("kind", "")), str(h.get("value", "")))
                )
                for h in item.get("hardware_ids") or ()
                if isinstance(h, dict) and h.get("value")
            )
            expected.append(ExpectedDevice(str(item.get("equipment_uid", "")), str(item.get("name", "")), ids))
        return cls(tuple(expected))

    @property
    def _by_id(self) -> dict[HardwareId, ExpectedDevice]:
        return {hardware_id: device for device in self.expected for hardware_id in device.hardware_ids}

    def match(self, device: ObservedDevice) -> Optional[ExpectedDevice]:
        lookup = self._by_id
        return next((lookup[h] for h in device.hardware_ids if h in lookup), None)

    def select(self, devices: Iterable[ObservedDevice]) -> list[ObservedDevice]:
        """Only the devices on the watch list; nothing else leaves the computer."""
        lookup = self._by_id
        return [d for d in devices if any(h in lookup for h in d.hardware_ids)]

    @property
    def unregistered(self) -> list[ExpectedDevice]:
        """Expected units whose hardware ID nobody registered yet (they cannot be seen)."""
        return [device for device in self.expected if not device.hardware_ids]
