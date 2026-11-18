"""Service Gateway — typed response models.

These dataclasses carry the *parsed* payload returned by standard endpoints
so callers work with named fields instead of raw dicts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class LoginResult:
    """Tokens returned by a successful ``login`` call."""

    access_token: str
    refresh_token: Optional[str] = None


@dataclass(frozen=True)
class TokenRefreshResult:
    """Tokens returned by a successful ``refresh_token`` call."""

    access_token: str
    refresh_token: Optional[str] = None


@dataclass(frozen=True)
class PackageInfo:
    """Metadata for the latest available software package."""

    version: str
    url: Optional[str] = None
    checksum: Optional[str] = None
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PackageUpdateResult:
    """Result of a ``check_package_update`` call."""

    has_update: bool
    version: Optional[str] = None
    url: Optional[str] = None
    checksum: Optional[str] = None
    extra: dict = field(default_factory=dict)
