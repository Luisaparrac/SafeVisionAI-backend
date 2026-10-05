"""System logic: keeps the Azure database and the in-memory structures in sync."""
from datetime import datetime
from threading import Lock
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app import config
from app.models import Alert, Camera, Event, EventType, Subject, Zone
from app.schemas import EventCreate, EventView
from app.structures import AlertPriorityQueue, EventHistory
from app.structures.priority_queue import AlertEntry

TZ = ZoneInfo(config.TIMEZONE)

# Database values (English) -> labels shown in the frontend (Spanish).
OPEN_EVENT_STATUSES = ("pending", "in_review")
CLOSED_EVENT_STATUSES = ("resolved", "false_alarm")
OPEN_ALERT_STATUSES = ("active", "seen")
SEVERITIES_BY_PRIORITY = {"Alto": (3, 4), "Medio": (2,), "Bajo": (1,)}
ALERT_STATUS_LABELS = {"active": "Activa", "seen": "Vista", "resolved": "Atendida", "dismissed": "Descartada"}
CLASS_LABELS = {"person": "Persona", "dog": "Perro", "cat": "Gato", "other_animal": "Animal"}

alert_queue = AlertPriorityQueue()
history = EventHistory(capacity=config.HISTORY_CAPACITY)
_lock = Lock()


def priority_label(severity: int) -> str:
    """Severity 1..4 in the DB; the frontend shows three levels."""
    if severity >= 3:
        return "Alto"
    return "Medio" if severity == 2 else "Bajo"


def status_label(status: str) -> str:
    return "Pendiente" if status in OPEN_EVENT_STATUSES else "Revisado"


def _event_query():
    return select(Event).options(
        joinedload(Event.subject),
        joinedload(Event.event_type),
        joinedload(Event.zone),
        joinedload(Event.camera).joinedload(Camera.location),
    )


def to_view(event: Event) -> EventView:
    local = event.occurred_at.astimezone(TZ)
    if event.subject is not None:
        subject = event.subject.name
    else:
        subject = f"{CLASS_LABELS.get(event.detected_class, 'Sujeto')} sin identificar"
    location = event.camera.location.name
    if event.zone is not None:
        location = f"{location} · {event.zone.name}"
    return EventView(
        id=event.event_id,
        type=event.event_type.name,
        subject=subject,
        location=location,
        camera=event.camera.name,
        date=local.date().isoformat(),
        time=local.strftime("%H:%M:%S"),
        priority=priority_label(event.event_type.severity_level),
        status=status_label(event.status),
        description=event.description,
    )


def _entry(event: Event) -> AlertEntry:
    return AlertEntry(
        event_id=event.event_id,
        severity=event.event_type.severity_level,
        created_at=event.occurred_at,
    )


def rebuild_structures(db: Session) -> None:
    """On startup, reload the structures from the database (source of truth)."""
    global alert_queue, history
    queue = AlertPriorityQueue()
    recent = EventHistory(capacity=config.HISTORY_CAPACITY)
    for event in db.scalars(_event_query().where(Event.status.in_(OPEN_EVENT_STATUSES))).unique():
        queue.push(_entry(event))
    rows = db.scalars(
        _event_query().order_by(Event.occurred_at.desc(), Event.event_id.desc()).limit(config.HISTORY_CAPACITY)
    ).unique()
    for event in rows:
        recent.add_oldest(event.event_id, to_view(event).model_dump())
    with _lock:
        alert_queue, history = queue, recent


def get_event(db: Session, event_id: int) -> Event:
    event = db.scalars(_event_query().where(Event.event_id == event_id)).unique().first()
    if event is None:
        raise HTTPException(404, f"Evento {event_id} no existe")
    return event


def list_events(db: Session, q: str | None, prioridad: str | None, estado: str | None) -> list[EventView]:
    stmt = _event_query().order_by(Event.occurred_at.desc(), Event.event_id.desc())
    if estado == "Pendiente":
        stmt = stmt.where(Event.status.in_(OPEN_EVENT_STATUSES))
    elif estado == "Revisado":
        stmt = stmt.where(Event.status.in_(CLOSED_EVENT_STATUSES))
    if prioridad in SEVERITIES_BY_PRIORITY:
        stmt = stmt.join(Event.event_type).where(EventType.severity_level.in_(SEVERITIES_BY_PRIORITY[prioridad]))
    views = [to_view(e) for e in db.scalars(stmt).unique()]
    if q:
        term = q.lower().strip()
        views = [
            v for v in views
            if any(term in str(value).lower() for value in (v.id, v.type, v.subject, v.location))
        ]
    return views


def create_event(db: Session, data: EventCreate) -> EventView:
    if db.get(Camera, data.camera_id) is None:
        raise HTTPException(404, f"Cámara {data.camera_id} no existe")
    if data.subject_id is not None and db.get(Subject, data.subject_id) is None:
        raise HTTPException(404, f"Sujeto {data.subject_id} no existe")
    if data.zone_id is not None:
        zone = db.get(Zone, data.zone_id)
        if zone is None or zone.camera_id != data.camera_id:
            raise HTTPException(404, f"Zona {data.zone_id} no existe para la cámara {data.camera_id}")
    if data.event_type_id is not None:
        event_type = db.get(EventType, data.event_type_id)
    elif data.event_type:
        event_type = db.scalar(select(EventType).where(func.lower(EventType.name) == data.event_type.lower()))
    else:
        raise HTTPException(422, "Envía event_type_id o event_type")
    if event_type is None:
        raise HTTPException(404, "Tipo de evento no existe")

    event = Event(
        description=data.description,
        status="pending",
        detected_class=data.detected_class,
        confidence=data.confidence,
        evidence_url=data.evidence_url,
        subject_id=data.subject_id,
        event_type_id=event_type.event_type_id,
        camera_id=data.camera_id,
        zone_id=data.zone_id,
    )
    db.add(event)
    db.flush()
    db.add(Alert(level=event_type.severity_level, status="active", event_id=event.event_id))
    db.commit()

    event = get_event(db, event.event_id)
    view = to_view(event)
    with _lock:
        alert_queue.push(_entry(event))
        history.add_newest(event.event_id, view.model_dump())
    return view


def review_event(db: Session, event_id: int) -> EventView:
    event = get_event(db, event_id)
    if event.status in OPEN_EVENT_STATUSES:
        event.status = "resolved"
        db.execute(
            update(Alert)
            .where(Alert.event_id == event_id, Alert.status.in_(OPEN_ALERT_STATUSES))
            .values(status="resolved", attended_at=func.now())
        )
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
            select(Alert).where(Alert.event_id == entry.event_id).order_by(Alert.alert_id.desc())
        )
        result.append({
            "id_alerta": alert.alert_id if alert else 0,
            "nivel": priority_label(alert.level if alert else entry.severity),
            "estado": ALERT_STATUS_LABELS.get(alert.status, alert.status) if alert else "Activa",
            "event": to_view(event),
        })
    return result


def recent_events(limit: int) -> list[dict]:
    with _lock:
        return list(history.newest(limit))


def metrics(db: Session) -> dict:
    total = db.scalar(select(func.count(Event.event_id))) or 0
    alto = db.scalar(
        select(func.count(Event.event_id)).join(Event.event_type).where(EventType.severity_level >= 3)
    ) or 0
    with _lock:
        pendientes = len(alert_queue)
    return {"total": total, "pendientes": pendientes, "alto": alto}


def to_local_iso(value: datetime | None) -> str | None:
    return value.astimezone(TZ).isoformat() if value else None
