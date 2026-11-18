"""Built-in check definitions.

The web app offers these as templates when an administrator adds a check; the agent also runs the
enabled ones on its own while the backend does not serve ``/agent/license-checks`` yet. A preset is
an ordinary check configuration: no vendor gets special code.
"""

from __future__ import annotations

VECTOR_LICENSE_CLIENT_EXE = r"C:\Program Files\Vector License Client\Vector.LicenseClient.exe"

# New Vector License Model, read with ``Vector.LicenseClient -listlicenses`` (Vector KB0021758).
# Covers licenses on Vector devices (BindingType DEVICE), Keyman dongles and the PC.
# ExpirationDateString is when the activation ends; FinalExpirationDateString 9999-12-31 = perpetual.
VECTOR_LICENSE_CLIENT = {
    "key": "vector-license-client",
    "revision": 1,
    "name": "Vector License Client",
    "vendor": "Vector",
    "interval_minutes": 360,
    "probe": {
        "type": "command",
        "executable": VECTOR_LICENSE_CLIENT_EXE,
        "args": ["-listlicenses"],
        "timeout_s": 20,
        "encoding": "auto",
    },
    "extract": {
        "format": "xml",
        "records": ".//VectorLicense",
        "fields": {
            "product_name": "ProductText",
            "product_code": "MaterialNumber",
            "max_version": "MaxVersion",
            "expires_at": "ExpirationDateString",
            "final_expires_at": "FinalExpirationDateString",
            "carrier_id": "DeviceName",
            "license_serial": "VectorLicenseId",
            "is_reactivatable": "IsReactivatable",
            "carrier_type": "BindingType",
        },
        "date_formats": ["iso"],
        "never_values": ["9999-12-31"],
    },
    # BindingType says what holds the license; DeviceName names the Vector device or Keyman.
    "carrier": {
        "type": "mapped",
        "type_map": {"DEVICE": "device", "DONGLE": "dongle", "PC": "computer"},
        "default_type": "computer",
        "hardware_id_kind": "vector_device",
    },
}

PRESETS = {VECTOR_LICENSE_CLIENT["key"]: VECTOR_LICENSE_CLIENT}


def preset_executables() -> set[str]:
    return {p["probe"]["executable"] for p in PRESETS.values() if p["probe"].get("executable")}
