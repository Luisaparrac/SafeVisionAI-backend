"""System logic: keeps the database and the in-memory structures in sync."""
from datetime import datetime
from threading import Lock
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app import config
from app.models import Alerta, Camara, Evento, Sujeto, TipoEvento
from app.schemas import EventCreate, EventView
from app.structures import AlertPriorityQueue, EventHistory
from app.structures.priority_queue import AlertEntry

SEVERITY_TO_PRIORITY = {3: "Alto", 2: "Medio", 1: "Bajo"}
PRIORITY_TO_SEVERITY = {v: k for k, v in SEVERITY_TO_PRIORITY.items()}

alert_queue = AlertPriorityQueue()
history = EventHistory(capacity=config.HISTORY_CAPACITY)
_lock = Lock()


def now_local() -> datetime:
    return datetime.now(ZoneInfo(config.TIMEZONE)).replace(tzinfo=None, microsecond=0)


def _event_query():
    return select(Evento).options(
        joinedload(Evento.sujeto),
        joinedload(Evento.tipo_evento),
        joinedload(Evento.camara).joinedload(Camara.ubicacion),
    )


def to_view(event: Evento) -> EventView:
    return EventView(
        id=event.id_evento,
        type=event.tipo_evento.nombre,
        subject=event.sujeto.nombre,
        location=event.camara.ubicacion.nombre,
        camera=event.camara.nombre,
        date=event.fecha.isoformat(),
        time=event.hora.strftime("%H:%M:%S"),
        priority=SEVERITY_TO_PRIORITY.get(event.tipo_evento.nivel_severidad, "Bajo"),
        status=event.estado,
        description=event.descripcion,
    )


def _entry(event: Evento) -> AlertEntry:
    return AlertEntry(
        event_id=event.id_evento,
        severity=event.tipo_evento.nivel_severidad,
        created_at=datetime.combine(event.fecha, event.hora),
    )


def rebuild_structures(db: Session) -> None:
    """On startup, reload the structures from the database (source of truth)."""
    with _lock:
        global alert_queue, history
        alert_queue = AlertPriorityQueue()
        history = EventHistory(capacity=config.HISTORY_CAPACITY)
        pending = db.scalars(_event_query().where(Evento.estado == "Pendiente")).unique()
        for event in pending:
            alert_queue.push(_entry(event))
        recent = db.scalars(
            _event_query()
            .order_by(Evento.fecha.desc(), Evento.hora.desc(), Evento.id_evento.desc())
            .limit(config.HISTORY_CAPACITY)
        ).unique()
        for event in recent:
            history.add_oldest(event.id_evento, to_view(event).model_dump())


def get_event(db: Session, event_id: int) -> Evento:
    event = db.scalars(_event_query().where(Evento.id_evento == event_id)).unique().first()
    if event is None:
        raise HTTPException(404, f"Evento {event_id} no existe")
    return event


def list_events(db: Session, q: str | None, prioridad: str | None, estado: str | None) -> list[EventView]:
    stmt = _event_query().order_by(Evento.fecha.desc(), Evento.hora.desc(), Evento.id_evento.desc())
    if estado:
        stmt = stmt.where(Evento.estado == estado)
    if prioridad and prioridad in PRIORITY_TO_SEVERITY:
        stmt = stmt.join(Evento.tipo_evento).where(
            TipoEvento.nivel_severidad == PRIORITY_TO_SEVERITY[prioridad]
        )
    views = [to_view(e) for e in db.scalars(stmt).unique()]
    if q:
        term = q.lower().strip()
        views = [
            v for v in views
            if any(term in str(value).lower() for value in (v.id, v.type, v.subject, v.location))
        ]
    return views


def create_event(db: Session, data: EventCreate) -> EventView:
    if db.get(Camara, data.id_camara) is None:
        raise HTTPException(404, f"Cámara {data.id_camara} no existe")
    if db.get(Sujeto, data.id_sujeto) is None:
        raise HTTPException(404, f"Sujeto {data.id_sujeto} no existe")
    if data.id_tipo_evento is not None:
        tipo = db.get(TipoEvento, data.id_tipo_evento)
    elif data.tipo_evento:
        tipo = db.scalar(select(TipoEvento).where(func.lower(TipoEvento.nombre) == data.tipo_evento.lower()))
    else:
        raise HTTPException(422, "Envía id_tipo_evento o tipo_evento")
    if tipo is None:
        raise HTTPException(404, "Tipo de evento no existe")

    stamp = now_local()
    event = Evento(
        fecha=stamp.date(), hora=stamp.time(), descripcion=data.descripcion, estado="Pendiente",
        id_sujeto=data.id_sujeto, id_tipo_evento=tipo.id_tipo_evento, id_camara=data.id_camara,
    )
    db.add(event)
    db.flush()
    db.add(Alerta(
        fecha=stamp.date(), hora=stamp.time(), estado="Pendiente",
        nivel=SEVERITY_TO_PRIORITY[tipo.nivel_severidad], id_evento=event.id_evento,
    ))
    db.commit()

    event = get_event(db, event.id_evento)
    view = to_view(event)
    with _lock:
        alert_queue.push(_entry(event))
        history.add_newest(event.id_evento, view.model_dump())
    return view


def review_event(db: Session, event_id: int) -> EventView:
    event = get_event(db, event_id)
    event.estado = "Revisado"
    for alert in db.scalars(select(Alerta).where(Alerta.id_evento == event_id)):
        alert.estado = "Atendida"
    db.commit()
    view = to_view(get_event(db, event_id))
    with _lock:
        alert_queue.remove(event_id)
        history.update(event_id, view.model_dump())
    return view


def pending_alerts(db: Session, limit: int) -> list[dict]:
    with _lock:
        top = alert_queue.top(limit)
    result = []
    for entry in top:
        event = get_event(db, entry.event_id)
        alert = db.scalar(
            select(Alerta).where(Alerta.id_evento == entry.event_id).order_by(Alerta.id_alerta.desc())
        )
        result.append({
            "id_alerta": alert.id_alerta if alert else 0,
            "nivel": alert.nivel if alert else SEVERITY_TO_PRIORITY[entry.severity],
            "estado": alert.estado if alert else "Pendiente",
            "event": to_view(event),
        })
    return result


def recent_events(limit: int) -> list[dict]:
    with _lock:
        return list(history.newest(limit))


def metrics(db: Session) -> dict:
    total = db.scalar(select(func.count(Evento.id_evento))) or 0
    alto = db.scalar(
        select(func.count(Evento.id_evento)).join(Evento.tipo_evento).where(TipoEvento.nivel_severidad == 3)
    ) or 0
    with _lock:
        pendientes = len(alert_queue)
    return {"total": total, "pendientes": pendientes, "alto": alto}
