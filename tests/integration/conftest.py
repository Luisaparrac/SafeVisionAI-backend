import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def session(pg_seeded):
    """Session on the seeded test database; uncommitted changes are discarded."""
    with Session(pg_seeded) as session:
        yield session
