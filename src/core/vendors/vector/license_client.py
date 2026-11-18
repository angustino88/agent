r"""Read licenses of the New Vector License Model with the Vector License Client.

``Vector.LicenseClient -listlicenses`` prints XML (Vector KB0021758)::

    <Containers>
      <LicenseContainer>
        <Licenses>
          <VectorLicense>
            <DeviceName>007113-585343</DeviceName>          carrier of a DEVICE-bound license
            <ProductText>CANalyzer PRO</ProductText>
            <MaterialNumber>55100</MaterialNumber>          Vector product (material) number
            <MaxVersion>15.0</MaxVersion>
            <ExpirationDateString>2027-04-09T23:59:59</ExpirationDateString>        activation ends
            <FinalExpirationDateString>9999-12-31T23:59:59</FinalExpirationDateString>  9999 = perpetual
            <IsReactivatable>true</IsReactivatable>  <ReactivationPeriod>12</ReactivationPeriod>
            <BindingType>DEVICE</BindingType>  <LicenseType>Device_Locked</LicenseType>
            <VectorLicenseId>…</VectorLicenseId>  <ContractId>…</ContractId>  <LicenseId>…</LicenseId>
            …

The declaration says ``encoding="Codepage - 437"``, which is not a valid XML encoding name, so the
bytes are decoded here and the declaration is dropped before parsing. Unknown elements are ignored
and missing ones are tolerated, so new License Client versions keep working.

Contract and ticket identifiers are never kept; ``VectorLicenseId`` is kept only to match the
license in Lab Mango and must not be logged.
"""

from __future__ import annotations

import os
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ...monitoring.devices import HardwareId, HardwareIdKind
from ...monitoring.licenses import CarrierType, LicenseObservation

DEFAULT_EXECUTABLE = r"C:\Program Files\Vector License Client\Vector.LicenseClient.exe"
LIST_LICENSES_ARGS = ("-listlicenses",)
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
_DECLARATION = re.compile(rb"^\s*<\?xml[^>]*\?>", re.IGNORECASE)
_CODEPAGE = re.compile(rb'encoding="\s*codepage\s*-\s*(\d+)\s*"', re.IGNORECASE)
_PERPETUAL_YEAR = 9999

_CARRIERS = {
    "DEVICE": CarrierType.DEVICE,
    "DONGLE": CarrierType.DONGLE,
    "PC": CarrierType.COMPUTER,
    "COMPUTER": CarrierType.COMPUTER,
}


class LicenseClientError(RuntimeError):
    """The License Client is missing, failed, timed out or printed something unreadable."""


@dataclass(frozen=True)
class VectorLicense:
    product_text: str
    material_number: str
    max_version: str
    device_name: str
    binding_type: str
    license_type: str
    license_restriction: str
    expires_at: Optional[datetime]
    final_expires_at: Optional[datetime]
    is_perpetual: bool
    is_reactivatable: bool
    reactivation_period_months: Optional[int]
    quantity: Optional[int]
    vector_license_id: str = field(repr=False, default="")

    @property
    def carrier_type(self) -> str:
        return _CARRIERS.get(self.binding_type.upper(), CarrierType.OTHER)

    def to_observation(self) -> LicenseObservation:
        carrier = self.carrier_type
        hardware_id = (
            HardwareId(HardwareIdKind.VECTOR_DEVICE, self.device_name)
            if carrier in (CarrierType.DEVICE, CarrierType.DONGLE) and self.device_name
            else None
        )
        carrier_key = hardware_id.value if hardware_id else "computer"
        return LicenseObservation(
            observation_key=f"vector:{carrier}:{carrier_key}:{self.material_number or self.product_text}",
            vendor="Vector",
            product_code=self.material_number,
            product_name=self.product_text,
            carrier_type=carrier,
            carrier_hardware_id=hardware_id,
            expires_at=self.expires_at,
            final_expires_at=self.final_expires_at,
            max_version=self.max_version,
            is_reactivatable=self.is_reactivatable,
            vendor_license_id=self.vector_license_id,
        )


# ---------------------------------------------------------------------- parsing


def _decode(raw: bytes) -> str:
    match = _CODEPAGE.search(raw[:200])
    encoding = f"cp{match.group(1).decode()}" if match else "utf-8"
    try:
        text = raw.decode(encoding)
    except (LookupError, UnicodeDecodeError):
        text = raw.decode("utf-8", errors="replace")
    return _DECLARATION.sub(b"", text.lstrip("\ufeff").encode("utf-8"), count=1).decode("utf-8")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(node: ET.Element, name: str) -> str:
    for child in node:
        if _local(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _bool(value: str) -> bool:
    return value.strip().lower() == "true"


def _int(value: str) -> Optional[int]:
    try:
        return int(value)
    except ValueError:
        return None


def _datetime(value: str) -> Optional[datetime]:
    """License Client times are local wall-clock time without an offset; year 9999 means never."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return None if parsed.year >= _PERPETUAL_YEAR else parsed.replace(tzinfo=None)


def parse_license_list(raw: bytes) -> list[VectorLicense]:
    """Parse ``-listlicenses`` output. Raises :class:`LicenseClientError` when it is not that XML."""
    try:
        root = ET.fromstring(_decode(raw))
    except ET.ParseError as error:
        raise LicenseClientError(f"License Client output is not valid XML: {error}") from None
    if _local(root.tag) != "Containers":
        raise LicenseClientError(f"Unexpected License Client output root <{_local(root.tag)}>")
    licenses = []
    for node in root.iter():
        if _local(node.tag) != "VectorLicense":
            continue
        licenses.append(
            VectorLicense(
                product_text=_text(node, "ProductText"),
                material_number=_text(node, "MaterialNumber"),
                max_version=_text(node, "MaxVersion"),
                device_name=_text(node, "DeviceName"),
                binding_type=_text(node, "BindingType"),
                license_type=_text(node, "LicenseType"),
                license_restriction=_text(node, "LicenseRestriction"),
                expires_at=_datetime(_text(node, "ExpirationDateString")),
                final_expires_at=_datetime(_text(node, "FinalExpirationDateString")),
                is_perpetual=_bool(_text(node, "IsPerpetual")),
                is_reactivatable=_bool(_text(node, "IsReactivatable")),
                reactivation_period_months=_int(_text(node, "ReactivationPeriod")),
                quantity=_int(_text(node, "Quantity")),
                vector_license_id=_text(node, "VectorLicenseId"),
            )
        )
    return licenses


# ---------------------------------------------------------------------- running the client


def find_executable(configured: str = "") -> Optional[str]:
    for candidate in (configured, DEFAULT_EXECUTABLE):
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def list_licenses(executable: str = "", timeout_s: float = 20.0) -> list[VectorLicense]:
    """Run the License Client and parse its license list. Read-only: lists, never activates."""
    path = find_executable(executable)
    if path is None:
        raise LicenseClientError("Vector License Client is not installed")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        completed = subprocess.run(
            [path, *LIST_LICENSES_ARGS],
            capture_output=True,
            timeout=timeout_s,
            creationflags=flags,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise LicenseClientError(f"Vector License Client failed: {type(error).__name__}") from None
    if completed.returncode != 0:
        raise LicenseClientError(f"Vector License Client exited with code {completed.returncode}")
    if len(completed.stdout) > MAX_OUTPUT_BYTES:
        raise LicenseClientError("Vector License Client output is too large")
    return parse_license_list(completed.stdout)
