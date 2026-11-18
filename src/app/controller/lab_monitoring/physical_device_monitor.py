import os
import json
import wmi
import copy
from PySide6.QtCore import Signal
from src.mvc.base_thread import BaseThread, EHandle


class PhysicalDeviceMonitor(BaseThread):
    device_inserted = Signal(str, str)  # object_name, device_id
    device_removed = Signal(str, str)

    _DEBOUNCE_THRESHOLD = 3  # Require 3 consecutive detections before confirming change

    def __init__(self, 
        api_service,
        device_tracking_file="devices.json",
        poll_interval=1.0
    ):
        super().__init__(loop=True, interval=poll_interval, e_handle=EHandle.ONLY_E_CHANGE)
        self._api_service = api_service
        self._device_tracking_file = device_tracking_file
        self._session_info = None
        self._device_filter_map = {}
        self._last_devices = {}
        self._wmi = wmi.WMI()
        self._device_list = []
        self._debounce_map = {}  # {dev_id: {"state": "present"/"missing", "count": int}}

        self.load_device_filters()
        self._load_device_state()

    def _initialize_wmi(self):
        try:
            self._wmi = wmi.WMI()
        except Exception as e:
            self._wmi = None
            self.exception.emit(e)

    def _reconnect_wmi(self):
        try:
            self._initialize_wmi()
        except Exception:
            pass

    def update_session_info(self, session_info):
        self._session_info = session_info

    def load_device_filters(self):
        """Public: Load device filters from API and strip key/value."""
        try:
            resp = self._api_service.get_computer_monitoring(timeout=5)
            if not resp.success:
                raise ValueError(f"get_computer_monitoring failed (status={resp.status_code})")
            data = resp.data
            if not isinstance(data, list):
                raise ValueError("Monitoring payload not a list")
            self._device_list = data
            self._device_filter_map = {
                str(f.get("key", "")).strip().upper(): str(f.get("value", "")).strip()
                for f in self._device_list
                if isinstance(f, dict)
            }
        except Exception as e:
            self._device_list = []
            self._device_filter_map = {}
            self.exception.emit(e)

    def _load_device_state(self):
        if os.path.exists(self._device_tracking_file):
            try:
                with open(self._device_tracking_file, "r", encoding="utf-8") as f:
                    self._last_devices = json.load(f)
            except Exception:
                self._last_devices = {}
        else:
            self._last_devices = {}

    def _save_device_state(self):
        try:
            with open(self._device_tracking_file, "w", encoding="utf-8") as f:
                json.dump(self._last_devices, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.exception.emit(e)

    def _collect_filtered_devices(self):
        devices = {}
        if not self._device_filter_map:
            return devices  # Skip all if no filters

        if not self._wmi:
            self._reconnect_wmi()
            if not self._wmi:
                return self._last_devices

        try:
            for dev in self._wmi.Win32_PnPEntity():
                dev_id = getattr(dev, "PNPDeviceID", "").strip().replace("\\", "/").upper()
                if not dev_id:
                    continue
                if dev_id in self._device_filter_map:
                    filter_name = self._device_filter_map.get(dev_id)
                    device_name = getattr(dev, "Name", dev_id)
                    devices[dev_id] = f"{filter_name} [{device_name}]"
        except Exception as e:
            self.exception.emit(e)
            self._reconnect_wmi()
            return self._last_devices

        try:
            for disk in self._wmi.Win32_DiskDrive(InterfaceType="USB"):
                dev_id = getattr(disk, "PNPDeviceID", "").strip().replace("\\", "/").upper()
                if not dev_id:
                    continue
                if dev_id not in self._device_filter_map:
                    continue
                model_name = getattr(disk, "Model", getattr(disk, "Name", dev_id))
                filter_name = self._device_filter_map.get(dev_id)
                name = f"{filter_name} [{model_name}]"
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

        return devices

    def _sync_devices_on_startup(self):
        """Ensure correct initial state on first run."""
        if not self._device_filter_map:
            return

        current_devices = self._collect_filtered_devices()

        for dev_id, name in current_devices.items():
            dev_id = dev_id.upper()
            if dev_id not in self._last_devices:
                obj_name = self._device_filter_map.get(dev_id, name)
                self.device_inserted.emit(obj_name, dev_id)
                self._send_monitoring_event("device_inserted", obj_name, dev_id)

        for dev_id, name in self._last_devices.items():
            if dev_id not in current_devices:
                obj_name = self._device_filter_map.get(dev_id, name)
                self.device_removed.emit(obj_name, dev_id)
                self._send_monitoring_event("device_removed", obj_name, dev_id)

        self._send_all_device_status(current_devices)
        self._last_devices = current_devices
        self._save_device_state()

    def run(self):
        """Public: Sync devices on startup and start monitoring loop."""
        self._sync_devices_on_startup()
        super().run()

    def run_user(self):
        self._sync_devices_periodically()

    def _sync_devices_periodically(self):
        if not self._device_filter_map:
            return

        current_devices = self._collect_filtered_devices()
        all_ids = set(self._last_devices.keys()) | set(current_devices.keys())

        for dev_id in all_ids:
            in_last = dev_id in self._last_devices
            in_now = dev_id in current_devices
            record = self._debounce_map.setdefault(dev_id, {"state": None, "count": 0})
            prev_state = record["state"]

            # Device disappeared
            if in_last and not in_now:
                if prev_state != "missing":
                    record["state"] = "missing"
                    record["count"] = 1
                else:
                    record["count"] += 1
                if record["count"] >= self._DEBOUNCE_THRESHOLD:
                    obj_name = self._device_filter_map.get(dev_id, self._last_devices[dev_id])
                    self.device_removed.emit(obj_name, dev_id)
                    self._send_monitoring_event("device_removed", obj_name, dev_id)
                    self._last_devices.pop(dev_id, None)
                    self._save_device_state()
                    record["state"] = None
                    record["count"] = 0

            # Device appeared
            elif not in_last and in_now:
                if prev_state != "present":
                    record["state"] = "present"
                    record["count"] = 1
                else:
                    record["count"] += 1
                if record["count"] >= self._DEBOUNCE_THRESHOLD:
                    obj_name = self._device_filter_map.get(dev_id, current_devices[dev_id])
                    self.device_inserted.emit(obj_name, dev_id)
                    self._send_monitoring_event("device_inserted", obj_name, dev_id)
                    self._last_devices[dev_id] = current_devices[dev_id]
                    self._save_device_state()
                    record["state"] = None
                    record["count"] = 0

            # Device stable (present in both or missing in both)
            else:
                # Only reset if state is not already None
                if record["state"] is not None:
                    record["state"] = None
                    record["count"] = 0

        # Clean up debounce map for devices no longer tracked
        tracked_ids = set(self._last_devices.keys()) | set(current_devices.keys())
        for dev_id in list(self._debounce_map.keys()):
            if dev_id not in tracked_ids:
                del self._debounce_map[dev_id]

        # Only update backend if there’s an actual difference
        if current_devices != self._last_devices:
            self._send_all_device_status(current_devices)

    def _send_all_device_status(self, current_devices: dict):
        updated = False
        device_list = copy.deepcopy(self._device_list)

        for dev in device_list:
            dev_id = str(dev.get('key')).strip().upper()
            dev['status'] = dev_id in current_devices
            updated = True

        if updated:
            try:
                resp = self._api_service.update_computer_monitoring(device_list)
                if getattr(resp, "success", False):
                    self._device_list = device_list
                else:
                    self.exception.emit(Exception("Failed to update monitoring status"))
            except Exception as e:
                self.exception.emit(e)

    def _send_monitoring_event(self, event_type, obj_name, dev_id):
        try:
            resp = self._api_service.send_lab_monitoring_event(
                event_type=event_type,
                category="hardware",
                object_name=obj_name,
                object_id=dev_id,
                technical_user=getattr(self._session_info, "technical_user", None),
                remote_user=getattr(self._session_info, "remote_user", None),
                details=None
            )
            if not resp.success:
                self.exception.emit(Exception(f"Failed to send {event_type} for {dev_id}"))
        except Exception as e:
            self.exception.emit(e)
