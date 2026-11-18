"""Device observations as the backend expects them (``DeviceObservation``).

The backend matches each reported ``serial_number`` against equipment declared on this
computer's interfaces, so the agent reports every device it sees and never filters by a local
list. ``observation_key`` must stay stable for the same physical device across snapshots.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable, Optional

USB_COLLECTOR_KEY = "usb"
USB_INTERFACE_NAME = "USB"
_FIELD_MAX = 255
_USB_INSTANCE = re.compile(r"^USB\\VID_([0-9A-F]{4})&PID_([0-9A-F]{4})(&[^\\]*)?\\(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class ObservedDevice:
    observation_key: str
    interface_name: str
    name: str = ""
    serial_number: str = ""
    state: str = "connected"  # connected | disconnected

    def to_body(self) -> dict:
        return {key: value[:_FIELD_MAX] for key, value in asdict(self).items()}


@dataclass(frozen=True)
class UsbInstance:
    vendor_id: str
    product_id: str
    serial_number: str  # empty when Windows generated the instance id (device has no serial)
    is_interface: bool  # a function of a composite device (``&MI_xx``), not the device itself


def parse_usb_instance_id(pnp_device_id: str) -> Optional[UsbInstance]:
    r"""Parse a Windows USB instance id such as ``USB\VID_0403&PID_6001\A12BC3``.

    Windows builds instance ids that contain ``&`` when the device reports no serial number,
    so such ids are not serial numbers. Returns ``None`` for non-USB ids.
    """
    match = _USB_INSTANCE.match((pnp_device_id or "").strip())
    if not match:
        return None
    vendor, product, suffix, instance = match.groups()
    serial = "" if "&" in instance else instance
    return UsbInstance(
        vendor_id=vendor.upper(),
        product_id=product.upper(),
        serial_number=serial,
        is_interface="&MI_" in (suffix or "").upper(),
    )


def usb_device(pnp_device_id: str, name: str, interface_name: str = USB_INTERFACE_NAME) -> Optional[ObservedDevice]:
    """An observation for a top-level USB device, or ``None`` for interfaces and non-USB ids."""
    instance = parse_usb_instance_id(pnp_device_id)
    if instance is None or instance.is_interface:
        return None
    return ObservedDevice(
        observation_key=f"usb:{pnp_device_id.strip().lower()}",
        interface_name=interface_name,
        name=(name or "").strip() or f"USB {instance.vendor_id}:{instance.product_id}",
        serial_number=instance.serial_number,
    )


def pick_interface_name(catalog: Iterable[str], wanted: str = USB_INTERFACE_NAME) -> str:
    """Use the backend catalog's spelling of the interface when it has one (matching ignores case)."""
    for name in catalog:
        if name.lower() == wanted.lower():
            return name
    return wanted
