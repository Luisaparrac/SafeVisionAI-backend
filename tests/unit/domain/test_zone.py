import pytest

from safevision.domain.errors import ValidationError
from safevision.domain.model.values import ZonePolygon
from safevision.domain.model.zone import Zone

SQUARE = [[0, 0], [1, 0], [1, 1], [0, 1]]


def test_coordinates_become_a_polygon():
    zone = Zone(name="Escalera", camera_id=2, polygon=SQUARE)
    assert zone.polygon == ZonePolygon.from_list(SQUARE)
    assert zone.is_active


def test_belongs_to_its_camera_only():
    zone = Zone(name="Escalera", camera_id=2, polygon=SQUARE)
    assert zone.belongs_to(2)
    assert not zone.belongs_to(3)


def test_inactive_zone():
    zone = Zone(name="Escalera", camera_id=2, polygon=SQUARE, is_active=0)
    assert zone.is_active is False


def test_polygon_needs_three_points():
    with pytest.raises(ValidationError):
        Zone(name="Escalera", camera_id=2, polygon=[[0, 0], [1, 1]])


def test_camera_is_required():
    with pytest.raises(ValidationError):
        Zone(name="Escalera", camera_id=0, polygon=SQUARE)
