"""Turn probe output into licenses with a declarative mapping (no code from the backend runs here)."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Optional

from ..monitoring.devices import HardwareId
from .checks import ExtractFormat, LicenseCheck
from .models import CarrierType, LicenseObservation

MAX_RECORDS = 500
_DECLARATION = re.compile(rb"^\s*<\?xml[^>]*\?>", re.IGNORECASE)
_DECLARED = re.compile(rb'encoding="\s*([^"]+?)\s*"', re.IGNORECASE)
_CODEPAGE = re.compile(r"^codepage\s*-?\s*(\d+)$", re.IGNORECASE)


class ExtractError(ValueError):
    """The output does not have the configured shape."""


# ---------------------------------------------------------------------- decoding


def decode(raw: bytes, encoding: str = "auto") -> str:
    """Bytes to text. ``auto``: the XML declaration's encoding (``Codepage - 437`` means cp437), else UTF-8."""
    if encoding == "auto":
        declared = _DECLARED.search(raw[:200])
        name = declared.group(1).decode("ascii", "replace") if declared else "utf-8"
        codepage = _CODEPAGE.match(name)
        encoding = f"cp{codepage.group(1)}" if codepage else name
    try:
        text = raw.decode(encoding)
    except (LookupError, UnicodeDecodeError):
        text = raw.decode("utf-8", errors="replace")
    return text.lstrip("﻿")


# ---------------------------------------------------------------------- records


def _strip_namespaces(root: ET.Element) -> ET.Element:
    for node in root.iter():
        if isinstance(node.tag, str) and "}" in node.tag:
            node.tag = node.tag.rsplit("}", 1)[1]
        for name in [n for n in node.attrib if "}" in n]:
            node.attrib[name.rsplit("}", 1)[1]] = node.attrib.pop(name)
    return root


def _xml_records(text: str, records: str, fields: dict[str, str]) -> list[dict[str, str]]:
    body = _DECLARATION.sub(b"", text.encode("utf-8"), count=1).decode("utf-8")
    try:
        root = _strip_namespaces(ET.fromstring(body))
    except ET.ParseError as error:
        raise ExtractError(f"not valid XML: {error}") from None
    try:
        nodes = root.findall(records) if records not in (".", "") else [root]
    except SyntaxError as error:
        raise ExtractError(f"invalid records path: {error}") from None
    return [{target: (node.findtext(source) or "").strip() for target, source in fields.items()} for node in nodes]


def _json_path(value: Any, path: str) -> list[Any]:
    current = [value]
    for part in [p for p in path.split(".") if p]:
        name, star = (part[:-3], True) if part.endswith("[*]") else (part, False)
        nxt = []
        for item in current:
            if name:
                item = item.get(name) if isinstance(item, dict) else None
            if star:
                nxt.extend(item if isinstance(item, list) else [])
            elif item is not None:
                nxt.append(item)
        current = nxt
    return current


def _json_records(text: str, records: str, fields: dict[str, str]) -> list[dict[str, str]]:
    try:
        data = json.loads(text)
    except ValueError as error:
        raise ExtractError(f"not valid JSON: {error}") from None
    rows = []
    for item in _json_path(data, records):
        row = {}
        for target, source in fields.items():
            found = _json_path(item, source)
            row[target] = "" if not found or found[0] is None else str(found[0]).strip()
        rows.append(row)
    return rows


def _text_records(text: str, records: str, fields: dict[str, str]) -> list[dict[str, str]]:
    pattern = re.compile(records, re.MULTILINE)
    return [
        {target: (match.group(source) or "").strip() for target, source in fields.items()}
        for match in pattern.finditer(text)
    ]


def records_from_output(output: Any, check: LicenseCheck) -> list[dict[str, str]]:
    """``output`` is bytes for command/file probes, a ``{name: value}`` dict for registry probes."""
    spec = check.extract
    if spec.format == ExtractFormat.VALUES:
        rows = [{t: str(output.get(s, "") or "").strip() for t, s in spec.fields.items()}] if output else []
    else:
        text = decode(output, check.probe.encoding)
        if spec.format == ExtractFormat.XML:
            rows = _xml_records(text, spec.records, spec.fields)
        elif spec.format == ExtractFormat.JSON:
            rows = _json_records(text, spec.records, spec.fields)
        else:
            rows = _text_records(text, spec.records, spec.fields)
    if len(rows) > MAX_RECORDS:
        raise ExtractError(f"more than {MAX_RECORDS} licenses")
    return [row for row in rows if row.get("product_name")]


# ---------------------------------------------------------------------- licenses


def parse_date(value: str, formats: tuple[str, ...], never_values: tuple[str, ...]) -> Optional[datetime]:
    """Naive local datetime; ``None`` for empty, "never" values and year 9999. Raises on a bad date."""
    value = (value or "").strip()
    if not value or any(value.lower().startswith(n.lower()) for n in never_values if n):
        return None
    for fmt in formats:
        try:
            parsed = datetime.fromisoformat(value) if fmt == "iso" else datetime.strptime(value, fmt)
        except ValueError:
            continue
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        if parsed.year >= 9999:
            return None
        if fmt != "iso" and "%H" not in fmt:
            parsed = parsed.replace(hour=23, minute=59, second=59)  # a date alone means the end of that day
        return parsed
    raise ExtractError(f"unrecognised date '{value[:40]}'")


def to_observations(rows: list[dict[str, str]], check: LicenseCheck) -> list[LicenseObservation]:
    spec, carrier = check.extract, check.carrier
    found: dict[str, LicenseObservation] = {}
    for row in rows:
        carrier_type = carrier.resolve(row.get("carrier_type", ""))
        carrier_id = row.get("carrier_id", "")
        hardware_id = None
        if carrier_type in (CarrierType.DEVICE, CarrierType.DONGLE):
            if not carrier_id:
                continue  # a device license whose device the tool did not name cannot be attributed
            hardware_id = HardwareId(carrier.hardware_id_kind, carrier_id)
        else:
            carrier_id = ""
        equipment_uid = carrier.equipment_uid if carrier_type == CarrierType.EQUIPMENT else ""
        product = row.get("product_code") or row["product_name"]
        carrier_key = carrier_id or equipment_uid or carrier_type
        key = f"{check.key}:{carrier_type}:{carrier_key}:{product}"[:255]
        found[key] = LicenseObservation(
            check_key=check.key,
            observation_key=key,
            vendor=check.vendor,
            product_code=row.get("product_code", ""),
            product_name=row["product_name"],
            carrier_type=carrier_type,
            carrier_hardware_id=hardware_id,
            expires_at=parse_date(row.get("expires_at", ""), spec.date_formats, spec.never_values),
            final_expires_at=parse_date(row.get("final_expires_at", ""), spec.date_formats, spec.never_values),
            max_version=row.get("max_version", ""),
            is_reactivatable=row.get("is_reactivatable", "").lower() in ("true", "yes", "1"),
            vendor_license_id=row.get("vendor_license_id", ""),
            carrier_equipment_uid=equipment_uid,
        )
    return list(found.values())
