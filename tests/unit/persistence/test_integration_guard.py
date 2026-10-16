"""The integration database guard only lets local "*_test" databases through."""

import pytest

from tests.integration.guard import UnsafeTestDatabaseError, ensure_safe_test_database


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://ci:ci@localhost:5432/safevision_test",
        "postgresql://ci:ci@127.0.0.1/safevision_test",
        "postgres://ci@localhost/other_test",
        "postgresql+psycopg://ci:ci@localhost:5432/safevision_test?sslmode=disable",
    ],
)
def test_local_test_databases_are_accepted(url):
    ensure_safe_test_database(url)


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("postgresql://ci:ci@db.example.com/safevision_test", "localhost"),
        ("postgresql://ci:ci@10.0.0.5/safevision_test", "localhost"),
        ("postgresql://ci:ci@/safevision_test", "localhost"),
        ("postgresql://ci:ci@localhost/safevision_test?host=db.example.com", "localhost"),
        ("postgresql://ci:ci@localhost/safevision_test?service=prod", "localhost"),
        ("postgresql://ci:ci@localhost/safevisionai", "_test"),
        ("postgresql://ci:ci@localhost/safevision_test_copy", "_test"),
        ("postgresql://ci:ci@localhost", "_test"),
        ("sqlite:///safevision_test", "PostgreSQL"),
        ("esto no es una url", "válida"),
    ],
)
def test_anything_else_is_rejected(url, reason):
    with pytest.raises(UnsafeTestDatabaseError, match=reason):
        ensure_safe_test_database(url)


def test_messages_never_reveal_the_url():
    secret = "postgresql://user:s3cret-pass@db.example.com/prod"
    with pytest.raises(UnsafeTestDatabaseError) as info:
        ensure_safe_test_database(secret)
    assert "s3cret" not in str(info.value)
    assert "db.example.com" not in str(info.value)
    assert info.value.__cause__ is None
