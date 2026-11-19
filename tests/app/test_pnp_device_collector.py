from src.app.controller.monitoring.pnp_device_collector import PnpDeviceCollector
from src.core.agent_api.models import MonitoringPolicy
from src.core.monitoring import WatchList, pnp_device

CANCASE = r"USB\VID_1248&PID_1073\007113-585343"
SCOPE = r"USB\VID_0957&PID_1755\MY52130101"
MOUSE = r"HID\VID_046D&PID_C077\7&1&0&0000"
EXPECTED = [
    {"equipment_uid": "u-1", "name": "CANcase 3", "hardware_ids": [{"kind": "pnp_id", "value": CANCASE}]},
    {"equipment_uid": "u-2", "name": "Scope", "hardware_ids": [{"kind": "pnp_id", "value": SCOPE}]},
]


class Reporter:
    def __init__(self):
        self.reports = []

    def refresh_policy(self):
        return MonitoringPolicy("g", 200, 262144, 120, ("USB",), expected_devices=tuple(EXPECTED))

    def report(self, devices, force=False):
        self.reports.append(([d.pnp_id for d in devices], force))


class Scanner:
    def __init__(self, *ids):
        self.ids = list(ids)

    def __call__(self):
        devices = [pnp_device(pnp_id, pnp_id.split("\\")[-1]) for pnp_id in self.ids]
        return {d.observation_key: d for d in devices}


def collector(scanner):
    reporter, discovery = Reporter(), Reporter()
    return PnpDeviceCollector(reporter, discovery, scanner=scanner), reporter, discovery


def test_reports_only_watched_devices_loaded_from_the_policy():
    scanner = Scanner(CANCASE, MOUSE)
    c, reporter, _ = collector(scanner)
    c.collect_once()
    assert c.watch_list == WatchList.from_policy(EXPECTED)
    assert reporter.reports == [([CANCASE], False)]  # the mouse never leaves the computer


def test_changes_count_after_three_scans():
    scanner = Scanner(CANCASE)
    c, reporter, _ = collector(scanner)
    c.collect_once()
    scanner.ids = [CANCASE, SCOPE]
    c.collect_once()
    c.collect_once()
    assert [d.pnp_id for d in c.watched_devices] == [CANCASE]
    c.collect_once()
    assert {d.pnp_id for d in c.watched_devices} == {CANCASE, SCOPE}
    scanner.ids = [SCOPE]
    for _ in range(3):
        c.collect_once()
    assert [d.pnp_id for d in c.watched_devices] == [SCOPE]
    assert reporter.reports[-1] == ([SCOPE], False)


def test_discovery_sends_connected_usb_devices_once():
    scanner = Scanner(CANCASE, MOUSE, r"USB\VID_0403&PID_6001\NEWDEVICE")
    c, _, discovery = collector(scanner)
    c.request_discovery()
    c.collect_once()
    c.collect_once()
    # watched devices are already reported; discovery offers only the unregistered ones
    assert discovery.reports == [([r"USB\VID_0403&PID_6001\NEWDEVICE"], True)]


def test_a_new_watch_list_reseeds_without_a_false_disconnect():
    scanner = Scanner(CANCASE, SCOPE)
    c, reporter, _ = collector(scanner)
    c.set_watch_list(WatchList.from_policy(EXPECTED[:1]))
    c.collect_once()
    assert reporter.reports[-1] == ([CANCASE], False)
    c.set_watch_list(WatchList.from_policy(EXPECTED))
    c.collect_once()
    assert set(reporter.reports[-1][0]) == {CANCASE, SCOPE}
