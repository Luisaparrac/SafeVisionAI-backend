import pytest

from safevision.domain.errors import ValidationError
from safevision.domain.model.values import Email


@pytest.mark.parametrize("value", ["ana@example.com", "A.B+tag@sub.example.org", "x@y.co"])
def test_valid_email(value):
    assert str(Email(value)) == value


def test_surrounding_spaces_are_removed():
    assert Email("  ana@example.com ").value == "ana@example.com"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "ana",
        "ana@",
        "@example.com",
        "ana@example",
        "ana@@example.com",
        "a na@example.com",
        None,
    ],
)
def test_invalid_email(value):
    with pytest.raises(ValidationError):
        Email(value)
