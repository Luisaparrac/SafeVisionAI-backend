from datetime import timedelta

import pytest

from safevision.application.use_cases.list_events import ListEvents
from safevision.domain.model.event import Event


@pytest.fixture
def list_events(uow, clock, presenter) -> ListEvents:
    # event type ids: 1 Caída (Alto), 2 Merodeo (Medio), 3 Ruido (Bajo), 4 Humo (Alto)
    rows = [
        {"event_type_id": 1, "subject_id": 1},
        {"event_type_id": 2, "status": "resolved"},
        {"event_type_id": 3, "camera_id": 2},
        {"event_type_id": 4, "status": "in_review", "zone_id": 1},
        {"event_type_id": 2, "status": "false_alarm", "detected_class": "dog"},
    ]
    for minutes, row in enumerate(rows):
        occurred = clock.now() + timedelta(minutes=minutes)
        uow.events.add(Event(**({"camera_id": 1, "occurred_at": occurred} | row)))
    uow.commit()
    return ListEvents(uow, presenter)


def ids(views) -> list[int]:
    return [view.id for view in views]


def test_without_filters_newest_first(list_events):
    assert ids(list_events.execute()) == [5, 4, 3, 2, 1]


@pytest.mark.parametrize(
    ("priority", "expected"), [("Alto", [4, 1]), ("Medio", [5, 2]), ("Bajo", [3])]
)
def test_filter_by_priority(list_events, priority, expected):
    assert ids(list_events.execute(priority=priority)) == expected


@pytest.mark.parametrize(("status", "expected"), [("Pendiente", [4, 3, 1]), ("Revisado", [5, 2])])
def test_filter_by_status(list_events, status, expected):
    assert ids(list_events.execute(status=status)) == expected


def test_filters_combine(list_events):
    assert ids(list_events.execute(priority="Medio", status="Revisado")) == [5, 2]
    assert ids(list_events.execute(priority="Bajo", status="Revisado")) == []


@pytest.mark.parametrize("label", ["", "alto", "Urgente"])
def test_unknown_labels_are_ignored(list_events, label):
    assert len(list_events.execute(priority=label, status=label)) == 5


@pytest.mark.parametrize(
    ("q", "expected"),
    [
        ("rosa", [1]),  # subject
        ("MERODEO", [5, 2]),  # type
        ("escalera", [4]),  # zone inside the location text
        ("perro", [5]),  # unidentified subject label
        ("3", [3]),  # id
        ("  caída ", [1]),
        ("nada", []),
    ],
)
def test_text_search(list_events, q, expected):
    assert ids(list_events.execute(q=q)) == expected


def test_blank_text_matches_everything(list_events):
    assert len(list_events.execute(q="   ")) == 5
