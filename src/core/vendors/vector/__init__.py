"""Vector Informatik tools: Vector License Client (New Vector License Model)."""

from .license_client import (
    DEFAULT_EXECUTABLE,
    LicenseClientError,
    VectorLicense,
    find_executable,
    list_licenses,
    parse_license_list,
)

__all__ = [
    "DEFAULT_EXECUTABLE",
    "LicenseClientError",
    "VectorLicense",
    "find_executable",
    "list_licenses",
    "parse_license_list",
]
