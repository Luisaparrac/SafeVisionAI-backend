import pytest

from safevision.domain.errors import InvalidTransitionError, ValidationError
from safevision.domain.model.values import AlertStatus

A = AlertStatus
ALLOWED = {
    (A.ACTIVE, A.SEEN),
    (A.ACTIVE, A.RESOLVED),
    (A.ACTIVE, A.DISMISSED),
    (A.SEEN, A.RESOLVED),
    (A.SEEN, A.DISMISSED),
}


@pytest.mark.parametrize("current", list(A))
@pytest.mark.parametrize("target", list(A))
def test_transition_table(current, target):
    allowed = (current, target) in ALLOWED
    assert current.can_transition_to(target) is allowed
    if not allowed:
        with pytest.raises(InvalidTransitionError):
            current.transition_to(target)


def test_open_statuses():
    assert {s for s in A if s.is_open} == {A.ACTIVE, A.SEEN}


def test_spanish_labels():
    assert [s.label for s in A] == ["Activa", "Vista", "Atendida", "Descartada"]


def test_values_match_database():
    assert [s.value for s in A] == ["active", "seen", "resolved", "dismissed"]
    with pytest.raises(ValidationError):
        A.parse("closed")
