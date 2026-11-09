"""The tree of installations built from the rows of a real database."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import Session

from safevision.adapters.outbound.persistence.database import make_session_factory
from safevision.adapters.outbound.persistence.orm import EventRow, LocationRow
from safevision.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from safevision.application.presenter import EventPresenter
from safevision.application.services.alert_board import AlertBoard
from safevision.application.use_cases.get_installations import GetInstallations
from safevision.application.use_cases.get_metrics import GetMetrics
from safevision.application.use_cases.rebuild_alert_board import RebuildAlertBoard

pytestmark = pytest.mark.integration

MOMENT = datetime(2026, 1, 1, tzinfo=UTC)


def event(camera_id: int, event_type_id: int, status: str = "pending", zone_id=None) -> EventRow:
    return EventRow(
        camera_id=camera_id,
        event_type_id=event_type_id,
        status=status,
        zone_id=zone_id,
        occurred_at=MOMENT,
        detected_class="person",
    )


@pytest.fixture
def uow(pg_seeded):
    return SqlAlchemyUnitOfWork(make_session_factory(pg_seeded))


def test_without_events(uow):
    view = GetInstallations(uow).execute()
    assert (view.pending, view.max_severity, view.priority) == (0, None, None)
    [casa] = view.locations
    assert [camera.name for camera in casa.children] == ["Patio", "Sala"]
    assert [zone.name for zone in casa.children[1].children] == ["Escalera"]


def test_real_rows_are_counted_and_added_up(uow, pg_seeded):
    with Session(pg_seeded) as session:
        session.add_all(
            [
                event(1, 1, zone_id=1),
                event(1, 2, status="in_review"),
                event(2, 3),
                event(2, 4, status="resolved"),
                event(2, 1, status="false_alarm"),
            ]
        )
        session.commit()

    view = GetInstallations(uow).execute()

    [casa] = view.locations
    patio, sala = casa.children
    [escalera] = sala.children
    assert (escalera.own_pending, escalera.pending, escalera.max_severity) == (1, 1, 4)
    assert (sala.own_pending, sala.pending, sala.max_severity) == (1, 2, 4)
    assert (patio.own_pending, patio.pending, patio.priority) == (1, 1, "Bajo")
    assert (casa.own_pending, casa.pending, casa.priority) == (0, 3, "Alto")
    assert view.pending == 3


def test_the_total_matches_the_pending_count_of_the_metrics(uow, pg_seeded):
    with Session(pg_seeded) as session:
        session.add_all([event(1, 1), event(2, 2, status="in_review"), event(2, 3, "resolved")])
        session.commit()
    board = AlertBoard(10)
    RebuildAlertBoard(uow, board, EventPresenter(ZoneInfo("America/Bogota"))).execute()
    assert GetInstallations(uow).execute().pending == GetMetrics(uow, board).execute().pending == 2


def test_a_location_without_cameras_and_a_camera_without_zones(uow, pg_seeded):
    with Session(pg_seeded) as session:
        session.add(LocationRow(name="Bodega", user_id=1))
        session.commit()
    bodega, casa = GetInstallations(uow).execute().locations
    assert (bodega.name, bodega.children) == ("Bodega", ())
    assert casa.children[0].children == ()
