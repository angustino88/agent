from src.core.monitoring import HardwareId, WatchList, pnp_device

POLICY = [
    {
        "equipment_uid": "u-1",
        "name": "CANcase 3",
        "hardware_ids": [
            {"kind": "pnp_id", "value": "usb/vid_1248&pid_1073/007113-585343"},
            {"kind": "vector_device", "value": "007113-585343"},
        ],
    },
    {"equipment_uid": "u-2", "name": "New scope", "hardware_ids": []},
]


def test_only_devices_on_the_watch_list_are_selected():
    watch = WatchList.from_policy(POLICY)
    cancase = pnp_device(r"USB\VID_1248&PID_1073\007113-585343", "VN1630A")
    mouse = pnp_device(r"HID\VID_046D&PID_C077\7&1", "Mouse")
    assert watch.select([cancase, mouse]) == [cancase]
    assert watch.match(cancase).name == "CANcase 3" and watch.match(mouse) is None


def test_expected_units_without_an_id_are_reported_as_unregistered():
    watch = WatchList.from_policy(POLICY)
    assert [d.name for d in watch.unregistered] == ["New scope"]
    assert HardwareId("vector_device", "007113-585343") in watch.expected[0].hardware_ids


def test_watch_lists_compare_by_content():
    assert WatchList.from_policy(POLICY) == WatchList.from_policy(POLICY)
    assert WatchList.from_policy(POLICY) != WatchList.from_policy(POLICY[:1])
    assert WatchList.from_policy(None).expected == ()
