import pytest

from safevision.domain.errors import ValidationError
from safevision.domain.model.event_type import EventType
from safevision.domain.model.values import Priority, Severity


def test_create_event_type():
    fall = EventType(id=1, name="  Caída ", severity=Severity(4), description="")
    assert fall.name == "Caída"
    assert fall.description is None
    assert fall.priority is Priority.HIGH


def test_integer_severity_is_converted():
    assert EventType(name="Merodeo", severity=2).severity == Severity(2)


@pytest.mark.parametrize("severity", [0, 5])
def test_invalid_severity(severity):
    with pytest.raises(ValidationError):
        EventType(name="X", severity=severity)


@pytest.mark.parametrize("name", ["", "   ", None])
def test_name_is_required(name):
    with pytest.raises(ValidationError):
        EventType(name=name, severity=1)


def test_description_must_be_text():
    with pytest.raises(ValidationError):
        EventType(name="X", severity=1, description=3)
