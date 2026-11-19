"""Device monitoring: PnP devices on this computer, the watch list, and reporting. Qt-free."""

from .devices import (
    CONNECTED,
    DISCONNECTED,
    HardwareId,
    HardwareIdKind,
    ObservedDevice,
    enumerator,
    is_discoverable,
    is_port_bound,
    normalize_hardware_id,
    pick_interface_name,
    pnp_device,
)
from .reporter import DeviceObservationReporter
from .watch_list import ExpectedDevice, WatchList

PNP_COLLECTOR_KEY = "pnp"  # devices on the watch list
DISCOVERY_COLLECTOR_KEY = "discovery"  # one-off snapshots an administrator pushes from the agent

__all__ = [
    "CONNECTED",
    "DISCONNECTED",
    "DISCOVERY_COLLECTOR_KEY",
    "PNP_COLLECTOR_KEY",
    "DeviceObservationReporter",
    "ExpectedDevice",
    "HardwareId",
    "HardwareIdKind",
    "ObservedDevice",
    "WatchList",
    "enumerator",
    "is_discoverable",
    "is_port_bound",
    "normalize_hardware_id",
    "pick_interface_name",
    "pnp_device",
]
