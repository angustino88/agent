from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional, Dict
from src.pkgman.package import Package
from src.pkgman.version import Version, InvalidVersion

@dataclass
class PackageUpdate:
    has_update: bool
    current_version: str
    latest_version: str | None = None
    package: Package | None = None
    update_type: str | None = None
    versions: list[str] | None = None
    changelog: str | None = None
    checksum: str | None = None
    size_bytes: int | None = None
    size_human: str | None = None
    download_token: str | None = None
    requires: Dict[str, str] | None = None
    released_at: str | None = None
    error: str | None = None
    raw: dict | None = None

    @property
    def download_url(self) -> str | None:
        return self.package.path if self.package else None

class UpdateChecker:
    def __init__(self, service, logger: logging.Logger, timeout: int = 15):
        self._svc = service
        self._logger = logger
        self._timeout = timeout

    # ---------- public ----------
    def check(self, current_version: str) -> PackageUpdate:
        try:
            resp = self._svc.check_package_update(current_version, timeout=self._timeout)
        except Exception as e:
            self._logger.warning(f"[update] request error: {e}")
            return PackageUpdate(False, current_version, error=str(e))

        if not getattr(resp, "success", False) or not resp.data:
            msg = f"backend failure status={getattr(resp,'status_code',None)}"
            self._logger.warning(f"[update] {msg}")
            return PackageUpdate(False, current_version, error=msg, raw=getattr(resp, "data", None))

        data = resp.data or {}
        latest = (data.get("latest_version") or current_version).strip()
        download_url = data.get("download_url")
        checksum = data.get("checksum")
        size_bytes = data.get("size_bytes") if isinstance(data.get("size_bytes"), int) else None
        versions = data.get("versions") if isinstance(data.get("versions"), list) else None
        update_type = data.get("update_type")
        raw_changelog = data.get("changelog")
        download_token = data.get("download_token")
        server_flag = bool(data.get("update_available"))
        requires = data.get("requires")
        if not isinstance(requires, dict):
            requires = None
        released_at = data.get("released_at") or data.get("release_at")

        # Normalize changelog:
        if isinstance(raw_changelog, list):
            # Join list elements (skip None)
            raw_changelog = "\n".join(str(x) for x in raw_changelog if x is not None)
        elif raw_changelog is None:
            raw_changelog = ""
        else:
            try:
                raw_changelog = str(raw_changelog)
            except Exception:
                raw_changelog = ""
        raw_changelog = raw_changelog.strip()
        if not raw_changelog:
            raw_changelog = "(no changelog provided)"

        try:
            newer = Version(latest) > Version(current_version)
        except InvalidVersion:
            newer = latest != current_version

        has_update = server_flag or newer

        if not has_update:
            return PackageUpdate(
                has_update=False,
                current_version=current_version,
                latest_version=latest,
                update_type=update_type,
                versions=versions,
                changelog=raw_changelog,
                checksum=checksum,
                size_bytes=size_bytes,
                size_human=self._human_size(size_bytes),
                download_token=download_token,
                requires=requires,
                released_at=released_at,
                raw=data
            )

        if not download_url:
            msg = "missing download_url for available update"
            self._logger.error(f"[update] {msg}")
            return PackageUpdate(
                has_update=False,
                current_version=current_version,
                latest_version=latest,
                error=msg,
                requires=requires,
                released_at=released_at,
                raw=data
            )

        if checksum and not self._valid_checksum(checksum):
            self._logger.warning("[update] checksum format appears invalid")

        if not update_type:
            inferred = self._classify(current_version, latest)
            if inferred:
                update_type = inferred

        try:
            pkg = Package(
                name=data.get("app_name") or data.get("name") or "LabMango",
                version=latest,
                path=download_url,
                checksum=checksum,
                size_bytes=size_bytes,
                download_token=download_token
            )
        except KeyError as e:
            msg = f"malformed response missing {e}"
            self._logger.error(f"[update] {msg}")
            return PackageUpdate(
                has_update=False,
                current_version=current_version,
                latest_version=latest,
                error=msg,
                requires=requires,
                released_at=released_at,
                raw=data
            )

        self._logger.info(
            f"[update] available current={current_version} latest={latest} "
            f"type={update_type or 'unknown'} size={size_bytes or '-'}"
        )

        return PackageUpdate(
            has_update=True,
            current_version=current_version,
            latest_version=latest,
            package=pkg,
            update_type=update_type,
            versions=versions,
            changelog=raw_changelog,
            checksum=checksum,
            size_bytes=size_bytes,
            size_human=self._human_size(size_bytes),
            download_token=download_token,
            requires=requires,
            released_at=released_at,
            raw=data
        )

    # ---------- helpers ----------
    @staticmethod
    def _human_size(n: Optional[int]) -> str | None:
        if not isinstance(n, int) or n < 0:
            return None
        units = ["B", "KB", "MB", "GB", "TB"]
        f = float(n)
        for u in units:
            if f < 1024 or u == units[-1]:
                return f"{f:.1f} {u}"
            f /= 1024
        return None

    @staticmethod
    def _classify(current: str, latest: str) -> str | None:
        try:
            cv, lv = Version(current), Version(latest)
        except InvalidVersion:
            return None
        if not (lv > cv):
            return None
        current = (str(cv).split(".") + ["0", "0", "0"])[:3]
        latest = (str(lv).split(".") + ["0", "0", "0"])[:3]
        if current[0] != latest[0]:
            return "major"
        if current[1] != latest[1]:
            return "minor"
        return "patch"

    @staticmethod
    def _valid_checksum(chk: str | None) -> bool:
        if not chk:
            return True
        return all(c in "0123456789abcdefABCDEF" for c in chk) and len(chk) in (40, 64)