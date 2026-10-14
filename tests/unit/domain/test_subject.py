import pytest

from safevision.domain.errors import ValidationError
from safevision.domain.model.subject import Subject
from safevision.domain.model.values import SubjectType


def test_create_subject():
    subject = Subject(id=4, name="Abuela Rosa", subject_type="elderly", user_id=1)
    assert subject.subject_type is SubjectType.ELDERLY
    assert subject.description is None


@pytest.mark.parametrize(
    "overrides",
    [{"subject_type": "adult"}, {"name": ""}, {"user_id": None}, {"description": 5}],
)
def test_invalid_subject(overrides):
    data = {"name": "Toby", "subject_type": "pet", "user_id": 1}
    with pytest.raises(ValidationError):
        Subject(**(data | overrides))
