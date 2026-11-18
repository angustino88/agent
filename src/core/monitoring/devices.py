"""Devices the agent sees, identified by the hardware IDs Windows reports.

The backend recognises equipment by IDs a coordinator registered on the unit
(``EquipmentHardwareId``), never by the inventory's ``serial_number``:

* ``pnp_id``: the PnP device instance ID (``Win32_PnPEntity.PNPDeviceID``, Device Manager →
  Details → *Device instance path*), e.g. ``USB\\VID_1248&PID_1073\\007113-585343``. If its last
  segment contains ``&``, Windows built it from the USB port, so it is only valid on this computer.
* ``vector_device``: the Vector device name license tools report (``007113-585343``).

Values are normalised exactly like the backend: upper case, backslash separators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

FIELD_MAX = 255
VALUE_MAX = 512
CONNECTED = "connected"
DISCONNECTED = "disconnected"


class HardwareIdKind:
    PNP_ID = "pnp_id"
    VECTOR_DEVICE = "vector_device"


def normalize_hardware_id(kind: str, value: str) -> str:
    value = (value or "").strip()
    if kind == HardwareIdKind.PNP_ID:
        value = value.replace("/", "\\")
    return value.upper()


def is_port_bound(pnp_id: str) -> bool:
    """True when Windows generated the last segment from the USB port (the device has no serial)."""
    last = normalize_hardware_id(HardwareIdKind.PNP_ID, pnp_id).rsplit("\\", 1)[-1]
    return "&" in last


def enumerator(pnp_id: str) -> str:
    """The bus that enumerated the device: ``USB``, ``USBSTOR``, ``HID``, ``PCI``, …"""
    return normalize_hardware_id(HardwareIdKind.PNP_ID, pnp_id).split("\\", 1)[0]


@dataclass(frozen=True, order=True)
class HardwareId:
    """A value read from the hardware itself; a coordinator registers it on the inventory unit."""

    kind: str
    value: str

    @classmethod
    def pnp(cls, pnp_id: str) -> "HardwareId":
        return cls(HardwareIdKind.PNP_ID, normalize_hardware_id(HardwareIdKind.PNP_ID, pnp_id))

    def to_body(self) -> dict:
        return {"kind": self.kind, "value": self.value[:VALUE_MAX]}


@dataclass(frozen=True)
class ObservedDevice:
    observation_key: str
    interface_name: str
    name: str = ""
    hardware_ids: tuple[HardwareId, ...] = field(default=())
    state: str = CONNECTED

    @property
    def pnp_id(self) -> str:
        return next((h.value for h in self.hardware_ids if h.kind == HardwareIdKind.PNP_ID), "")

    def to_body(self) -> dict:
        return {
            "observation_key": self.observation_key[:FIELD_MAX],
            "interface_name": self.interface_name[:FIELD_MAX],
            "name": self.name[:FIELD_MAX],
            "state": self.state,
            "hardware_ids": [h.to_body() for h in self.hardware_ids[:4]],
        }


def pnp_device(pnp_id: str, name: str = "", interface_name: Optional[str] = None) -> Optional[ObservedDevice]:
    """An observation for one PnP entity, or ``None`` when Windows gave no ID."""
    hardware_id = HardwareId.pnp(pnp_id)
    if not hardware_id.value or "\\" not in hardware_id.value:
        return None
    bus = enumerator(hardware_id.value)
    return ObservedDevice(
        observation_key=f"pnp:{hardware_id.value}"[:FIELD_MAX],
        interface_name=interface_name or bus,
        name=(name or "").strip() or hardware_id.value,
        hardware_ids=(hardware_id,),
    )


DISCOVERY_BUSES = frozenset({"USB", "USBSTOR", "FTDIBUS"})


def is_discoverable(device: ObservedDevice) -> bool:
    """Devices offered in a discovery snapshot: plugged-in USB hardware, not its function interfaces."""
    pnp_id = device.pnp_id
    return enumerator(pnp_id) in DISCOVERY_BUSES and "&MI_" not in pnp_id


def pick_interface_name(catalog: Iterable[str], wanted: str) -> str:
    """Use the backend catalog's spelling of the interface when it has one (matching ignores case)."""
    for name in catalog:
        if name.lower() == wanted.lower():
            return name
    return wanted
