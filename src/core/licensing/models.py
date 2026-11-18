"""Licenses found on this computer or on hardware connected to it, and the outcome of a check. Vendor-neutral.

A license usually has two dates:

* ``expires_at``: when the license stops working unless it is renewed or reactivated (for a
  reactivatable Vector license this is the end of the current activation period);
* ``final_expires_at``: the end of the license itself; ``None`` for a perpetual license.

Warnings and the backend's ``License.expiry_date`` follow ``expires_at``: that is the date the
user loses the tool.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional

from ..monitoring.devices import HardwareId


class CarrierType:
    """What holds the license."""

    COMPUTER = "computer"  # this computer (node-locked, license file, activation on the PC)
    DEVICE = "device"  # hardware mounted to the PC (e.g. a Vector CANcase); identified by a hardware ID
    DONGLE = "dongle"  # a license dongle (e.g. Vector Keyman, CodeMeter stick)
    SERVER = "server"  # a floating license on a license server, seen from this PC
    EQUIPMENT = "equipment"  # a unit named in the check configuration (tool reports no hardware ID)

    ALL = (COMPUTER, DEVICE, DONGLE, SERVER, EQUIPMENT)


class LicenseState:
    VALID = "valid"
    EXPIRED = "expired"


@dataclass(frozen=True)
class LicenseObservation:
    """One license as a check read it. ``check_key`` names the configured check that found it."""

    check_key: str
    observation_key: str
    vendor: str
    product_code: str
    product_name: str
    carrier_type: str
    carrier_hardware_id: Optional[HardwareId]  # None when the carrier is this computer
    expires_at: Optional[datetime]  # naive local time; None = does not expire
    final_expires_at: Optional[datetime]  # None = perpetual
    max_version: str = ""
    is_reactivatable: bool = False
    vendor_license_id: str = ""  # vendor's license ID; matches License.identifier. Never log it.
    carrier_equipment_uid: str = ""  # for CarrierType.EQUIPMENT: the unit configured on the check

    def state(self, now: datetime) -> str:
        return LicenseState.EXPIRED if self.expires_at is not None and self.expires_at <= now else LicenseState.VALID

    def days_left(self, now: datetime) -> Optional[int]:
        if self.expires_at is None:
            return None
        return max(0, (self.expires_at - now).days)

    @property
    def carrier_label(self) -> str:
        if self.carrier_hardware_id:
            return self.carrier_hardware_id.value
        return {CarrierType.SERVER: "license server", CarrierType.EQUIPMENT: "configured equipment"}.get(
            self.carrier_type, "this computer"
        )

    def describe(self) -> str:
        """Safe for logs and the UI (no license ID)."""
        until = f"{self.expires_at:%Y-%m-%d}" if self.expires_at else "no expiry"
        version = f" v{self.max_version}" if self.max_version else ""
        return f"{self.product_name}{version} on {self.carrier_label} ({self.carrier_type}), until {until}"


def expiring(licenses: Iterable[LicenseObservation], now: datetime, within_days: int) -> list[LicenseObservation]:
    """Licenses that expire within ``within_days`` days (already expired ones included), soonest first."""
    limit = now + timedelta(days=within_days)
    found = [lic for lic in licenses if lic.expires_at is not None and lic.expires_at <= limit]
    return sorted(found, key=lambda lic: lic.expires_at)


class CheckStatus:
    """Outcome of one run of a license check, reported to the backend and shown in the web app."""

    OK = "ok"  # ran; ``licenses`` is complete (may be empty)
    NOT_INSTALLED = "not_installed"  # the tool, file or registry key is not on this computer
    FAILED = "failed"  # ran but failed, timed out or produced unreadable output
    REJECTED = "rejected"  # the agent refused the configuration (safety rules, unknown type)


@dataclass(frozen=True)
class CheckResult:
    check_key: str
    revision: int
    status: str
    started_at: datetime
    duration_ms: int
    licenses: tuple = ()
    error_code: str = ""  # stable, e.g. "timeout", "exit_code", "parse_error", "path_not_allowed"
    error_message: str = ""  # short, never contains tool output

    @property
    def is_complete(self) -> bool:
        return self.status == CheckStatus.OK
