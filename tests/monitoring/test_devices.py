from src.core.monitoring import parse_usb_instance_id, pick_interface_name, usb_device


def test_usb_serial_is_the_last_segment():
    instance = parse_usb_instance_id(r"USB\VID_0403&PID_6001\A12BC3")
    assert (instance.vendor_id, instance.product_id, instance.serial_number) == ("0403", "6001", "A12BC3")
    assert not instance.is_interface


def test_windows_generated_instance_ids_are_not_serials():
    assert parse_usb_instance_id(r"USB\VID_046D&PID_C52B\5&2A3C0F1&0&2").serial_number == ""


def test_composite_interfaces_and_non_usb_ids_are_skipped():
    assert usb_device(r"USB\VID_046D&PID_C52B&MI_00\6&1B2C&0&0000", "Receiver") is None
    assert usb_device(r"PCI\VEN_8086&DEV_A370\3&11583659&0&A3", "Controller") is None


def test_observation_key_is_stable_and_name_has_a_fallback():
    device = usb_device(r"USB\VID_0403&PID_6001\A12BC3", "")
    assert device.observation_key == r"usb:usb\vid_0403&pid_6001\a12bc3"
    assert device.name == "USB 0403:6001" and device.serial_number == "A12BC3"
    assert device.to_body()["state"] == "connected"


def test_interface_name_follows_backend_catalog_spelling():
    assert pick_interface_name(["Ethernet", "usb"]) == "usb"
    assert pick_interface_name([]) == "USB"
