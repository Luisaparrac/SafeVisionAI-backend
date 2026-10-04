"""Initial data: event types from the documentation and a minimal demo setup."""
import hashlib
import os
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.models import Alerta, Camara, Evento, Sujeto, TipoEvento, Ubicacion, Usuario
from app.services import SEVERITY_TO_PRIORITY, now_local

EVENT_TYPES = [
    ("Caída", "Paso rápido de estar de pie a una posición cercana al suelo", 3),
    ("Colapso", "Pérdida súbita de estabilidad sin recuperación", 3),
    ("Inmovilidad prolongada", "Sin movimiento significativo durante un período definido", 2),
    ("Movimiento anormal", "Patrón de movimiento corporal inusual", 2),
    ("Permanencia en zona restringida", "El sujeto permanece en un área marcada como peligrosa", 2),
    ("Cambio repentino de postura", "Variación brusca de postura sin caída confirmada", 1),
]


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def seed(db: Session) -> None:
    for nombre, descripcion, nivel in EVENT_TYPES:
        if db.scalar(select(TipoEvento).where(TipoEvento.nombre == nombre)) is None:
            db.add(TipoEvento(nombre=nombre, descripcion=descripcion, nivel_severidad=nivel))
    db.commit()

    if db.scalar(select(Usuario)) is not None:
        return

    admin = Usuario(
        nombre="Administrador SafeVision",
        correo="admin@safevision.local",
        contrasena=hash_password(os.getenv("ADMIN_PASSWORD", secrets.token_urlsafe(12))),
    )
    db.add(admin)
    db.flush()

    zona_a = Ubicacion(nombre="Zona de monitoreo A", descripcion="Habitación principal", id_usuario=admin.id_usuario)
    zona_b = Ubicacion(nombre="Zona de monitoreo B", descripcion="Sala", id_usuario=admin.id_usuario)
    db.add_all([zona_a, zona_b])
    db.flush()

    cam1 = Camara(nombre="Cámara 01 · Tapo C110", direccion_ip="192.168.1.50",
                  estado="Sin conexión", id_ubicacion=zona_a.id_ubicacion)
    cam2 = Camara(nombre="Cámara 02", direccion_ip=None, estado="Sin conexión", id_ubicacion=zona_b.id_ubicacion)
    db.add_all([cam1, cam2])

    s1 = Sujeto(nombre="Individuo 01", tipo="Adulto mayor", descripcion=None, id_usuario=admin.id_usuario)
    s2 = Sujeto(nombre="Individuo 02", tipo="Persona", descripcion=None, id_usuario=admin.id_usuario)
    s3 = Sujeto(nombre="Mascota 01", tipo="Mascota", descripcion=None, id_usuario=admin.id_usuario)
    db.add_all([s1, s2, s3])
    db.commit()

    if not config.SEED_DEMO_EVENTS:
        return

    types = {t.nombre: t for t in db.scalars(select(TipoEvento))}
    base = now_local()
    samples = [
        ("Caída", s1, cam1, 70, "Revisado"),
        ("Movimiento anormal", s2, cam2, 55, "Revisado"),
        ("Cambio repentino de postura", s1, cam1, 40, "Revisado"),
        ("Inmovilidad prolongada", s2, cam2, 15, "Pendiente"),
        ("Caída", s1, cam1, 5, "Pendiente"),
    ]
    for type_name, subject, camera, minutes_ago, estado in samples:
        stamp = base - timedelta(minutes=minutes_ago)
        tipo = types[type_name]
        event = Evento(fecha=stamp.date(), hora=stamp.time(), descripcion="Evento de demostración",
                       estado=estado, id_sujeto=subject.id_sujeto,
                       id_tipo_evento=tipo.id_tipo_evento, id_camara=camera.id_camara)
        db.add(event)
        db.flush()
        db.add(Alerta(fecha=stamp.date(), hora=stamp.time(),
                      nivel=SEVERITY_TO_PRIORITY[tipo.nivel_severidad],
                      estado="Pendiente" if estado == "Pendiente" else "Atendida",
                      id_evento=event.id_evento))
    db.commit()
