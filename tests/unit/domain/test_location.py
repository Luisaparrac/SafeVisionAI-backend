import pytest

from safevision.domain.errors import ValidationError
from safevision.domain.model.location import Location


def test_create_location():
    home = Location(id=3, name=" Casa ", user_id=1, description=" Primer piso ")
    assert (home.id, home.name, home.user_id, home.description) == (3, "Casa", 1, "Primer piso")


def test_new_location_has_no_id():
    assert Location(name="Casa", user_id=1).id is None


@pytest.mark.parametrize("user_id", [0, -1, None, "1", True])
def test_owner_is_required(user_id):
    with pytest.raises(ValidationError):
        Location(name="Casa", user_id=user_id)


def test_invalid_id():
    with pytest.raises(ValidationError):
        Location(id=0, name="Casa", user_id=1)


def test_name_is_required():
    with pytest.raises(ValidationError):
        Location(name=" ", user_id=1)
