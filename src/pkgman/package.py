from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Package:
    """Immutable descriptor for a downloadable application package.

    Attributes:
        name:           Application name (e.g. ``'Pacman'``).
        version:        Semantic version string (e.g. ``'1.2.3'``).
        path:           Download URL or local file path.
        checksum:       Expected SHA-256 hex digest (optional).
        size_bytes:     Archive size in bytes (optional).
        download_token: Bearer token for authenticated downloads (optional).
    """
    name           : str
    version        : str
    path           : str
    checksum       : str | None = None
    size_bytes     : int | None = None
    download_token : str | None = None

    @property
    def fullname(self) -> str:
        """Filename component of :attr:`path`."""
        return os.path.basename(self.path)

    @property
    def is_remote(self) -> bool:
        """``True`` when :attr:`path` points to an HTTP(S) URL."""
        return self.path.startswith(("http://", "https://"))
