from datetime import datetime

from src.app.controller.monitoring.license_collector import LicenseCollector, warning_text
from src.core.monitoring import CarrierType, HardwareId, LicenseObservation
from src.core.vendors.vector import LicenseClientError


def lic(key="vector:device:007113-585343:55100", expires=datetime(2027, 4, 9, 23, 59, 59)):
    return LicenseObservation(
        observation_key=key,
        vendor="Vector",
        product_code="55100",
        product_name="CANalyzer PRO",
        carrier_type=CarrierType.DEVICE,
        carrier_hardware_id=HardwareId("vector_device", "007113-585343"),
        expires_at=expires,
        final_expires_at=None,
        max_version="15.0",
        is_reactivatable=True,
    )


class Log:
    def __init__(self):
        self.lines = []

    def info(self, message):
        self.lines.append(message)


def test_warns_once_a_day_inside_the_window():
    collector = LicenseCollector({"vector": lambda: [lic()]}, warn_days=30)
    collector.collect()
    assert collector.due_warnings(datetime(2027, 3, 1)) == []  # 39 days left
    assert collector.due_warnings(datetime(2027, 3, 15, 9)) == [lic()]
    assert collector.due_warnings(datetime(2027, 3, 15, 15)) == []  # already warned today
    assert collector.due_warnings(datetime(2027, 3, 16, 9)) == [lic()]


def test_failing_source_is_logged_once_and_drops_its_licenses():
    state = {"fail": False}

    def source():
        if state["fail"]:
            raise LicenseClientError("Vector License Client is not installed")
        return [lic()]

    log = Log()
    collector = LicenseCollector({"Vector License Client": source}, logger=log)
    assert collector.collect() == [lic()]
    state["fail"] = True
    assert collector.collect() == [] and collector.collect() == []
    assert log.lines == ["[Licenses] Vector License Client: Vector License Client is not installed"]


def test_warning_text_tells_the_user_what_to_do():
    text = warning_text(lic(), datetime(2027, 3, 30, 12))
    assert text == (
        "CANalyzer PRO on 007113-585343 expires in 10 days (09 Apr 2027). Reactivate it in the Vector License Client."
    )
    assert "has expired" in warning_text(lic(), datetime(2027, 4, 10))
