import pytest

from safevision.application.use_cases.get_installations import GetInstallations
from safevision.domain.errors import NotFoundError
from safevision.domain.model.camera import Camera
from safevision.domain.model.event import Event
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


def add_event(uow, clock, event_type_id: int, camera_id: int = 1, **changes) -> None:
    uow.events.add(
        Event(camera_id=camera_id, event_type_id=event_type_id, occurred_at=clock.now(), **changes)
    )


def nodes(view):
    [casa] = view.locations
    patio, sala = casa.children
    [escalera] = sala.children
    return casa, patio, sala, escalera


def test_an_event_with_a_zone_counts_in_the_zone(uow, clock):
    add_event(uow, clock, 1, zone_id=1)
    casa, patio, sala, escalera = nodes(GetInstallations(uow).execute())
    assert (escalera.own_pending, sala.own_pending) == (1, 0)
    assert (casa.own_pending, patio.own_pending) == (0, 0)


def test_an_event_without_a_zone_counts_in_its_camera(uow, clock):
    add_event(uow, clock, 2, camera_id=2)
    _, patio, sala, _ = nodes(GetInstallations(uow).execute())
    assert (patio.own_pending, sala.own_pending) == (1, 0)


def test_an_event_of_a_zone_that_no_longer_exists_counts_in_its_camera(uow, clock):
    add_event(uow, clock, 2, zone_id=99)
    _, _, sala, escalera = nodes(GetInstallations(uow).execute())
    assert (sala.own_pending, escalera.own_pending) == (1, 0)


def test_an_event_with_a_zone_of_another_camera_counts_in_its_camera(uow, clock):
    add_event(uow, clock, 2, camera_id=2, zone_id=1)
    _, patio, _, escalera = nodes(GetInstallations(uow).execute())
    assert (patio.own_pending, escalera.own_pending) == (1, 0)


@pytest.mark.parametrize(
    ("status", "counted"),
    [("pending", 1), ("in_review", 1), ("resolved", 0), ("false_alarm", 0)],
)
def test_open_events_are_the_pending_ones(uow, clock, status, counted):
    add_event(uow, clock, 1, status=status)
    _, _, sala, _ = nodes(GetInstallations(uow).execute())
    assert sala.own_pending == counted


def test_an_open_event_of_a_missing_type_is_reported(uow, clock):
    add_event(uow, clock, 99)
    with pytest.raises(NotFoundError, match="Tipo de evento 99"):
        GetInstallations(uow).execute()


def test_a_closed_event_of_a_missing_type_is_ignored(uow, clock):
    add_event(uow, clock, 99, status="resolved")
    assert GetInstallations(uow).execute().locations


def test_an_open_event_of_a_missing_camera_is_reported(uow, clock):
    add_event(uow, clock, 1, camera_id=99)
    with pytest.raises(NotFoundError, match="Cámara 99"):
        GetInstallations(uow).execute()
