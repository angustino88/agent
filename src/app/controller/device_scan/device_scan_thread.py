import re
import wmi
import pythoncom
from PySide6.QtCore import Signal
from src.mvc.base_thread import BaseThread, EHandle


class DeviceScanThread(BaseThread):
    device_inserted = Signal(str, str)  # name, device_id
    device_removed = Signal(str, str)

    def __init__(self):
        super().__init__(loop=True, interval=0, e_handle=EHandle.ONLY_E_CHANGE)
        self._wmi = None
        self._insert_watcher = None
        self._remove_watcher = None
        self._last_devices = {}

    # -------------------- Helpers --------------------
    def _extract_vid_pid(self, dev_id: str):
        match = re.search(r"VID_([0-9A-F]{4})&PID_([0-9A-F]{4})", dev_id, re.I)
        if match:
            return match.group(1).upper(), match.group(2).upper()
        return None, None

    def _group_main_devices(self, devices: dict):
        grouped = {}
        for dev_id, name in devices.items():
            vidpid = self._extract_vid_pid(dev_id)
            if not vidpid[0]:
                continue
            key = f"{vidpid[0]}:{vidpid[1]}"
            grouped.setdefault(key, []).append((dev_id, name))

        main_devices = {}
        for key, entries in grouped.items():
            composite = [e for e in entries if "Composite" in e[1]]
            if composite:
                main_devices[key] = composite[0]
            else:
                main_devices[key] = entries[0]
        return main_devices

    def _collect_filtered_devices(self):
        devices = {}
        if self._wmi is None:
            self._initialize_wmi()
            if self._wmi is None:
                return self._last_devices

        try:
            for dev in self._wmi.Win32_PnPEntity():
                dev_id = getattr(dev, "PNPDeviceID", "").strip().replace("\\", "/")
                if not dev_id:
                    continue
                devices[dev_id] = getattr(dev, "Name", dev_id)
        except Exception as e:
            self.exception.emit(e)
            self._reconnect_wmi()
            return self._last_devices

        try:
            for disk in self._wmi.Win32_DiskDrive(InterfaceType="USB"):
                dev_id = getattr(disk, "PNPDeviceID", "").strip().replace("\\", "/")
                if not dev_id:
                    continue
                name = getattr(disk, "Model", getattr(disk, "Name", dev_id))
                drives = []
                for part in disk.associators("Win32_DiskDriveToDiskPartition"):
                    for logical in part.associators("Win32_LogicalDiskToPartition"):
                        drives.append(getattr(logical, "DeviceID", ""))
                if drives:
                    name = f"{name} ({', '.join(drives)})"
                devices[dev_id] = name
        except Exception as e:
            self.exception.emit(e)
            self._reconnect_wmi()
            return self._last_devices

        main_devices = self._group_main_devices(devices)
        return {dev_id: name for dev_id, name in main_devices.values()}

    # -------------------- WMI init --------------------
    def _initialize_wmi(self):
        try:
            self._wmi = wmi.WMI()
            self._insert_watcher = self._wmi.watch_for(notification_type="Creation", wmi_class="Win32_PnPEntity")
            self._remove_watcher = self._wmi.watch_for(notification_type="Deletion", wmi_class="Win32_PnPEntity")
        except Exception as e:
            self._wmi = None
            self.exception.emit(e)

    # -------------------- Thread main loop --------------------
    def run(self):
        pythoncom.CoInitialize()
        try:
            self._initialize_wmi()

            # Initial scan
            current_devices = self._collect_filtered_devices()
            self._last_devices = current_devices.copy()
            for dev_id, name in current_devices.items():
                self.device_inserted.emit(name, dev_id)

            # Event watcher loop
            while not self._thread_kill:
                try:
                    inserted = None
                    removed = None

                    try:
                        inserted = self._insert_watcher(timeout_ms=500)
                    except wmi.x_wmi_timed_out:
                        pass
                    try:
                        removed = self._remove_watcher(timeout_ms=500)
                    except wmi.x_wmi_timed_out:
                        pass

                    if inserted:
                        new_snapshot = self._collect_filtered_devices()
                        for dev_id, name in new_snapshot.items():
                            if dev_id not in self._last_devices:
                                self.device_inserted.emit(name, dev_id)
                        self._last_devices = new_snapshot

                    if removed:
                        new_snapshot = self._collect_filtered_devices()
                        for dev_id in self._last_devices:
                            if dev_id not in new_snapshot:
                                self.device_removed.emit(self._last_devices[dev_id], dev_id)
                        self._last_devices = new_snapshot

                except Exception as e:
                    self.exception.emit(e)
                    self._initialize_wmi()
        finally:
            pythoncom.CoUninitialize()
