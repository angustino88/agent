from src.core.monitoring import (
    HardwareId,
    enumerator,
    is_discoverable,
    is_port_bound,
    normalize_hardware_id,
    pick_interface_name,
    pnp_device,
)

CANCASE = r"USB\VID_1248&PID_1073\007113-585343"


def test_pnp_ids_are_normalised_like_the_backend():
    assert normalize_hardware_id("pnp_id", " usb/vid_1248&pid_1073/007113-585343 ") == CANCASE
    assert HardwareId.pnp("usb\\vid_1248&pid_1073\\007113-585343") == HardwareId("pnp_id", CANCASE)


def test_port_bound_ids_are_recognised():
    assert not is_port_bound(CANCASE)
    assert is_port_bound(r"USB\VID_046D&PID_C52B\5&2A3C0F1&0&2")


def test_a_pnp_entity_becomes_an_observation_with_its_hardware_id():
    device = pnp_device(CANCASE.lower(), "Vector VN1630A")
    assert device.observation_key == f"pnp:{CANCASE}"
    assert device.interface_name == "USB" and device.name == "Vector VN1630A"
    assert device.pnp_id == CANCASE
    assert device.to_body() == {
        "observation_key": f"pnp:{CANCASE}",
        "interface_name": "USB",
        "name": "Vector VN1630A",
        "state": "connected",
        "hardware_ids": [{"kind": "pnp_id", "value": CANCASE}],
    }
    assert pnp_device("", "No id") is None and pnp_device("ROOT", "No path") is None


def test_discovery_offers_usb_hardware_not_interfaces_or_system_devices():
    assert is_discoverable(pnp_device(CANCASE))
    assert is_discoverable(pnp_device(r"USBSTOR\DISK&VEN_SANDISK&PROD_ULTRA\4C530001"))
    assert not is_discoverable(pnp_device(r"USB\VID_046D&PID_C52B&MI_00\6&1B2C&0&0000"))
    assert not is_discoverable(pnp_device(r"PCI\VEN_8086&DEV_A370\3&11583659&0&A3"))
    assert enumerator(r"HID\VID_046D&PID_C52B\7&1") == "HID"


def test_interface_name_follows_backend_catalog_spelling():
    assert pick_interface_name(["Ethernet", "usb"], "USB") == "usb"
    assert pick_interface_name([], "USB") == "USB"
