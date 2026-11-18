"""Package manager — public API for update checking, downloading, and installing."""

from .checker import UpdateChecker, UpdateResult
from .installer import (
    PackageInstaller,
    PackageInstallError,
    PackageDownloadError,
    PackageChecksumError,
    PackageCancelledError,
)
from .logprint import LogPrintMixin
from .package import Package
from .scanner import PackageScanner
from .updater import PackageUpdater, UpdateStage
from .version import Version, InvalidVersion

__all__ = [
    # Core data
    "Package", "Version", "InvalidVersion",
    # Update checking
    "UpdateChecker", "UpdateResult",
    # Scanning
    "PackageScanner",
    # Download & install
    "PackageInstaller",
    "PackageInstallError", "PackageDownloadError",
    "PackageChecksumError", "PackageCancelledError",
    # Update orchestration
    "PackageUpdater", "UpdateStage",
    # Mixin
    "LogPrintMixin",
]
