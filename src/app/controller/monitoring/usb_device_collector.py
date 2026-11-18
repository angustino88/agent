"""Collects connected USB devices with WMI and reports them to the backend.

Every connected top-level USB device is reported with its serial number; the backend matches
serials to equipment declared on this computer, so no local filter list is needed. A device must
be seen (or missed) on ``DEBOUNCE_SCANS`` consecutive scans before its change counts.
"""

from __future__ import annotations

import threading
from typing import Optional

import pythoncom
import wmi
from PySide6.QtCore import Signal

from src.core.agent_api import errors as agent_errors
from src.core.monitoring import (
    USB_INTERFACE_NAME,
    DeviceObservationReporter,
    ObservedDevice,
    pick_interface_name,
    usb_device,
)
from src.mvc.base_thread import BaseThread, EHandle


class UsbDeviceCollector(BaseThread):
    device_connected = Signal(str, str)  # name, observation key
    device_disconnected = Signal(str, str)

    DEBOUNCE_SCANS = 3

    def __init__(self, reporter: Optional[DeviceObservationReporter], scan_interval_s: float = 5.0):
        super().__init__(loop=True, interval=scan_interval_s, e_handle=EHandle.ONLY_E_CHANGE)
        self._reporter = reporter
        self._wmi = None
        self._interface_name = USB_INTERFACE_NAME
        self._confirmed: dict[str, ObservedDevice] = {}
        self._streak: dict[str, int] = {}  # key -> consecutive scans disagreeing with confirmed state
        self._has_baseline = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ public

    @property
    def devices(self) -> list[ObservedDevice]:
        """Confirmed connected devices, for display."""
        with self._lock:
            return sorted(self._confirmed.values(), key=lambda d: d.name.lower())

    def set_reporter(self, reporter: Optional[DeviceObservationReporter]) -> None:
        self._reporter = reporter

    def set_interface_catalog(self, interface_names) -> None:
        """Spell the interface the way the backend catalog does."""
        self._interface_name = pick_interface_name(interface_names)

    # ------------------------------------------------------------------ thread

    def run(self) -> None:
        pythoncom.CoInitialize()  # WMI objects belong to the thread that creates them
        try:
            super().run()
        finally:
            self._wmi = None
            pythoncom.CoUninitialize()

    def run_user(self) -> None:
        self._apply_scan(self._scan())
        self._report()

    # ------------------------------------------------------------------ internals

    def _scan(self) -> dict[str, ObservedDevice]:
        if self._wmi is None:
            self._wmi = wmi.WMI()
        found: dict[str, ObservedDevice] = {}
        try:
            for entity in self._wmi.Win32_PnPEntity():
                device = usb_device(
                    getattr(entity, "PNPDeviceID", "") or "", getattr(entity, "Name", "") or "", self._interface_name
                )
                if device is not None:
                    found[device.observation_key] = device
        except Exception:
            self._wmi = None  # reconnect on the next scan
            raise
        return found

    def _apply_scan(self, found: dict[str, ObservedDevice]) -> None:
        with self._lock:
            if not self._has_baseline:
                # The first scan is the current state: report it as is, never as an empty snapshot.
                self._confirmed = dict(found)
                self._has_baseline = True
                for key, device in found.items():
                    self.device_connected.emit(device.name, key)
                return
            for key in set(found) | set(self._confirmed):
                differs = (key in found) != (key in self._confirmed)
                self._streak[key] = self._streak.get(key, 0) + 1 if differs else 0
                if self._streak[key] < self.DEBOUNCE_SCANS:
                    continue
                self._streak.pop(key, None)
                if key in found:
                    self._confirmed[key] = found[key]
                    self.device_connected.emit(found[key].name, key)
                else:
                    device = self._confirmed.pop(key)
                    self.device_disconnected.emit(device.name, key)
            for key in list(self._streak):
                if key not in found and key not in self._confirmed:
                    del self._streak[key]

    def _report(self) -> None:
        if self._reporter is None:
            return
        try:
            self._reporter.report(self.devices)
        except agent_errors.NotEnrolled:
            pass
        except agent_errors.AgentApiError as e:
            raise RuntimeError(f"Device observation report deferred: {e}") from e
