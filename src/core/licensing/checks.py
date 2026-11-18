"""License checks: configured in the Lab Mango web app, fetched by the agent, run read-only.

A check says *how* to read licenses (a probe), *how* to turn the output into licenses (an
extraction mapping) and *what holds them* (the carrier). The agent supports a closed catalog of
probe types; a check can never make the agent run something outside that catalog or outside the
local safety rules in :mod:`probes`.

Wire shape (``GET /agent/license-checks``, one item)::

    {
      "key": "vector-license-client", "revision": 3, "name": "Vector License Client",
      "vendor": "Vector", "interval_minutes": 360,
      "probe": {"type": "command", "executable": "C:\\\\Program Files\\\\…\\\\Vector.LicenseClient.exe",
                "args": ["-listlicenses"], "timeout_s": 20, "encoding": "auto"},
      "extract": {"format": "xml", "records": ".//VectorLicense",
                  "fields": {"product_name": "ProductText", "expires_at": "ExpirationDateString", …},
                  "date_formats": ["iso"], "never_values": ["9999-12-31"]},
      "carrier": {"type": "device", "hardware_id_kind": "vector_device"}
    }
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .models import CarrierType

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


class ProbeType:
    COMMAND = "command"  # run an installed tool with fixed arguments; read stdout
    FILE = "file"  # read a license or status file
    REGISTRY = "registry"  # read values under one HKLM key (Windows)

    ALL = (COMMAND, FILE, REGISTRY)


class ExtractFormat:
    XML = "xml"  # records: ElementTree path (".//VectorLicense"); fields: child paths
    JSON = "json"  # records: dotted path with [*] ("licenses[*]"); fields: dotted paths
    TEXT = "text"  # records: regex with named groups, one match per license; fields: group names
    VALUES = "values"  # registry: one record of the read values; fields: value names

    ALL = (XML, JSON, TEXT, VALUES)


# Observation fields a mapping may fill. ``product_name`` is required.
TARGET_FIELDS = (
    "product_name",
    "product_code",
    "max_version",
    "expires_at",
    "final_expires_at",
    "carrier_id",
    "license_serial",  # the license's serial / ID: the backend matches it to License.serial_number
    "is_reactivatable",  # "true"/"yes"/"1" -> the user can renew it themselves (warning text)
    "carrier_type",  # with carrier type "mapped": the tool's own value, translated by carrier.type_map
)

MAPPED_CARRIER = "mapped"  # carrier type taken per license from the "carrier_type" field

MAX_ARGS = 16
MAX_ARG_LENGTH = 256
MAX_TIMEOUT_S = 60
MIN_INTERVAL_MINUTES = 15


class InvalidCheck(ValueError):
    """The configuration is not a valid check; the agent reports it as ``rejected``."""


@dataclass(frozen=True)
class Probe:
    type: str
    executable: str = ""
    args: tuple[str, ...] = ()
    path: str = ""
    hive: str = ""
    key: str = ""
    values: tuple[str, ...] = ()
    timeout_s: int = 20
    encoding: str = "auto"  # "auto" honours an XML declaration (incl. "Codepage - 437"), else UTF-8


@dataclass(frozen=True)
class Extract:
    format: str
    records: str
    fields: dict[str, str]
    date_formats: tuple[str, ...] = ("iso",)
    never_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class Carrier:
    type: str  # a CarrierType, or "mapped"
    hardware_id_kind: str = ""  # for device / dongle: the kind of ``carrier_id``
    equipment_uid: str = ""  # for equipment: the unit chosen in the web app
    type_map: dict = field(default_factory=dict)  # for "mapped": tool value (upper case) -> CarrierType
    default_type: str = CarrierType.COMPUTER  # for "mapped": when the value is not in type_map

    def resolve(self, value: str) -> str:
        if self.type != MAPPED_CARRIER:
            return self.type
        return self.type_map.get((value or "").strip().upper(), self.default_type)


@dataclass(frozen=True)
class LicenseCheck:
    key: str
    revision: int
    name: str
    vendor: str
    probe: Probe
    extract: Extract
    carrier: Carrier
    interval_minutes: int = 360
    extra: dict = field(default_factory=dict, compare=False, repr=False)


def _str(data: dict, name: str, default: str = "", *, required: bool = False, limit: int = 512) -> str:
    value = data.get(name, default)
    if value is None:
        value = default
    if not isinstance(value, str) or len(value) > limit:
        raise InvalidCheck(f"'{name}' must be a string of at most {limit} characters")
    if required and not value.strip():
        raise InvalidCheck(f"'{name}' is required")
    return value.strip()


def _str_list(data: dict, name: str, *, limit: int, item_limit: int) -> tuple[str, ...]:
    value = data.get(name) or []
    if not isinstance(value, list) or len(value) > limit:
        raise InvalidCheck(f"'{name}' must be a list of at most {limit} items")
    items = []
    for item in value:
        if not isinstance(item, str) or len(item) > item_limit or "\x00" in item:
            raise InvalidCheck(f"'{name}' items must be strings of at most {item_limit} characters")
        items.append(item)
    return tuple(items)


def _probe(data: Any) -> Probe:
    if not isinstance(data, dict):
        raise InvalidCheck("'probe' must be an object")
    kind = _str(data, "type", required=True)
    if kind not in ProbeType.ALL:
        raise InvalidCheck(f"unsupported probe type '{kind}'")
    timeout = data.get("timeout_s", 20)
    if not isinstance(timeout, int) or not 1 <= timeout <= MAX_TIMEOUT_S:
        raise InvalidCheck(f"'timeout_s' must be 1..{MAX_TIMEOUT_S}")
    probe = Probe(
        type=kind,
        executable=_str(data, "executable"),
        args=_str_list(data, "args", limit=MAX_ARGS, item_limit=MAX_ARG_LENGTH),
        path=_str(data, "path"),
        hive=_str(data, "hive", "HKLM").upper(),
        key=_str(data, "key"),
        values=_str_list(data, "values", limit=32, item_limit=128),
        timeout_s=timeout,
        encoding=_str(data, "encoding", "auto", limit=32).lower(),
    )
    if kind == ProbeType.COMMAND and not probe.executable:
        raise InvalidCheck("a command probe needs 'executable'")
    if kind == ProbeType.FILE and not probe.path:
        raise InvalidCheck("a file probe needs 'path'")
    if kind == ProbeType.REGISTRY and (probe.hive != "HKLM" or not probe.key or not probe.values):
        raise InvalidCheck("a registry probe reads 'values' under one HKLM 'key'")
    return probe


def _extract(data: Any, probe: Probe) -> Extract:
    if not isinstance(data, dict):
        raise InvalidCheck("'extract' must be an object")
    fmt = _str(data, "format", required=True)
    if fmt not in ExtractFormat.ALL:
        raise InvalidCheck(f"unsupported extract format '{fmt}'")
    if (fmt == ExtractFormat.VALUES) != (probe.type == ProbeType.REGISTRY):
        raise InvalidCheck("format 'values' is used with, and only with, registry probes")
    fields_ = data.get("fields")
    if not isinstance(fields_, dict) or not fields_:
        raise InvalidCheck("'fields' must map observation fields to source fields")
    unknown = set(fields_) - set(TARGET_FIELDS)
    if unknown:
        raise InvalidCheck(f"unknown fields: {', '.join(sorted(unknown))}")
    if "product_name" not in fields_:
        raise InvalidCheck("'fields.product_name' is required")
    if any(not isinstance(v, str) or not v or len(v) > 256 for v in fields_.values()):
        raise InvalidCheck("field sources must be non-empty strings")
    records = _str(data, "records", required=fmt != ExtractFormat.VALUES, limit=1024)
    if fmt == ExtractFormat.TEXT:
        try:
            pattern = re.compile(records)
        except re.error as error:
            raise InvalidCheck(f"'records' is not a valid regular expression: {error}") from None
        missing = set(fields_.values()) - set(pattern.groupindex)
        if missing:
            raise InvalidCheck(f"regex has no named groups: {', '.join(sorted(missing))}")
    return Extract(
        format=fmt,
        records=records,
        fields=dict(fields_),
        date_formats=_str_list(data, "date_formats", limit=8, item_limit=64) or ("iso",),
        never_values=_str_list(data, "never_values", limit=16, item_limit=64),
    )


def _carrier(data: Any, extract: Extract) -> Carrier:
    if not isinstance(data, dict):
        raise InvalidCheck("'carrier' must be an object")
    kind = _str(data, "type", required=True)
    if kind not in (*CarrierType.ALL, MAPPED_CARRIER):
        raise InvalidCheck(f"unsupported carrier type '{kind}'")
    type_map = data.get("type_map") or {}
    if (
        not isinstance(type_map, dict)
        or len(type_map) > 16
        or any(not isinstance(k, str) or v not in CarrierType.ALL for k, v in type_map.items())
    ):
        raise InvalidCheck("'type_map' must map tool values to carrier types")
    default_type = _str(data, "default_type", CarrierType.COMPUTER, limit=16)
    if default_type not in CarrierType.ALL:
        raise InvalidCheck(f"unsupported default carrier type '{default_type}'")
    carrier = Carrier(
        kind,
        _str(data, "hardware_id_kind", limit=32),
        _str(data, "equipment_uid", limit=64),
        {k.strip().upper(): v for k, v in type_map.items()},
        default_type,
    )
    possible = set(carrier.type_map.values()) | {default_type} if kind == MAPPED_CARRIER else {kind}
    if kind == MAPPED_CARRIER and "carrier_type" not in extract.fields:
        raise InvalidCheck("a mapped carrier needs a 'carrier_type' field")
    if possible & {CarrierType.DEVICE, CarrierType.DONGLE}:
        if not carrier.hardware_id_kind or "carrier_id" not in extract.fields:
            raise InvalidCheck("device and dongle carriers need 'hardware_id_kind' and a 'carrier_id' field")
    if CarrierType.EQUIPMENT in possible and not carrier.equipment_uid:
        raise InvalidCheck("an equipment carrier needs 'equipment_uid'")
    return carrier


def parse_check(data: Any) -> LicenseCheck:
    if not isinstance(data, dict):
        raise InvalidCheck("a check must be an object")
    key = _str(data, "key", required=True, limit=32)
    if not KEY_PATTERN.match(key):
        raise InvalidCheck("'key' must be a lowercase slug of at most 32 characters")
    revision = data.get("revision", 1)
    interval = data.get("interval_minutes", 360)
    if not isinstance(revision, int) or revision < 1:
        raise InvalidCheck("'revision' must be a positive integer")
    if not isinstance(interval, int) or interval < MIN_INTERVAL_MINUTES:
        raise InvalidCheck(f"'interval_minutes' must be at least {MIN_INTERVAL_MINUTES}")
    probe = _probe(data.get("probe"))
    extract = _extract(data.get("extract"), probe)
    return LicenseCheck(
        key=key,
        revision=revision,
        name=_str(data, "name", key, limit=128),
        vendor=_str(data, "vendor", limit=128),
        probe=probe,
        extract=extract,
        carrier=_carrier(data.get("carrier"), extract),
        interval_minutes=interval,
    )


def parse_checks(items: Any) -> tuple[list[LicenseCheck], dict[str, str]]:
    """Valid checks, and ``{key or index: reason}`` for the rejected ones (reported back)."""
    checks: list[LicenseCheck] = []
    rejected: dict[str, str] = {}
    for index, item in enumerate(items if isinstance(items, list) else []):
        try:
            checks.append(parse_check(item))
        except InvalidCheck as error:
            key = item.get("key") if isinstance(item, dict) and isinstance(item.get("key"), str) else f"#{index}"
            rejected[key[:32]] = str(error)
    return checks, rejected


def check_by_key(checks: list[LicenseCheck], key: str) -> Optional[LicenseCheck]:
    return next((c for c in checks if c.key == key), None)
