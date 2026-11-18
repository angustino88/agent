import os
import time
import json
import shutil
from datetime import datetime
from typing import Dict, Optional
from pyad import aduser
from PySide6.QtCore import QObject, Signal
from src.utils.windows import WindowsUtil
from src.app.model.types.user_attributes import UserAttributes

class UserStorageMonitor(QObject):
    """
    Monitors storage usage for individual user folders inside a parent folder.
    Only sends updates to the API if usage or quota has changed since last scan.
    Supports per-user quota from a config file if provided.
    """

    exception = Signal(Exception)     # Emits exceptions encountered during scanning

    def __init__(
        self,
        base_dir: str,
        api_model: object,
        storage_info_file: str,
        unit: str = "GB",
        quota: float = 15.0,
        user_quotas: Dict[str, float] = {}
    ):
        super().__init__()
        self.set_base_dir(base_dir)
        total, used, free = shutil.disk_usage(base_dir)
        self._total_available_gb = round(free / (1024 ** 3), 2)

        self._api_service = api_model.service
        self._storage_info_file = storage_info_file
        self._unit = unit
        self._quota = quota
        self._storage_info: Dict[str, float] = {}
        self._last_storage_info: Dict[str, Dict[str, float]] = {}
        self._user_quotas: Dict[str, float] = user_quotas
        self._load_last_storage_info()

    def run(self):
        """Scan user folders and handle storage info."""
        try:
            self._scan_user_folders()
            self._handle_storage_info()
            self._update_quota_files()
        except Exception as e:
            self.exception.emit(e)

    def _load_last_storage_info(self):
        """Load last storage info from file."""
        if os.path.exists(self._storage_info_file):
            try:
                with open(self._storage_info_file, "r", encoding="utf-8") as f:
                    self._last_storage_info = json.load(f)
            except Exception as e:
                self.exception.emit(Exception(f"Failed to load last storage info: {e}"))
                self._last_storage_info = {}
        else:
            self._last_storage_info = {}

    def _save_last_storage_info(self):
        """Save last storage info to file with pretty JSON format (indentation)."""
        try:
            with open(self._storage_info_file, "w", encoding="utf-8") as f:
                json.dump(self._last_storage_info, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.exception.emit(Exception(f"Failed to save last storage info: {e}"))

    def _scan_user_folders(self):
        """Scan all folders inside the users directory and update self._storage_info."""
        info: Dict[str, float] = {}

        for entry in os.scandir(self._users_dir):
            if not entry.is_dir():
                continue

            try:
                username = entry.name.strip().lower()
                size = WindowsUtil.get_folder_size(entry.path, unit=self._unit)
                info[username] = round(float(size), 2)
            except Exception as e:
                self.exception.emit(Exception(f"Failed to scan folder {entry.path}: {e}"))

        self._storage_info = info

    def _resolve_display_name(self, username: str) -> Optional[str]:
        """
        Return display name from AD, or None if lookup fails.
        If AD returns an empty display name, use the username.
        """
        try:
            ad_user = aduser.ADUser.from_cn(username)
            attrs = UserAttributes.from_aduser(ad_user)
            displayname = getattr(attrs, "user_displayname", "") or username
            return displayname
        except:
            pass
        return None

    def _send_quota(self, username: str, displayname: str, used: float, quota: float) -> bool:
        """
        Send storage quota to API. Returns True if successful, False if failed.
        """
        try:
            self._api_service.send_storage_quota(
                username=username,
                user_displayname=displayname,
                used=used,
                quota=quota
            )
            time.sleep(0.1)
            return True
        except Exception as e:
            return False
    
    def _handle_storage_info(self):
        """Sync storage info with API (only if changes detected)."""
        changed = False

        current_users = set(self._storage_info.keys())
        previous_users = set(self._last_storage_info.keys())

        # Users that need quota updates
        users_to_update = [
            u for u in current_users
            if (
                u not in self._last_storage_info
                or self._last_storage_info[u].get("used") != self._storage_info[u]
                or self._last_storage_info[u].get("quota") != self._user_quotas.get(u, self._quota)
            )
        ]

        # Users that need to be removed
        users_to_remove = previous_users - current_users

        # --- Handle updates ---
        for username in users_to_update:
            displayname = self._resolve_display_name(username) or f"{username} (Unknown)"
            used = self._storage_info[username]
            quota = self._user_quotas.get(username, self._quota)
            if self._send_quota(username, displayname, used, quota):
                self._last_storage_info[username] = {"used": used, "quota": quota}
                changed = True

        # --- Handle removals ---
        for username in users_to_remove:
            displayname = self._resolve_display_name(username) or f"{username} (Unknown)"
            quota = self._user_quotas.get(username, self._quota)
            if self._send_quota(username, displayname, 0, quota):
                del self._last_storage_info[username]
                changed = True

        # --- Save only if there were changes ---
        if changed:
            self._save_last_storage_info()

    def _update_quota_files(self):
        os.makedirs(self._quota_dir, exist_ok=True)
        total_used = 0.0
        now_dt = datetime.now()
        now = now_dt.isoformat(timespec="seconds")

        users_data = []
        for username, info in self._last_storage_info.items():
            used_gb = info["used"]
            quota_gb = round(info.get("quota", self._user_quotas.get(username, self._quota)), 2)
            total_used += used_gb
            user_path = os.path.join(self._users_dir, username)
            try:
                stat = os.stat(user_path)
                last_modified_dt = datetime.fromtimestamp(stat.st_mtime)
                last_modified = last_modified_dt.isoformat(timespec="seconds")
                inactive_days = (datetime.now() - last_modified_dt).days
            except Exception:
                last_modified = "unknown"
                inactive_days = None
            
            status = "OVER_LIMIT" if used_gb > quota_gb else "OK"

            data = {
                "username": username,
                "used_gb": used_gb,
                "quota_gb": quota_gb,
                "status": status,
                "last_checked": now,
                "last_modified": last_modified,
                "inactive_days": inactive_days
            }
            users_data.append(data)

        summary = {
            "total_users": len(self._last_storage_info),
            "total_used_gb": round(total_used, 2),
            "total_available_gb": self._total_available_gb,
            "last_scan": now
        }

        all_data = {
            "users": users_data,
            "summary": summary
        }

        try:
            with open(os.path.join(self._quota_dir, "quota_report.json"), "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=4)
        except Exception as e:
            self.exception.emit(Exception(f"Failed to write quota_report.json: {e}"))

    def set_base_dir(self, base_dir: str):
        """Dynamically update the base LabMango shared directory."""
        self._base_dir = base_dir
        self._users_dir = os.path.join(base_dir, "users")
        self._system_dir = os.path.join(base_dir, ".system")
        self._quota_dir = os.path.join(self._system_dir, "quota")
        self._logs_dir = os.path.join(self._system_dir, "logs")

        # Ensure required folders exist
        os.makedirs(self._quota_dir, exist_ok=True)
        os.makedirs(self._logs_dir, exist_ok=True)

    def set_quota(self, quota: float):
        """Dynamically update the quota value."""
        self._quota = quota