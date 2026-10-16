"""SQLAlchemy mapping of the team's PostgreSQL tables.

These rows are persistence details, separate from the domain entities; the
mappers translate between both. The tables already exist and belong to another
role: this module never creates, alters or drops them.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, FetchedValue, ForeignKey, SmallInteger, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=FetchedValue()
    )


class LocationRow(Base):
    __tablename__ = "locations"

    location_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))


class SubjectRow(Base):
    __tablename__ = "subjects"

    subject_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    subject_type: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))


class EventTypeRow(Base):
    __tablename__ = "event_types"

    event_type_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    severity_level: Mapped[int] = mapped_column(SmallInteger)
