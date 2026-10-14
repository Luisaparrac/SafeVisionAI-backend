import pytest

from safevision.domain.errors import ValidationError
from safevision.domain.model.values import Priority, Severity


@pytest.mark.parametrize(
    ("level", "priority"),
    [(4, Priority.HIGH), (3, Priority.HIGH), (2, Priority.MEDIUM), (1, Priority.LOW)],
)
def test_severity_maps_to_priority(level, priority):
    assert Severity(level).priority is priority


@pytest.mark.parametrize("level", [0, 5, -1, 2.5, "3", True, None])
def test_invalid_severity_is_rejected(level):
    with pytest.raises(ValidationError):
        Severity(level)


def test_severities_compare_by_level():
    assert Severity(4) > Severity(3) > Severity(1)
    assert Severity(2) == Severity(2)
    assert max(Severity(1), Severity(3), Severity(2)) == Severity(3)


def test_severity_is_immutable():
    with pytest.raises(AttributeError):
        Severity(1).level = 2


def test_priority_labels_are_spanish():
    assert [p.value for p in Priority] == ["Alto", "Medio", "Bajo"]


def test_priority_groups_severity_levels():
    assert Priority.HIGH.severity_levels == (3, 4)
    assert Priority.MEDIUM.severity_levels == (2,)
    assert Priority.LOW.severity_levels == (1,)


def test_every_level_belongs_to_the_priority_it_maps_to():
    for level in range(Severity.MIN, Severity.MAX + 1):
        assert level in Severity(level).priority.severity_levels


def test_parse_priority():
    assert Priority.parse("Medio") is Priority.MEDIUM
    with pytest.raises(ValidationError):
        Priority.parse("Urgente")
