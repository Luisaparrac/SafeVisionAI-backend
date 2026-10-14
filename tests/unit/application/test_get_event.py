import pytest

from safevision.application.use_cases.get_event import GetEvent
from safevision.domain.errors import NotFoundError
from safevision.domain.model.event import Event


def test_returns_the_view(uow, clock, presenter):
    uow.events.add(Event(camera_id=2, event_type_id=3, occurred_at=clock.now()))
    uow.commit()
    view = GetEvent(uow, presenter).execute(1)
    assert (view.id, view.camera, view.type, view.priority) == (1, "Patio", "Ruido", "Bajo")
    assert uow.commits == 1  # reading does not commit


def test_unknown_event(uow, presenter):
    with pytest.raises(NotFoundError, match="Evento 8 no existe"):
        GetEvent(uow, presenter).execute(8)
