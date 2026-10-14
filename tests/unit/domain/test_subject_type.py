import pytest

from safevision.domain.errors import ValidationError
from safevision.domain.model.values import SubjectType


def test_values_match_database():
    assert [t.value for t in SubjectType] == ["person", "child", "elderly", "pet"]


def test_parse():
    assert SubjectType.parse("elderly") is SubjectType.ELDERLY
    with pytest.raises(ValidationError):
        SubjectType.parse("adult")
