import pytest

from safevision.domain.errors import ValidationError
from safevision.domain.model.values import DetectedClass


def test_values_match_database():
    assert [c.value for c in DetectedClass] == ["person", "dog", "cat", "other_animal"]


@pytest.mark.parametrize(
    ("value", "label"),
    [("person", "Persona"), ("dog", "Perro"), ("cat", "Gato"), ("other_animal", "Animal")],
)
def test_spanish_labels(value, label):
    assert DetectedClass.parse(value).label == label


def test_unknown_class_is_rejected():
    with pytest.raises(ValidationError):
        DetectedClass.parse("bird")
