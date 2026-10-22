import pytest

from safevision.domain.errors import ValidationError
from safevision.domain.model.user import User


def test_create_user():
    user = User(id=2, name=" Ana ", email=" ana@example.com ", password_hash="pbkdf2_sha256$1$a$b")
    assert (user.id, user.name, user.email) == (2, "Ana", "ana@example.com")
    assert user.password_hash == "pbkdf2_sha256$1$a$b"


def test_new_user_has_no_id():
    assert User(name="Ana", email="ana@example.com", password_hash="x").id is None


@pytest.mark.parametrize("field", ["name", "email", "password_hash"])
@pytest.mark.parametrize("value", [None, "", "  "])
def test_text_fields_are_required(field, value):
    data = {"name": "Ana", "email": "ana@example.com", "password_hash": "x"}
    with pytest.raises(ValidationError, match=field):
        User(**(data | {field: value}))


def test_invalid_id():
    with pytest.raises(ValidationError):
        User(id=0, name="Ana", email="ana@example.com", password_hash="x")


def test_password_hash_is_not_shown():
    user = User(name="Ana", email="ana@example.com", password_hash="secret-hash")
    assert "secret-hash" not in repr(user)
