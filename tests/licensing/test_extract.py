from datetime import datetime
from pathlib import Path

import pytest

from src.core.licensing import VECTOR_LICENSE_CLIENT, CarrierType, parse_check
from src.core.licensing.extract import ExtractError, parse_date, records_from_output, to_observations
from src.core.monitoring import HardwareId

FIXTURE = Path(__file__).parent / "fixtures" / "listlicenses_device_perpetual.xml"


def run(check_data, output):
    check = parse_check(check_data)
    return to_observations(records_from_output(output, check), check)


def test_vector_license_client_output_through_the_generic_engine():
    (lic,) = run(VECTOR_LICENSE_CLIENT, FIXTURE.read_bytes())
    assert lic.check_key == "vector-license-client" and lic.vendor == "Vector"
    assert (lic.product_name, lic.product_code, lic.max_version) == ("CANalyzer PRO", "55100", "15.0")
    assert lic.carrier_type == CarrierType.DEVICE
    assert lic.carrier_hardware_id == HardwareId("vector_device", "007113-585343")
    assert lic.expires_at == datetime(2027, 4, 9, 23, 59, 59)
    assert lic.final_expires_at is None and lic.is_reactivatable
    assert lic.license_serial == "55100045010"
    assert lic.observation_key == "vector-license-client:serial:55100045010"
    assert lic.describe() == "CANalyzer PRO v15.0 on 007113-585343 (device), serial 55100045010, until 2027-04-09"


def test_pc_bound_vector_license_has_the_computer_as_carrier():
    xml = (
        b'<?xml version="1.0" encoding="Codepage - 437"?><Containers><LicenseContainer><Licenses>'
        b"<VectorLicense><ProductText>CANoe</ProductText><MaterialNumber>1</MaterialNumber>"
        b"<BindingType>PC</BindingType><DeviceName>MY-PC</DeviceName>"  # no VectorLicenseId
        b"<ExpirationDateString>2026-12-31T23:59:59</ExpirationDateString></VectorLicense>"
        b"</Licenses></LicenseContainer></Containers>"
    )
    (lic,) = run(VECTOR_LICENSE_CLIENT, xml)
    assert lic.carrier_type == CarrierType.COMPUTER and lic.carrier_hardware_id is None
    assert lic.observation_key == "vector-license-client:computer:computer:1"


def test_json_tool_output():
    check = {
        "key": "tool-json",
        "vendor": "Acme",
        "probe": {"type": "command", "executable": r"C:\Program Files\Acme\lic.exe", "args": ["--json"]},
        "extract": {
            "format": "json",
            "records": "licenses[*]",
            "fields": {"product_name": "product.name", "expires_at": "expires", "carrier_id": "dongle.serial"},
            "date_formats": ["%Y-%m-%d"],
            "never_values": ["never"],
        },
        "carrier": {"type": "dongle", "hardware_id_kind": "vector_device"},
    }
    out = (
        b'{"licenses": [{"product": {"name": "Suite"}, "expires": "2027-01-31", "dongle": {"serial": "D-1"}},'
        b' {"product": {"name": "Viewer"}, "expires": "never", "dongle": {"serial": "D-1"}}]}'
    )
    suite, viewer = run(check, out)
    assert suite.expires_at == datetime(2027, 1, 31, 23, 59, 59)  # a date means the end of that day
    assert viewer.expires_at is None and viewer.carrier_hardware_id == HardwareId("vector_device", "D-1")


def test_text_output_with_regex_for_a_license_on_the_pc():
    check = {
        "key": "flex-file",
        "vendor": "Example",
        "probe": {"type": "file", "path": r"C:\ProgramData\Example\license.lic"},
        "extract": {
            "format": "text",
            "records": r"^INCREMENT\s+(?P<feature>\S+)\s+\S+\s+(?P<version>\S+)\s+(?P<expiry>\S+)",
            "fields": {"product_name": "feature", "max_version": "version", "expires_at": "expiry"},
            "date_formats": ["%d-%b-%Y"],
            "never_values": ["permanent"],
        },
        "carrier": {"type": "computer"},
    }
    text = b"INCREMENT toolA vendord 2.0 31-mar-2027 1 SIGN=X\nINCREMENT toolB vendord 1.0 permanent 1 SIGN=Y\n"
    a, b = run(check, text)
    assert (a.product_name, a.max_version, a.expires_at) == ("toolA", "2.0", datetime(2027, 3, 31, 23, 59, 59))
    assert b.expires_at is None and a.carrier_type == CarrierType.COMPUTER


def test_registry_values_on_configured_equipment():
    check = {
        "key": "reg",
        "vendor": "Example",
        "probe": {"type": "registry", "key": r"SOFTWARE\Example", "values": ["Product", "Expiry"]},
        "extract": {"format": "values", "fields": {"product_name": "Product", "expires_at": "Expiry"}},
        "carrier": {"type": "equipment", "equipment_uid": "eq-1"},
    }
    (lic,) = run(check, {"Product": "Analyzer", "Expiry": "2027-06-30"})
    assert lic.carrier_type == CarrierType.EQUIPMENT and lic.carrier_equipment_uid == "eq-1"
    assert run(check, {}) == []


def test_bad_output_and_dates_raise_extract_error():
    with pytest.raises(ExtractError):
        run(VECTOR_LICENSE_CLIENT, b"License service not running")
    with pytest.raises(ExtractError, match="unrecognised date"):
        parse_date("31/31/2027", ("iso",), ())
    assert parse_date("9999-12-31T23:59:59", ("iso",), ()) is None
