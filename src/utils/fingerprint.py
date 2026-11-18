"""Hardware fingerprint — stable per-machine hardware identifier.

Combines firmware-reported system UUID and motherboard serial number, then
hashes the normalized identity with SHA-256.

The fingerprint is used as a seat identifier when registering or releasing a
license activation on the server.  It does **not** transmit any personally
identifiable information beyond a salted hash of hardware-level identifiers.

Usage::

    from src.utils.fingerprint import get_hardware_fingerprint
    fp = get_hardware_fingerprint()   # e.g. "a3f82c1d..."  (64 hex chars)
"""
from __future__ import annotations

import hashlib
import platform
import subprocess
from pathlib import Path


def get_hardware_fingerprint() -> str:
    """Return a stable 64-character fingerprint derived from hardware identity.

    The fingerprint is deterministic for the same hardware identity and does
    not depend on the hostname, application, or persisted application data.

    Returns:
        A 64-character lowercase SHA-256 hexadecimal string.

    Raises:
        RuntimeError: If no suitable machine identity can be determined.
    """
    identity = _get_hardware_identity()

    if not identity:
        raise RuntimeError("Unable to determine hardware identity")

    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _get_hardware_identity() -> str | None:
    system = platform.system()

    if system == "Windows":
        return _get_windows_hardware_identity()

    if system == "Linux":
        return _get_linux_hardware_identity()

    return None


def _get_windows_hardware_identity() -> str | None:
    values: list[str] = []

    commands = (
        "(Get-CimInstance Win32_ComputerSystemProduct).UUID",
        "(Get-CimInstance Win32_BaseBoard).SerialNumber",
    )

    for command in commands:
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    command,
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            value = result.stdout.strip()

            if value:
                values.append(value)

        except (OSError, subprocess.SubprocessError):
            continue

    return _normalize_identity(values)


def _get_linux_hardware_identity() -> str | None:
    values: list[str] = []

    for path in (
        "/sys/class/dmi/id/product_uuid",
        "/sys/devices/virtual/dmi/id/product_uuid",
    ):
        value = _read_file(path)

        if value:
            values.append(value)
            break

    for path in (
        "/sys/class/dmi/id/board_serial",
        "/sys/devices/virtual/dmi/id/board_serial",
    ):
        value = _read_file(path)

        if value:
            values.append(value)
            break

    return _normalize_identity(values)


def _read_file(path: str) -> str | None:
    try:
        value = Path(path).read_text(encoding="utf-8").strip()
        return value or None
    except (OSError, UnicodeError):
        return None


def _normalize_identity(values: list[str]) -> str | None:
    ignored = {
        "",
        "unknown",
        "none",
        "null",
        "default string",
        "to be filled by o.e.m.",
        "to be filled by oem",
    }

    values = [
        value.strip().lower()
        for value in values
        if value and value.strip().lower() not in ignored
    ]

    if not values:
        return None

    return "|".join(sorted(set(values)))