"""Device monitoring: what the agent observes and how it reports it to the backend. Qt-free."""

from .devices import (
    USB_COLLECTOR_KEY,
    USB_INTERFACE_NAME,
    HardwareId,
    HardwareIdKind,
    ObservedDevice,
    UsbInstance,
    parse_usb_instance_id,
    pick_interface_name,
    usb_device,
)
from .reporter import DeviceObservationReporter

__all__ = [
    "USB_COLLECTOR_KEY",
    "USB_INTERFACE_NAME",
    "DeviceObservationReporter",
    "HardwareId",
    "HardwareIdKind",
    "ObservedDevice",
    "UsbInstance",
    "parse_usb_instance_id",
    "pick_interface_name",
    "usb_device",
]
