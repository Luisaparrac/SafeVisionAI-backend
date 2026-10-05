"""Mapping of the team's Azure PostgreSQL schema (01_tables.sql).

The tables already exist and are owned by safevision_admin. This backend never
creates or alters them; it only reads and writes rows.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (BigInteger, Boolean, DateTime, FetchedValue, ForeignKey, Numeric,
                        SmallInteger, String, Text)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class Location(Base):
    __tablename__ = "locations"
    location_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))


class Camera(Base):
    __tablename__ = "cameras"
    camera_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    ip_address: Mapped[str] = mapped_column(INET)
    status: Mapped[str] = mapped_column(String, server_default=FetchedValue())  # active, inactive, disconnected, maintenance
    location_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("locations.location_id"))
    location: Mapped[Location] = relationship()


class Zone(Base):
    __tablename__ = "zones"
    zone_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    coordinates: Mapped[list] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=FetchedValue())
    camera_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cameras.camera_id"))


class Subject(Base):
    __tablename__ = "subjects"
    subject_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    subject_type: Mapped[str] = mapped_column(String)  # person, child, elderly, pet
    description: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))


class EventType(Base):
    __tablename__ = "event_types"
    event_type_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    severity_level: Mapped[int] = mapped_column(SmallInteger)  # 1..4


class Event(Base):
    __tablename__ = "events"
    event_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, server_default=FetchedValue())  # pending, in_review, resolved, false_alarm
    detected_class: Mapped[str] = mapped_column(String, server_default=FetchedValue())  # person, dog, cat, other_animal
    confidence: Mapped[Decimal | None] = mapped_column(Numeric)
    evidence_url: Mapped[str | None] = mapped_column(String)
    subject_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("subjects.subject_id"))
    event_type_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("event_types.event_type_id"))
    camera_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cameras.camera_id"))
    zone_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("zones.zone_id"))

    subject: Mapped[Subject | None] = relationship()
    event_type: Mapped[EventType] = relationship()
    camera: Mapped[Camera] = relationship()
    zone: Mapped[Zone | None] = relationship()


class Alert(Base):
    __tablename__ = "alerts"
    alert_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    level: Mapped[int] = mapped_column(SmallInteger)  # 1..4
    status: Mapped[str] = mapped_column(String, server_default=FetchedValue())  # active, seen, resolved, dismissed
    attended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attended_by_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    event_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("events.event_id"))
