import json
import os
from PySide6.QtCore import QObject, Signal

class ComputerInfoMonitor(QObject):
    """
    Monitors and reports computer information (OS, IP, disk usage, system info) to the API.
    Always sends info (for PUT) and only updates saved data if send succeeds.
    """

    exception = Signal(Exception)

    def __init__(self, computer_model: object, api_service: object, computer_info_file: str):
        super().__init__()
        self._computer_model = computer_model
        self._api_service = api_service
        self._computer_info_file = computer_info_file

    def run(self):
        """Collect and send computer info, update record only if send succeeds."""
        try:
            computer_info = self._collect_computer_info()
            success = self._update_computer_info(computer_info)
            if success:
                self._save_computer_info(computer_info)
        except Exception as e:
            self.exception.emit(e)

    def _get_disk_usage(self):
        original_data = self._computer_model.get_disk_usage()
        return [
            {
                "name": d.get("name", "").replace("\\", ""),
                "used": int(d.get("used_gb", 0)),
                "total": int(d.get("total_gb", 0))
            }
            for d in original_data
        ]

    def _get_sys_info(self):
        sys_info_dict = self._computer_model.get_system_info()
        return [
            {
                "item": k,
                "value": json.dumps(v, ensure_ascii=False, sort_keys=True)
                if isinstance(v, (dict, list)) else str(v)
            }
            for k, v in sys_info_dict.items()
        ]

    def _collect_computer_info(self):
        return {
            "os_name": getattr(self._computer_model, "os_name", ""),
            "computer_ip": getattr(self._computer_model, "computer_ip", ""),
            "disk_usage": self._get_disk_usage(),
            "sys_info": self._get_sys_info()
        }

    def _update_computer_info(self, computer_info):
        response = self._api_service.update_computer_info(computer_info)
        return True if response.success else False

    def _save_computer_info(self, computer_info):
        """Save computer info to JSON file (pretty format)."""
        with open(self._computer_info_file, "w", encoding="utf-8") as f:
            json.dump(computer_info, f, indent=2, ensure_ascii=False)
 