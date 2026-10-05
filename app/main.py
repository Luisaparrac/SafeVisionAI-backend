from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config, services
from app.database import SessionLocal, get_db
from app.models import Camera, EventType, Location, Subject, Zone
from app.schemas import AlertView, CameraStatus, EventCreate, EventView, Metrics


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Tables already exist in Azure: no create_all, no seed. Only load the structures.
    with SessionLocal() as db:
        services.rebuild_structures(db)
    yield


app = FastAPI(title="SafeVision AI - Backend", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.FRONTEND_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_iot_key(x_api_key: str | None = Header(default=None)) -> None:
    if config.IOT_API_KEY and x_api_key != config.IOT_API_KEY:
        raise HTTPException(401, "X-API-Key inválida")


@app.get("/")
def root():
    return {"servicio": "SafeVision AI backend", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- Events ----------
@app.get("/api/eventos", response_model=list[EventView])
def list_events(
    q: str | None = None,
    prioridad: str | None = Query(None, description="Alto, Medio o Bajo"),
    estado: str | None = Query(None, description="Pendiente o Revisado"),
    db: Session = Depends(get_db),
):
    return services.list_events(db, q, prioridad, estado)


@app.get("/api/eventos/recientes", response_model=list[EventView])
def recent_events(limit: int = Query(20, ge=1, le=100)):
    return services.recent_events(limit)


@app.get("/api/eventos/{event_id}", response_model=EventView)
def get_event(event_id: int, db: Session = Depends(get_db)):
    return services.to_view(services.get_event(db, event_id))


@app.post("/api/eventos", response_model=EventView, status_code=201, dependencies=[Depends(require_iot_key)])
def create_event(data: EventCreate, db: Session = Depends(get_db)):
    return services.create_event(db, data)


@app.patch("/api/eventos/{event_id}/revisar", response_model=EventView)
def review_event(event_id: int, db: Session = Depends(get_db)):
    return services.review_event(db, event_id)


# ---------- Alerts and metrics ----------
@app.get("/api/alertas/pendientes", response_model=list[AlertView])
def pending_alerts(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    return services.pending_alerts(db, limit)


@app.get("/api/metricas", response_model=Metrics)
def metrics(db: Session = Depends(get_db)):
    return services.metrics(db)


# ---------- Catalogs (read only) ----------
@app.get("/api/tipos-evento")
def list_event_types(db: Session = Depends(get_db)):
    rows = db.scalars(select(EventType).order_by(EventType.severity_level.desc(), EventType.name))
    return [
        {"event_type_id": t.event_type_id, "name": t.name, "description": t.description,
         "severity_level": t.severity_level, "priority": services.priority_label(t.severity_level)}
        for t in rows
    ]


@app.get("/api/ubicaciones")
def list_locations(db: Session = Depends(get_db)):
    return [
        {"location_id": l.location_id, "name": l.name, "description": l.description}
        for l in db.scalars(select(Location).order_by(Location.location_id))
    ]


@app.get("/api/camaras")
def list_cameras(db: Session = Depends(get_db)):
    return [
        {"camera_id": c.camera_id, "name": c.name, "ip_address": str(c.ip_address),
         "status": c.status, "location_id": c.location_id}
        for c in db.scalars(select(Camera).order_by(Camera.camera_id))
    ]


@app.patch("/api/camaras/{camera_id}/estado", dependencies=[Depends(require_iot_key)])
def update_camera_status(camera_id: int, data: CameraStatus, db: Session = Depends(get_db)):
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(404, "Cámara no existe")
    camera.status = data.status
    db.commit()
    return {"camera_id": camera.camera_id, "status": camera.status}


@app.get("/api/zonas")
def list_zones(db: Session = Depends(get_db)):
    return [
        {"zone_id": z.zone_id, "name": z.name, "description": z.description,
         "coordinates": z.coordinates, "is_active": z.is_active, "camera_id": z.camera_id}
        for z in db.scalars(select(Zone).order_by(Zone.zone_id))
    ]


@app.get("/api/sujetos")
def list_subjects(db: Session = Depends(get_db)):
    return [
        {"subject_id": s.subject_id, "name": s.name, "subject_type": s.subject_type,
         "description": s.description}
        for s in db.scalars(select(Subject).order_by(Subject.subject_id))
    ]
