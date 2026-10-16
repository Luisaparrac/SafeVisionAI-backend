import pytest

from safevision.domain.errors import ValidationError
from safevision.domain.model.values import CameraStatus


def test_values_match_database():
    assert [s.value for s in CameraStatus] == ["active", "inactive", "disconnected", "maintenance"]


@pytest.mark.parametrize("value", ["on", "", "ACTIVE"])
def test_unknown_status_is_rejected(value):
    with pytest.raises(ValidationError):
        CameraStatus.parse(value)
