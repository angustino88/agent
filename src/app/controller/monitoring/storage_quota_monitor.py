"""Measures each user's folder on the shared drive and writes a local quota report.

Layout under the sharing root: ``users/<username>/`` (measured) and ``.system/quota/quota_report.json``
(written). The backend has no storage-quota route for agents, so nothing is sent.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from typing import Dict, Optional

from PySide6.QtCore import QObject, Signal

from src.utils.windows import WindowsUtil


class StorageQuotaMonitor(QObject):
    exception = Signal(Exception)

    REPORT_FILE_NAME = "quota_report.json"

    def __init__(
        self,
        sharing_root_dir: str,
        usage_file: str,
        default_quota_gb: float = 15.0,
        user_quotas_gb: Optional[Dict[str, float]] = None,
    ):
        super().__init__()
        self._usage_file = usage_file
        self._default_quota_gb = default_quota_gb
        self._user_quotas_gb = dict(user_quotas_gb or {})
        self.set_sharing_root_dir(sharing_root_dir)

    def set_sharing_root_dir(self, sharing_root_dir: str) -> None:
        self._root_dir = sharing_root_dir
        self._users_dir = os.path.join(sharing_root_dir, "users")
        self._quota_dir = os.path.join(sharing_root_dir, ".system", "quota")
        os.makedirs(self._quota_dir, exist_ok=True)
        os.makedirs(os.path.join(sharing_root_dir, ".system", "logs"), exist_ok=True)

    def set_default_quota(self, quota_gb: float) -> None:
        self._default_quota_gb = quota_gb

    def quota_for(self, username: str) -> float:
        return float(self._user_quotas_gb.get(username, self._default_quota_gb))

    def run(self) -> None:
        try:
            usage = self._measure()
            self._write_json(self._usage_file, {u: {"used": gb, "quota": self.quota_for(u)} for u, gb in usage.items()})
            self._write_report(usage)
        except Exception as e:
            self.exception.emit(e)

    # ------------------------------------------------------------------ internals

    def _measure(self) -> Dict[str, float]:
        usage: Dict[str, float] = {}
        if not os.path.isdir(self._users_dir):
            return usage
        for entry in os.scandir(self._users_dir):
            if not entry.is_dir():
                continue
            try:
                usage[entry.name.strip().lower()] = round(float(WindowsUtil.get_folder_size(entry.path, unit="GB")), 2)
            except Exception as e:
                self.exception.emit(Exception(f"Could not measure {entry.path}: {e}"))
        return usage

    def _write_report(self, usage: Dict[str, float]) -> None:
        now = datetime.now()
        users = []
        for username, used_gb in sorted(usage.items()):
            quota_gb = round(self.quota_for(username), 2)
            try:
                modified = datetime.fromtimestamp(os.stat(os.path.join(self._users_dir, username)).st_mtime)
                last_modified, inactive_days = modified.isoformat(timespec="seconds"), (now - modified).days
            except OSError:
                last_modified, inactive_days = "unknown", None
            users.append(
                {
                    "username": username,
                    "used_gb": used_gb,
                    "quota_gb": quota_gb,
                    "status": "OVER_LIMIT" if used_gb > quota_gb else "OK",
                    "last_checked": now.isoformat(timespec="seconds"),
                    "last_modified": last_modified,
                    "inactive_days": inactive_days,
                }
            )
        free_gb = round(shutil.disk_usage(self._root_dir).free / (1024**3), 2)
        summary = {
            "total_users": len(users),
            "total_used_gb": round(sum(usage.values()), 2),
            "total_available_gb": free_gb,
            "last_scan": now.isoformat(timespec="seconds"),
        }
        self._write_json(os.path.join(self._quota_dir, self.REPORT_FILE_NAME), {"users": users, "summary": summary})

    @staticmethod
    def _write_json(path: str, data: dict) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
