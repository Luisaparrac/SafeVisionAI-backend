from safevision.domain.model.camera import Camera
from safevision.domain.model.event_type import EventType
from safevision.domain.model.location import Location
from safevision.domain.model.subject import Subject
from safevision.domain.model.user import User
from safevision.domain.model.zone import Zone
from tests.fakes.unit_of_work import FakeUnitOfWork
from tests.fakes.users import TEST_EMAIL, TEST_NAME, TEST_PASSWORD_HASH

SQUARE = [[0, 0], [1, 0], [1, 1], [0, 1]]


def seed_reference_catalog(uow: FakeUnitOfWork) -> None:
    """Same rows as ``tests.integration.postgres.insert_reference_rows``.

    Ids: user 1 (``tests.fakes.users``); location 1 Casa; cameras 1 Sala, 2 Patio;
    zone 1 Escalera (camera 1);
    subject 1 Rosa; event types 1 Caída (4), 2 Merodeo (2), 3 Ruido (1), 4 Humo (3).
    """
    uow.users.add(User(name=TEST_NAME, email=TEST_EMAIL, password_hash=TEST_PASSWORD_HASH))
    uow.catalog.locations.add(Location(name="Casa", user_id=1))
    uow.cameras.add(Camera(name="Sala", ip_address="192.0.2.1", location_id=1))
    uow.cameras.add(Camera(name="Patio", ip_address="192.0.2.2", location_id=1))
    uow.cameras.zones.add(Zone(name="Escalera", camera_id=1, polygon=SQUARE))
    uow.catalog.subjects.add(Subject(name="Rosa", subject_type="elderly", user_id=1))
    for name, severity in [("Caída", 4), ("Merodeo", 2), ("Ruido", 1), ("Humo", 3)]:
        uow.event_types.add(EventType(name=name, severity=severity))
    uow.commit()
    uow.commits = 0
