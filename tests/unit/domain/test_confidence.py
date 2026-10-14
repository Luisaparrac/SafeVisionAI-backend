import pytest

from safevision.domain.errors import ValidationError
from safevision.domain.model.values import Confidence


@pytest.mark.parametrize("value", [0, 1, 0.5, 0.93])
def test_valid_confidence(value):
    confidence = Confidence(value)
    assert confidence.value == value
    assert isinstance(confidence.value, float)


@pytest.mark.parametrize("value", [-0.01, 1.01, float("nan"), float("inf"), "0.5", None, True])
def test_invalid_confidence(value):
    with pytest.raises(ValidationError):
        Confidence(value)


def test_equality_by_value():
    assert Confidence(1) == Confidence(1.0)
