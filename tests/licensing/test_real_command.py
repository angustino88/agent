"""Runs a real process through the probe: safety check, no shell, output parsed by the Vector preset."""

import copy
import os
import stat
import sys
from pathlib import Path

import pytest

from src.core.licensing import VECTOR_LICENSE_CLIENT, CheckStatus, SafetyPolicy, parse_check, result_body, run_check

FIXTURE = Path(__file__).parent / "fixtures" / "listlicenses_device_perpetual.xml"


@pytest.mark.skipif(os.name == "nt", reason="stand-in tool is a POSIX script")
def test_stand_in_license_client_end_to_end(tmp_path):
    tool = tmp_path / "Vector.LicenseClient"
    tool.write_text(
        f"#!{sys.executable}\nimport sys\nassert sys.argv[1:] == ['-listlicenses']\n"
        f"sys.stdout.buffer.write(open({str(FIXTURE)!r}, 'rb').read())\n"
    )
    tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    data = copy.deepcopy(VECTOR_LICENSE_CLIENT)
    data["probe"]["executable"] = str(tool)
    check = parse_check(data)

    untrusted = run_check(check, SafetyPolicy(allowed_roots=(str(tmp_path),)))
    assert (untrusted.status, untrusted.error_code) == (CheckStatus.REJECTED, "untrusted_connection")

    result = run_check(check, SafetyPolicy(allowed_roots=(str(tmp_path),), allow_configured_paths=True))
    assert result.status == CheckStatus.OK, result.error_message
    (lic,) = result.licenses
    assert lic.product_name == "CANalyzer PRO"
    body = result_body(result, sequence=1)
    assert body["is_complete"] and body["licenses"][0]["carrier"] == {
        "type": "device",
        "hardware_id": {"kind": "vector_device", "value": "007113-585343"},
    }
    assert body["licenses"][0]["license_serial"] == "55100045010"
