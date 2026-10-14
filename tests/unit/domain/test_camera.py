import ipaddress

import pytest

from safevision.domain.errors import ValidationError
from safevision.domain.model.camera import Camera
from safevision.domain.model.values import CameraStatus


def make_camera(**overrides) -> Camera:
    data = {"name": "Sala", "ip_address": "192.0.2.10", "location_id": 1}
    return Camera(**(data | overrides))


def test_ip_text_is_parsed():
    camera = make_camera()
    assert camera.ip_address == ipaddress.IPv4Address("192.0.2.10")
    assert camera.status is CameraStatus.ACTIVE


def test_ipv6_and_address_objects_are_accepted():
    assert make_camera(ip_address=" 2001:db8::1 ").ip_address.version == 6
    address = ipaddress.ip_address("198.51.100.7")
    assert make_camera(ip_address=address).ip_address is address


@pytest.mark.parametrize("ip", ["", "999.1.1.1", "camera.local", None, "10.0.0"])
def test_invalid_ip_is_rejected(ip):
    with pytest.raises(ValidationError):
        make_camera(ip_address=ip)


def test_status_text_is_parsed_and_validated():
    assert make_camera(status="maintenance").status is CameraStatus.MAINTENANCE
    with pytest.raises(ValidationError):
        make_camera(status="broken")


def test_change_status():
    camera = make_camera()
    camera.change_status("disconnected")
    assert camera.status is CameraStatus.DISCONNECTED
    with pytest.raises(ValidationError):
        camera.change_status("off")
    assert camera.status is CameraStatus.DISCONNECTED


def test_location_is_required():
    with pytest.raises(ValidationError):
        make_camera(location_id=None)
