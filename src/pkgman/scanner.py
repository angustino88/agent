from __future__ import annotations
import re
import base64
import logging
import requests
from typing import Optional, Dict, List
from .package import Package
from .version import Version
from .logprint import LogPrintMixin


class PackageScanner(LogPrintMixin):
    """Scans an Artifactory repository for valid application package files and extracts their versions."""

    def __init__(
        self,
        app_name: str,
        repo: str,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        logger: logging.Logger | None = None,
        printer=print,
    ) -> None:
        super().__init__(logger, printer)
        self._app_name = app_name
        self._repo = repo
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._api_key = api_key
        self._packages: Dict[Version, Package] = {}

    def _normalize_segment(self, s: str | None) -> str:
        return (s or "").strip("/")

    def _build_url(self, *segments: str) -> str:
        """
        Join URL parts ignoring empty segments to avoid double slashes.
        """
        base = self._base_url.rstrip("/")
        cleaned = [self._normalize_segment(p) for p in segments if p is not None and p != ""]
        return "/".join([base] + cleaned)

    def _headers(self) -> dict:
        if self._api_key:
            return {"Authorization": f"Bearer {self._api_key}"}
        return {}

    def _request(self, url: str):
        headers = {}
        if self._username and self._api_key:
            token = base64.b64encode(f"{self._username}:{self._api_key}".encode()).decode()
            headers["Authorization"] = f"Basic {token}"
            return requests.get(url, headers=headers)
        elif self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
            return requests.get(url, headers=headers)
        elif self._username and self._password:
            return requests.get(url, auth=(self._username, self._password))
        else:
            return requests.get(url)

    def extract_version(self, filename: str) -> Optional[Version]:
        """
        Extract the version from a package filename.
        Accepts pre-releases like 1.2.3-beta, 1.2.3_rc1, etc.
        """
        match = re.search(rf"{re.escape(self._app_name)}-([\w\.\-\_]+)\.zip", filename)
        if match:
            try:
                # Replace underscores with hyphens for consistent pre-release format
                return Version(match.group(1).replace("_", "-"))
            except Exception:
                pass
        return None

    def is_valid_package(self, filename: str, include_prerelease: bool = False) -> bool:
        """
        Check if a filename matches the expected package pattern.
        Optionally filter out pre-release versions.
        """
        version = self.extract_version(filename)
        if not version:
            return False
        if not include_prerelease and getattr(version, "is_prerelease", False):
            return False
        return filename.startswith(self._app_name) and filename.endswith(".zip")

    def scan(self, repo_path: str = "", include_prerelease: bool = False, fetch_checksum: bool = False) -> Dict[Version, Package]:
        """
        Scan the Artifactory repo and return a dict of Version -> Package.
        """
        self._packages = {}
        repo_path = self._normalize_segment(repo_path)
        storage_url = self._build_url("api", "storage", self._repo, repo_path)
        try:
            response = self._request(storage_url)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            self.log(f"Failed to query Artifactory: {e}", exception=True)
            return {}

        for child in data.get("children", []):
            if not child["uri"].endswith(".zip"):
                continue

            filename = child["uri"].lstrip("/")
            if not self.is_valid_package(filename, include_prerelease=include_prerelease):
                continue

            version = self.extract_version(filename)
            if not version:
                continue

            checksum = None
            if fetch_checksum:
                file_url = self._build_url("api", "storage", self._repo, repo_path, filename)
                try:
                    file_resp = self._request(file_url)
                    file_resp.raise_for_status()
                    file_data = file_resp.json()
                    checksum = file_data.get("checksums", {}).get("sha256")
                except Exception as e:
                    self.log(f"Failed to get checksum for {filename}: {e}")

            download_url = self._build_url(self._repo, repo_path, filename)
            self._packages[version] = Package(
                name=self._app_name,
                version=version,
                path=download_url,
                checksum=checksum
            )
        self.log(f"Found {len(self._packages)} package(s) for '{self._app_name}' in repo '{self._repo}/{repo_path}'")
        return self._packages

    @property
    def all_versions(self) -> List[Version]:
        """Return all versions sorted according to semantic versioning."""
        return sorted(self._packages.keys())

    @property
    def packages(self) -> Dict[Version, Package]:
        """Return all found packages as a version-to-package dictionary."""
        return self._packages

    @property
    def latest(self) -> Optional[Package]:
        """Return the latest package (by version) found in the scan, or None if none found."""
        if not self._packages:
            return None
        return self._packages[max(self._packages.keys())]

    @property
    def oldest(self) -> Optional[Package]:
        """Return the oldest package (by version) found in the scan, or None if none found."""
        if not self._packages:
            return None
        return self._packages[min(self._packages.keys())]

    def find(self, version: Version) -> Optional[Package]:
        """Return the package for a specific version, or None if not found."""
        return self._packages.get(version)

    def filter_by_range(self, min_version: Version, max_version: Version, include_prerelease: bool = False) -> Dict[Version, Package]:
        """Return packages within a version range, optionally including pre-releases."""
        return {
            v: p for v, p in self._packages.items()
            if min_version <= v <= max_version and (include_prerelease or not v.is_prerelease)
        }