from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional, Dict
from .package import Package
from .version import Version, InvalidVersion


@dataclass
class UpdateResult:
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
    """Pure parser: converts a raw update-check response dict into an UpdateResult.

    No network I/O — the caller is responsible for fetching the response from
    the remote service and handling transport-level errors before calling parse().
    """

    @staticmethod
    def parse(
        data: dict,
        current_version: str,
        logger: logging.Logger | None = None,
    ) -> UpdateResult:
        current_version = str(current_version).strip()
        latest_raw = data.get("latest_version") or current_version
        latest = str(latest_raw).strip()
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

        # Normalize changelog
        if isinstance(raw_changelog, list):
            raw_changelog = "\n".join(str(x) for x in raw_changelog if x is not None)
        elif raw_changelog is None:
            raw_changelog = ""
        else:
            try:
                raw_changelog = str(raw_changelog)
            except Exception:
                raw_changelog = ""
        raw_changelog = raw_changelog.strip() or "(no changelog provided)"

        try:
            newer = Version(latest) > Version(current_version)
        except InvalidVersion:
            newer = latest != current_version

        has_update = server_flag or newer

        if not has_update:
            return UpdateResult(
                has_update=False,
                current_version=current_version,
                latest_version=latest,
                update_type=update_type,
                versions=versions,
                changelog=raw_changelog,
                checksum=checksum,
                size_bytes=size_bytes,
                size_human=UpdateChecker._human_size(size_bytes),
                download_token=download_token,
                requires=requires,
                released_at=released_at,
                raw=data,
            )

        if not download_url:
            msg = "missing download_url for available update"
            if logger:
                logger.error(f"[update] {msg}")
            return UpdateResult(
                has_update=False,
                current_version=current_version,
                latest_version=latest,
                error=msg,
                requires=requires,
                released_at=released_at,
                raw=data,
            )

        if checksum and not UpdateChecker._valid_checksum(checksum):
            if logger:
                logger.warning("[update] checksum format appears invalid")

        if not update_type:
            inferred = UpdateChecker._classify(current_version, latest)
            if inferred:
                update_type = inferred

        try:
            pkg = Package(
                name=data.get("app_name") or data.get("name"),
                version=latest,
                path=download_url,
                checksum=checksum,
                size_bytes=size_bytes,
                download_token=download_token,
            )
        except KeyError as e:
            msg = f"malformed response missing {e}"
            if logger:
                logger.error(f"[update] {msg}")
            return UpdateResult(
                has_update=False,
                current_version=current_version,
                latest_version=latest,
                error=msg,
                requires=requires,
                released_at=released_at,
                raw=data,
            )

        if logger:
            logger.info(
                f"[update] available current={current_version} latest={latest} "
                f"type={update_type or 'unknown'} size={size_bytes or '-'}"
            )

        return UpdateResult(
            has_update=True,
            current_version=current_version,
            latest_version=latest,
            package=pkg,
            update_type=update_type,
            versions=versions,
            changelog=raw_changelog,
            checksum=checksum,
            size_bytes=size_bytes,
            size_human=UpdateChecker._human_size(size_bytes),
            download_token=download_token,
            requires=requires,
            released_at=released_at,
            raw=data,
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
        if cv.major != lv.major:
            return "major"
        if cv.minor != lv.minor:
            return "minor"
        return "patch"

    @staticmethod
    def _valid_checksum(chk: str | None) -> bool:
        if not chk:
            return True
        return all(c in "0123456789abcdefABCDEF" for c in chk) and len(chk) in (40, 64)
