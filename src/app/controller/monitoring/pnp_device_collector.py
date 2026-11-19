"""Scans this computer's PnP devices and reports the ones on the watch list.

The watch list comes from the monitoring policy: equipment expected on this computer with the PnP
IDs a coordinator registered on it. Only those devices are reported (collector ``pnp``); every
other device stays on the computer. A change counts after ``DEBOUNCE_SCANS`` consecutive scans.

An administrator can push a one-off **discovery** snapshot of the connected USB devices from the
Device Scan dialog, so a coordinator can register a new device's PnP ID with *Link*.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

import pythoncom
import wmi
from PySide6.QtCore import Signal

from src.core.agent_api import errors as agent_errors
from src.core.monitoring import (
    DeviceObservationReporter,
    ObservedDevice,
    WatchList,
    is_discoverable,
    pnp_device,
)
from src.mvc.base_thread import BaseThread, EHandle


class PnpDeviceCollector(BaseThread):
    watched_connected = Signal(str, str)  # expected unit name, PnP ID
    watched_disconnected = Signal(str, str)

    DEBOUNCE_SCANS = 3

    def __init__(
        self,
        reporter: DeviceObservationReporter,
        discovery_reporter: DeviceObservationReporter,
        scan_interval_s: float = 5.0,
        scanner: Optional[Callable[[], dict[str, ObservedDevice]]] = None,
    ):
        super().__init__(loop=True, interval=scan_interval_s, e_handle=EHandle.ONLY_E_CHANGE)
        self._reporter = reporter
        self._discovery_reporter = discovery_reporter
        self._scanner = scanner
        self._wmi = None
        self._lock = threading.Lock()
        self._watch_list: Optional[WatchList] = None
        self._present: dict[str, ObservedDevice] = {}  # latest scan, every device
        self._confirmed: dict[str, ObservedDevice] = {}  # debounced watched devices
        self._streak: dict[str, int] = {}
        self._has_baseline = False
        self._discovery_requested = False

    # ------------------------------------------------------------------ public

    @property
    def watch_list(self) -> Optional[WatchList]:
        return self._watch_list

    def set_watch_list(self, watch_list: WatchList) -> None:
        with self._lock:
            if watch_list == self._watch_list:
                return
            self._watch_list = watch_list
            self._has_baseline = False  # re-seed against the new list on the next scan

    @property
    def present_devices(self) -> list[ObservedDevice]:
        """Every device of the latest scan (for the Device Scan dialog)."""
        with self._lock:
            return sorted(self._present.values(), key=lambda d: d.name.lower())

    @property
    def watched_devices(self) -> list[ObservedDevice]:
        """Watched devices confirmed connected."""
        with self._lock:
            return sorted(self._confirmed.values(), key=lambda d: d.name.lower())

    def request_discovery(self) -> None:
        """Send a discovery snapshot after the next scan (admin action in the Device Scan dialog)."""
        self._discovery_requested = True

    # ------------------------------------------------------------------ thread

    def run(self) -> None:
        if self._scanner is not None:
            return super().run()
        pythoncom.CoInitialize()  # WMI objects belong to the thread that creates them
        try:
            super().run()
        finally:
            self._wmi = None
            pythoncom.CoUninitialize()

    def run_user(self) -> None:
        self.collect_once()

    def collect_once(self) -> None:
        """One cycle: scan, debounce the watched devices, report, and push discovery if asked."""
        found = self._scanner() if self._scanner else self._scan()
        with self._lock:
            self._present = found
        if self._watch_list is None:
            self._load_watch_list()
        if self._watch_list is not None:
            self._apply(self._watch_list.select(found.values()))
            self._report(self._reporter, self.watched_devices)
        if self._discovery_requested:
            self._discovery_requested = False
            watched = {d.observation_key for d in self._watch_list.select(found.values())} if self._watch_list else set()
            new = [d for d in found.values() if is_discoverable(d) and d.observation_key not in watched]
            self._report(self._discovery_reporter, new, force=True)  # only devices nobody registered yet

    # ------------------------------------------------------------------ internals

    def _load_watch_list(self) -> None:
        try:
            policy = self._reporter.refresh_policy()
        except agent_errors.NotEnrolled:
            return
        except agent_errors.AgentApiError as e:
            raise RuntimeError(f"Monitoring policy unavailable: {e}") from e
        self.set_watch_list(WatchList.from_policy(policy.expected_devices))

    def _scan(self) -> dict[str, ObservedDevice]:
        if self._wmi is None:
            self._wmi = wmi.WMI()
        found: dict[str, ObservedDevice] = {}
        try:
            for entity in self._wmi.Win32_PnPEntity():
                device = pnp_device(getattr(entity, "PNPDeviceID", "") or "", getattr(entity, "Name", "") or "")
                if device is not None:
                    found[device.observation_key] = device
        except Exception:
            self._wmi = None  # reconnect on the next scan
            raise
        return found

    def _label(self, device: ObservedDevice) -> str:
        expected = self._watch_list.match(device) if self._watch_list else None
        return expected.name if expected else device.name

    def _apply(self, watched: list[ObservedDevice]) -> None:
        found = {d.observation_key: d for d in watched}
        with self._lock:
            if not self._has_baseline:
                # The first scan after a (new) watch list is the current state: never report an
                # empty snapshot just because debouncing has not confirmed anything yet.
                self._confirmed = dict(found)
                self._streak.clear()
                self._has_baseline = True
                for device in found.values():
                    self.watched_connected.emit(self._label(device), device.pnp_id)
                return
            for key in set(found) | set(self._confirmed):
                differs = (key in found) != (key in self._confirmed)
                self._streak[key] = self._streak.get(key, 0) + 1 if differs else 0
                if self._streak[key] < self.DEBOUNCE_SCANS:
                    continue
                self._streak.pop(key, None)
                if key in found:
                    self._confirmed[key] = found[key]
                    self.watched_connected.emit(self._label(found[key]), found[key].pnp_id)
                else:
                    device = self._confirmed.pop(key)
                    self.watched_disconnected.emit(self._label(device), device.pnp_id)
            for key in [k for k in self._streak if k not in found and k not in self._confirmed]:
                del self._streak[key]

    @staticmethod
    def _report(reporter: DeviceObservationReporter, devices: list[ObservedDevice], force: bool = False) -> None:
        try:
            reporter.report(devices, force=force)
        except agent_errors.NotEnrolled:
            pass
        except agent_errors.AgentApiError as e:
            raise RuntimeError(f"Device report deferred: {e}") from e
