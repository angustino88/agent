"""Tool licenses found on this computer or on hardware connected to it. Vendor-neutral.

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

from .devices import HardwareId


class CarrierType:
    DEVICE = "device"  # a hardware interface (e.g. a Vector CANcase / VN device)
    DONGLE = "dongle"  # a license dongle (e.g. a Vector Keyman)
    COMPUTER = "computer"  # this computer
    OTHER = "other"


class LicenseState:
    VALID = "valid"
    EXPIRED = "expired"


@dataclass(frozen=True)
class LicenseObservation:
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

    def state(self, now: datetime) -> str:
        return LicenseState.EXPIRED if self.expires_at is not None and self.expires_at <= now else LicenseState.VALID

    def days_left(self, now: datetime) -> Optional[int]:
        if self.expires_at is None:
            return None
        return max(0, (self.expires_at - now).days)

    @property
    def carrier_label(self) -> str:
        return self.carrier_hardware_id.value if self.carrier_hardware_id else "this computer"

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
