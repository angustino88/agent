from __future__ import annotations
from functools import total_ordering
from packaging.version import Version as _PkgVersion, InvalidVersion


@total_ordering
class Version:
    """Semantic version wrapper (``major.minor.patch[-prerelease]``).

    Wraps :class:`packaging.version.Version` and enforces a strict
    three-part base (``X.Y.Z``).  Pre-release suffixes (e.g. ``-beta``,
    ``-rc1``) are supported.

    Raises:
        InvalidVersion: If the string does not match ``X.Y.Z[-pre]``.
    """

    __slots__ = ("_version_str", "_parsed", "_parts")

    def __init__(self, vstring: str) -> None:
        self._version_str = str(vstring).strip()
        base = self._version_str.split('-', 1)[0]
        parts = base.split('.')
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise InvalidVersion(f"Invalid version: {vstring}. Expected major.minor.patch")
        self._parts  = tuple(int(p) for p in parts)
        self._parsed = _PkgVersion(self._version_str)

    # ---- component accessors ------------------------------------------------

    @property
    def major(self) -> int:
        return self._parts[0]

    @property
    def minor(self) -> int:
        return self._parts[1]

    @property
    def patch(self) -> int:
        return self._parts[2]

    @property
    def is_prerelease(self) -> bool:
        return self._parsed.is_prerelease

    # ---- comparison (total_ordering fills the rest) -------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._parsed == other._parsed

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._parsed < other._parsed

    def __hash__(self) -> int:
        return hash(self._parsed)

    # ---- display ------------------------------------------------------------

    def __str__(self) -> str:
        return self._version_str

    def __repr__(self) -> str:
        return f"Version('{self._version_str}')"


__all__ = ["Version", "InvalidVersion"]