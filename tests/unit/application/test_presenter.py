from datetime import UTC, datetime

import pytest

from safevision.application.dto import EventView
from safevision.domain.errors import NotFoundError
from safevision.domain.model.event import Event

# 03:30 UTC is 22:30 of the previous day in Bogota (UTC-5).
OCCURRED = datetime(2026, 10, 14, 3, 30, 15, tzinfo=UTC)


def stored(uow, **overrides) -> Event:
    data = {"camera_id": 1, "event_type_id": 1, "occurred_at": OCCURRED}
    return uow.events.add(Event(**(data | overrides)))


def test_full_view_with_local_time(uow, presenter):
    event = stored(
        uow,
        subject_id=1,
        zone_id=1,
        description="Se cayó",
        detected_class="person",
        confidence=0.87,
        evidence_url="https://example.com/evidencias/0001.jpg",
    )
    assert presenter.present(uow, event) == EventView(
        id=1,
        type="Caída",
        subject="Rosa",
        location="Casa · Escalera",
        camera="Sala",
        date="2026-10-13",
        time="22:30:15",
        occurred_at="2026-10-13T22:30:15-05:00",
        priority="Alto",
        status="Pendiente",
        description="Se cayó",
        detected_class="person",
        detected_class_label="Persona",
        confidence=0.87,
        evidence_url="https://example.com/evidencias/0001.jpg",
    )


@pytest.mark.parametrize(
    ("detected_class", "subject"),
    [("person", "Persona sin identificar"), ("dog", "Perro sin identificar")],
)
def test_unknown_subject_uses_detected_class(uow, presenter, detected_class, subject):
    view = presenter.present(uow, stored(uow, detected_class=detected_class))
    assert view.subject == subject
    assert view.location == "Casa"


@pytest.mark.parametrize(
    ("event_type_id", "priority"), [(1, "Alto"), (4, "Alto"), (2, "Medio"), (3, "Bajo")]
)
def test_priority_from_event_type_severity(uow, presenter, event_type_id, priority):
    assert presenter.present(uow, stored(uow, event_type_id=event_type_id)).priority == priority


@pytest.mark.parametrize(
    ("status", "label"),
    [("pending", "Pendiente"), ("in_review", "Pendiente"), ("resolved", "Revisado")],
)
def test_status_label(uow, presenter, status, label):
    assert presenter.present(uow, stored(uow, status=status)).status == label


@pytest.mark.parametrize(
    ("detected_class", "label"),
    [("person", "Persona"), ("dog", "Perro"), ("cat", "Gato"), ("other_animal", "Animal")],
)
def test_detected_class_and_its_label(uow, presenter, detected_class, label):
    view = presenter.present(uow, stored(uow, detected_class=detected_class))
    assert (view.detected_class, view.detected_class_label) == (detected_class, label)


@pytest.mark.parametrize("confidence", [0, 0.5, 1])
def test_confidence_as_stored(uow, presenter, confidence):
    assert presenter.present(uow, stored(uow, confidence=confidence)).confidence == confidence


def test_without_confidence_and_class_the_defaults_are_shown(uow, presenter):
    view = presenter.present(uow, stored(uow))
    assert (
        view.detected_class,
        view.detected_class_label,
        view.confidence,
        view.evidence_url,
    ) == ("person", "Persona", None, None)


@pytest.mark.parametrize(
    "url", ["https://example.com/evidencias/x.jpg", "http://example.com/evidencias/x.jpg"]
)
def test_http_evidence_is_published(uow, presenter, url):
    assert presenter.present(uow, stored(uow, evidence_url=url)).evidence_url == url


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "data:image/png;base64,iVBORw0KGgo=",
        "C:\\evidencias\\x.jpg",
        "/evidencias/x.jpg",
        "https:///x.jpg",
        None,
    ],
)
def test_other_evidence_is_withheld(uow, presenter, url):
    assert presenter.present(uow, stored(uow, evidence_url=url)).evidence_url is None


def test_blank_evidence_is_withheld(uow, presenter):
    # The entity turns blank text into None, so the view never sees an empty string.
    assert presenter.present(uow, stored(uow, evidence_url="  ")).evidence_url is None


def test_deleted_subject_and_zone_are_tolerated(uow, presenter):
    view = presenter.present(uow, stored(uow, subject_id=9, zone_id=9))
    assert view.subject == "Persona sin identificar"
    assert view.location == "Casa"


def test_missing_camera_is_an_error(uow, presenter):
    with pytest.raises(NotFoundError):
        presenter.present(uow, stored(uow, camera_id=9))


def test_present_many_keeps_order(uow, presenter):
    events = [stored(uow, event_type_id=t) for t in (3, 1, 2)]
    assert [v.type for v in presenter.present_many(uow, events)] == ["Ruido", "Caída", "Merodeo"]


def test_unsaved_event_cannot_be_presented(uow, presenter):
    with pytest.raises(ValueError):
        presenter.present(uow, Event(camera_id=1, event_type_id=1, occurred_at=OCCURRED))
