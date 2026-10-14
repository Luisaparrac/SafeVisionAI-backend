from datetime import UTC, datetime

import pytest

from safevision.domain.errors import ValidationError
from safevision.domain.model.user import User
from safevision.domain.model.values import Email


def make_user(**overrides) -> User:
    data = {"name": "Ana", "email": "ana@example.com", "password_hash": "hash-value"}
    return User(**(data | overrides))


def test_create_user():
    user = make_user(id=1, created_at=datetime(2026, 1, 1, tzinfo=UTC))
    assert user.email == Email("ana@example.com")
    assert user.id == 1


def test_password_hash_is_not_shown_in_repr():
    assert "hash-value" not in repr(make_user())


@pytest.mark.parametrize("email", ["ana", "ana@example"])
def test_invalid_email(email):
    with pytest.raises(ValidationError):
        make_user(email=email)


def test_password_hash_is_required():
    with pytest.raises(ValidationError):
        make_user(password_hash="")


def test_created_at_needs_time_zone():
    with pytest.raises(ValidationError):
        make_user(created_at=datetime(2026, 1, 1))
