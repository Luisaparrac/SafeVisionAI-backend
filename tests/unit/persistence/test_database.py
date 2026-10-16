import pytest

from safevision.adapters.outbound.persistence.database import (
    make_engine,
    make_session_factory,
    normalize_url,
)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("postgres://u:p@localhost/db", "postgresql+psycopg://u:p@localhost/db"),
        ("postgresql://u:p@localhost/db", "postgresql+psycopg://u:p@localhost/db"),
        ("postgresql+psycopg://u:p@localhost/db", "postgresql+psycopg://u:p@localhost/db"),
        (
            "postgresql://u:p@localhost:5432/db?sslmode=require",
            "postgresql+psycopg://u:p@localhost:5432/db?sslmode=require",
        ),
    ],
)
def test_normalize_url_selects_psycopg(url, expected):
    assert normalize_url(url) == expected


def test_engine_is_created_without_connecting():
    engine = make_engine("postgresql://test:test@localhost/test")
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "psycopg"
    assert engine.pool._pre_ping is True
    engine.dispose()


def test_sessions_keep_loaded_values_after_commit():
    engine = make_engine("postgresql://test:test@localhost/test")
    factory = make_session_factory(engine)
    with factory() as session:
        assert session.bind is engine
        assert session.autoflush is False
        assert factory.kw["expire_on_commit"] is False
    engine.dispose()
