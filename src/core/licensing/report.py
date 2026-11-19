"""Wire body of ``POST /agent/license-checks/{key}/actions/report`` (lab-mango `core/agents/api/license_checks.py`).

One body per run of one check. When ``status`` is ``ok`` the license list is complete for that
check and carrier set, so licenses it no longer lists are gone; for any other status the backend
keeps the previous licenses and only records the failed run.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .models import CheckResult, CheckStatus, LicenseObservation


def _iso(value: datetime | None) -> str | None:
    return value.astimezone().isoformat() if value else None


def license_body(lic: LicenseObservation) -> dict:
    carrier: dict = {"type": lic.carrier_type}
    if lic.carrier_hardware_id:
        carrier["hardware_id"] = lic.carrier_hardware_id.to_body()
    if lic.carrier_equipment_uid:
        carrier["equipment_uid"] = lic.carrier_equipment_uid
    body = {
        "observation_key": lic.observation_key,
        "vendor": lic.vendor[:128],
        "product_code": lic.product_code[:128],
        "product_name": lic.product_name[:255],
        "carrier": carrier,
        "expires_at": _iso(lic.expires_at),
        "final_expires_at": _iso(lic.final_expires_at),
        "max_version": lic.max_version[:64],
        "is_reactivatable": lic.is_reactivatable,
    }
    if lic.license_serial:
        body["license_serial"] = lic.license_serial[:128]
    return body


def result_body(result: CheckResult, sequence: int) -> dict:
    body = {
        "revision": result.revision,
        "sequence": sequence,
        "status": result.status,
        "started_at": result.started_at.astimezone().isoformat(),
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": result.duration_ms,
        "is_complete": result.status == CheckStatus.OK,
        "licenses": [license_body(lic) for lic in result.licenses] if result.status == CheckStatus.OK else [],
    }
    if result.error_code:
        body["error"] = {"code": result.error_code, "message": result.error_message}
    return body
