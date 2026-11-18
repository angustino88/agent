import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from src.core.monitoring import CarrierType, HardwareId, LicenseState, expiring
from src.core.vendors.vector import license_client
from src.core.vendors.vector import LicenseClientError, parse_license_list

FIXTURES = Path(__file__).parent / "fixtures"


def sample() -> bytes:
    return (FIXTURES / "listlicenses_device_perpetual.xml").read_bytes()


def test_parses_the_license_client_sample_despite_its_codepage_declaration():
    (lic,) = parse_license_list(sample())
    assert lic.product_text == "CANalyzer PRO" and lic.material_number == "55100"
    assert lic.max_version == "15.0" and lic.device_name == "007113-585343"
    assert lic.carrier_type == CarrierType.DEVICE and lic.license_type == "Device_Locked"
    assert lic.expires_at == datetime(2027, 4, 9, 23, 59, 59)
    assert lic.final_expires_at is None  # 9999-12-31 = perpetual
    assert lic.is_perpetual and lic.is_reactivatable and lic.reactivation_period_months == 12
    assert "55100045010" not in repr(lic)  # license id never in logs


def test_observation_uses_the_device_as_carrier_and_activation_end_as_expiry():
    obs = parse_license_list(sample())[0].to_observation()
    assert obs.carrier_hardware_id == HardwareId("vector_device", "007113-585343")
    assert obs.observation_key == "vector:device:007113-585343:55100"
    assert obs.vendor_license_id == "55100045010"
    assert obs.state(datetime(2027, 1, 1)) == LicenseState.VALID
    assert obs.state(datetime(2027, 4, 10)) == LicenseState.EXPIRED
    assert obs.days_left(datetime(2027, 3, 10)) == 30
    assert "55100045010" not in obs.describe()
    assert obs.describe() == "CANalyzer PRO v15.0 on 007113-585343 (device), until 2027-04-09"


def test_expiring_lists_licenses_inside_the_window():
    obs = parse_license_list(sample())[0].to_observation()
    assert expiring([obs], datetime(2027, 3, 1), within_days=30) == []
    assert expiring([obs], datetime(2027, 3, 15), within_days=30) == [obs]


def test_computer_bound_and_unknown_fields_are_tolerated():
    xml = b"""<?xml version="1.0" encoding="utf-8"?>
<Containers><LicenseContainer><NewContainerField>x</NewContainerField><Licenses>
<VectorLicense><ProductText>CANoe</ProductText><MaterialNumber>1</MaterialNumber>
<BindingType>PC</BindingType><SomethingNew>1</SomethingNew></VectorLicense>
</Licenses></LicenseContainer></Containers>"""
    (lic,) = parse_license_list(xml)
    obs = lic.to_observation()
    assert obs.carrier_type == CarrierType.COMPUTER and obs.carrier_hardware_id is None
    assert obs.expires_at is None and obs.observation_key == "vector:computer:computer:1"


def test_empty_list_and_garbage():
    assert parse_license_list(b'<?xml version="1.0" encoding="Codepage - 437"?><Containers />') == []
    with pytest.raises(LicenseClientError):
        parse_license_list(b"Error: license service not running")
    with pytest.raises(LicenseClientError):
        parse_license_list(b"<Other/>")


def test_list_licenses_runs_the_client_read_only(monkeypatch, tmp_path):
    exe = tmp_path / "Vector.LicenseClient.exe"
    exe.write_text("")
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout=sample(), stderr=b"")

    monkeypatch.setattr(license_client.subprocess, "run", fake_run)
    licenses = license_client.list_licenses(str(exe))
    assert calls == [[str(exe), "-listlicenses"]] and len(licenses) == 1


def test_missing_client_and_failures_are_reported(monkeypatch, tmp_path):
    monkeypatch.setattr(license_client, "DEFAULT_EXECUTABLE", str(tmp_path / "missing.exe"))
    with pytest.raises(LicenseClientError, match="not installed"):
        license_client.list_licenses("")
    exe = tmp_path / "client.exe"
    exe.write_text("")
    monkeypatch.setattr(
        license_client.subprocess, "run", lambda args, **k: subprocess.CompletedProcess(args, 3, b"", b"")
    )
    with pytest.raises(LicenseClientError, match="code 3"):
        license_client.list_licenses(str(exe))
