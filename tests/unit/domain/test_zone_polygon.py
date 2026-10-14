import pytest

from safevision.domain.errors import ValidationError
from safevision.domain.model.values import ZonePolygon

TRIANGLE = [[0, 0], [10, 0], [5, 8.5]]


def test_round_trip_with_database_shape():
    polygon = ZonePolygon.from_list(TRIANGLE)
    assert polygon.points == ((0.0, 0.0), (10.0, 0.0), (5.0, 8.5))
    assert polygon.to_list() == [[0.0, 0.0], [10.0, 0.0], [5.0, 8.5]]


def test_accepts_tuples():
    assert len(ZonePolygon(((0, 0), (1, 0), (1, 1), (0, 1))).points) == 4


@pytest.mark.parametrize(
    "coordinates",
    [
        [],
        [[0, 0], [1, 1]],
        [[0, 0], [1, 1], [2]],
        [[0, 0], [1, 1], [2, 2, 2]],
        [[0, 0], [1, 1], ["a", 2]],
        [[0, 0], [1, 1], [True, 2]],
        [[0, 0], [1, 1], [float("nan"), 2]],
        [[0, 0], [1, 1], "xy"],
        "not a list",
        None,
        {"x": 1},
    ],
)
def test_invalid_coordinates(coordinates):
    with pytest.raises(ValidationError):
        ZonePolygon.from_list(coordinates)


def test_equality_by_points():
    assert ZonePolygon.from_list(TRIANGLE) == ZonePolygon.from_list(TRIANGLE)
