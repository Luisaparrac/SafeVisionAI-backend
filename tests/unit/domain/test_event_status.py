import pytest

from safevision.domain.errors import InvalidTransitionError, ValidationError
from safevision.domain.model.values import EventStatus, ReviewLabel

S = EventStatus
ALLOWED = {
    (S.PENDING, S.IN_REVIEW),
    (S.PENDING, S.RESOLVED),
    (S.PENDING, S.FALSE_ALARM),
    (S.IN_REVIEW, S.RESOLVED),
    (S.IN_REVIEW, S.FALSE_ALARM),
}


@pytest.mark.parametrize("current", list(S))
@pytest.mark.parametrize("target", list(S))
def test_transition_table(current, target):
    allowed = (current, target) in ALLOWED
    assert current.can_transition_to(target) is allowed
    if allowed:
        assert current.transition_to(target) is target
    else:
        with pytest.raises(InvalidTransitionError):
            current.transition_to(target)


@pytest.mark.parametrize("terminal", [S.RESOLVED, S.FALSE_ALARM])
def test_terminal_states_have_no_exit(terminal):
    assert not any(terminal.can_transition_to(target) for target in S)


def test_labels():
    assert S.PENDING.label is ReviewLabel.PENDING
    assert S.IN_REVIEW.label is ReviewLabel.PENDING
    assert S.RESOLVED.label is ReviewLabel.REVIEWED
    assert S.FALSE_ALARM.label is ReviewLabel.REVIEWED
    assert S.PENDING.label == "Pendiente"
    assert S.RESOLVED.label == "Revisado"


def test_open_statuses():
    assert {s for s in S if s.is_open} == {S.PENDING, S.IN_REVIEW}


def test_review_label_groups_statuses():
    assert ReviewLabel.PENDING.statuses == (S.PENDING, S.IN_REVIEW)
    assert ReviewLabel.REVIEWED.statuses == (S.RESOLVED, S.FALSE_ALARM)
    assert ReviewLabel.parse("Revisado") is ReviewLabel.REVIEWED
    with pytest.raises(ValidationError):
        ReviewLabel.parse("Cerrado")


def test_parse_database_value():
    assert S.parse("in_review") is S.IN_REVIEW
    with pytest.raises(ValidationError):
        S.parse("closed")
