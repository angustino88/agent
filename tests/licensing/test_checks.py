import copy

import pytest

from src.core.licensing import VECTOR_LICENSE_CLIENT, InvalidCheck, parse_check, parse_checks


def vector(**changes):
    data = copy.deepcopy(VECTOR_LICENSE_CLIENT)
    for path, value in changes.items():
        target = data
        *parents, leaf = path.split("__")
        for part in parents:
            target = target[part]
        target[leaf] = value
    return data


def test_the_vector_preset_is_a_valid_check():
    check = parse_check(vector())
    assert check.probe.args == ("-listlicenses",) and check.extract.records == ".//VectorLicense"
    assert check.carrier.resolve("DEVICE") == "device" and check.carrier.resolve("PC") == "computer"
    assert check.carrier.resolve("SOMETHING_NEW") == "computer"


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"key": "Bad Key"}, "slug"),
        ({"probe__type": "powershell"}, "unsupported probe type"),
        ({"probe__timeout_s": 600}, "timeout_s"),
        ({"probe__args": ["x"] * 17}, "at most 16"),
        ({"extract__fields": {"expires_at": "X"}}, "product_name"),
        ({"extract__fields": {"product_name": "P", "password": "X"}}, "unknown fields"),
        ({"interval_minutes": 1}, "interval_minutes"),
        ({"carrier": {"type": "device"}}, "hardware_id_kind"),
        ({"carrier": {"type": "equipment"}}, "equipment_uid"),
    ],
)
def test_invalid_configurations_are_rejected(changes, message):
    with pytest.raises(InvalidCheck, match=message):
        parse_check(vector(**changes))


def test_text_regex_must_name_every_mapped_group():
    data = vector(
        extract={
            "format": "text",
            "records": r"(?P<feature>\w+)",
            "fields": {"product_name": "feature", "expires_at": "exp"},
        }
    )
    with pytest.raises(InvalidCheck, match="named groups: exp"):
        parse_check(data)


def test_parse_checks_keeps_valid_ones_and_reports_the_rest():
    checks, rejected = parse_checks([vector(), vector(key="other", probe__type="shell"), "junk"])
    assert [c.key for c in checks] == ["vector-license-client"]
    assert set(rejected) == {"other", "#2"}
