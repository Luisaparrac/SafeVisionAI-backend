"""The 7 tables from the SafeVision AI documentation (section 14)."""
from datetime import date, time

from sqlalchemy import Date, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Usuario(Base):
    __tablename__ = "usuario"
    id_usuario: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    correo: Mapped[str] = mapped_column(String(150), unique=True)
    contrasena: Mapped[str] = mapped_column(String(255))  # stored as a PBKDF2 hash


class Ubicacion(Base):
    __tablename__ = "ubicacion"
    id_ubicacion: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[str | None] = mapped_column(Text)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"))


class Camara(Base):
    __tablename__ = "camara"
    id_camara: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    direccion_ip: Mapped[str | None] = mapped_column(String(45))
    estado: Mapped[str] = mapped_column(String(30), default="Sin conexión")
    id_ubicacion: Mapped[int] = mapped_column(ForeignKey("ubicacion.id_ubicacion"))
    ubicacion: Mapped[Ubicacion] = relationship()


class Sujeto(Base):
    __tablename__ = "sujeto"
    id_sujeto: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    tipo: Mapped[str] = mapped_column(String(30))  # Persona, Niño, Adulto mayor, Mascota
    descripcion: Mapped[str | None] = mapped_column(Text)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"))


class TipoEvento(Base):
    __tablename__ = "tipo_evento"
    id_tipo_evento: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text)
    nivel_severidad: Mapped[int] = mapped_column(Integer)  # 1 Bajo, 2 Medio, 3 Alto


class Evento(Base):
    __tablename__ = "evento"
    id_evento: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date)
    hora: Mapped[time] = mapped_column(Time)
    descripcion: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(20), default="Pendiente")  # Pendiente / Revisado
    id_sujeto: Mapped[int] = mapped_column(ForeignKey("sujeto.id_sujeto"))
    id_tipo_evento: Mapped[int] = mapped_column(ForeignKey("tipo_evento.id_tipo_evento"))
    id_camara: Mapped[int] = mapped_column(ForeignKey("camara.id_camara"))

    sujeto: Mapped[Sujeto] = relationship()
    tipo_evento: Mapped[TipoEvento] = relationship()
    camara: Mapped[Camara] = relationship()
    alertas: Mapped[list["Alerta"]] = relationship(back_populates="evento")


class Alerta(Base):
    __tablename__ = "alerta"
    id_alerta: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date)
    hora: Mapped[time] = mapped_column(Time)
    nivel: Mapped[str] = mapped_column(String(10))  # Alto / Medio / Bajo
    estado: Mapped[str] = mapped_column(String(20), default="Pendiente")  # Pendiente / Atendida
    id_evento: Mapped[int] = mapped_column(ForeignKey("evento.id_evento"))
    evento: Mapped[Evento] = relationship(back_populates="alertas")
