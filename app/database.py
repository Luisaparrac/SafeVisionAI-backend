from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL


def normalize_url(url: str) -> str:
    """Render gives 'postgres://' or 'postgresql://'; SQLAlchemy needs the psycopg driver."""
    if not url:
        return "sqlite:///./safevision.db"
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


url = normalize_url(DATABASE_URL)
connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
