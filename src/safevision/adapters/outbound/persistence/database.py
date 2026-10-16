"""Engine and session factory for the PostgreSQL database."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def normalize_url(url: str) -> str:
    """Accepts 'postgres://' or 'postgresql://' URLs and selects the psycopg 3 driver."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def make_engine(url: str) -> Engine:
    """Lazy engine: no connection is opened until the first query.

    ``pool_pre_ping`` discards connections the server closed while idle (the
    free hosting plan sleeps), and ``pool_recycle`` renews them every 30 minutes.
    """
    return create_engine(normalize_url(url), pool_pre_ping=True, pool_recycle=1800)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    # Entities are mapped out of the rows before the commit, so rows need not be refreshed.
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
