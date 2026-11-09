import pytest

from safevision.application.use_cases.get_installations import GetInstallations
from safevision.domain.errors import NotFoundError
from safevision.domain.model.camera import Camera
from safevision.domain.model.location import Location
from safevision.domain.model.zone import Zone
from tests.fakes.catalog import SQUARE
from tests.fakes.unit_of_work import FakeUnitOfWork


def add_location(uow, name: str) -> None:
    uow.catalog.locations.add(Location(name=name, user_id=1))


def add_camera(uow, name: str, location_id: int) -> None:
    uow.cameras.add(Camera(name=name, ip_address="192.0.2.9", location_id=location_id))


def add_zone(uow, name: str, camera_id: int) -> None:
    uow.cameras.zones.add(Zone(name=name, camera_id=camera_id, polygon=SQUARE))


def test_an_empty_database():
    view = GetInstallations(FakeUnitOfWork()).execute()
    assert (view.pending, view.max_severity, view.priority, view.locations) == (0, None, None, ())


def test_locations_contain_their_cameras_and_these_their_zones(uow):
    view = GetInstallations(uow).execute()
    [casa] = view.locations
    assert (casa.id, casa.name, casa.status) == (1, "Casa", None)
    patio, sala = casa.children
    assert (patio.id, patio.name, patio.status, patio.children) == (2, "Patio", "active", ())
    [escalera] = sala.children
    assert (escalera.id, escalera.name, escalera.status) == (1, "Escalera", None)
    assert escalera.children == ()


def test_a_location_without_cameras_is_listed(uow):
    add_location(uow, "Bodega")
    bodega, casa = GetInstallations(uow).execute().locations
    assert (bodega.name, bodega.children) == ("Bodega", ())
    assert casa.name == "Casa"


def test_siblings_are_ordered_by_name_and_then_by_id(uow):
    add_camera(uow, "Sala", 1)  # same name as camera 1, higher id
    add_camera(uow, "Cocina", 1)
    add_zone(uow, "Puerta", 1)
    add_zone(uow, "Balcón", 1)
    [casa] = GetInstallations(uow).execute().locations
    assert [(c.name, c.id) for c in casa.children] == [
        ("Cocina", 4),
        ("Patio", 2),
        ("Sala", 1),
        ("Sala", 3),
    ]
    assert [z.name for z in casa.children[2].children] == ["Balcón", "Escalera", "Puerta"]


def test_the_order_does_not_depend_on_the_order_of_the_rows():
    def seeded(names: list[str]) -> list[str]:
        uow = FakeUnitOfWork()
        add_location(uow, "Casa")
        for name in names:
            add_camera(uow, name, 1)
        [casa] = GetInstallations(uow).execute().locations
        return [c.name for c in casa.children]

    assert seeded(["b", "c", "a"]) == seeded(["c", "a", "b"]) == ["a", "b", "c"]


def test_a_camera_of_a_missing_location_is_reported(uow):
    add_camera(uow, "Perdida", 99)
    with pytest.raises(NotFoundError, match="Ubicación 99"):
        GetInstallations(uow).execute()


def test_a_zone_of_a_missing_camera_is_reported(uow):
    add_zone(uow, "Perdida", 99)
    with pytest.raises(NotFoundError, match="Cámara 99"):
        GetInstallations(uow).execute()
