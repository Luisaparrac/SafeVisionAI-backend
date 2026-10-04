from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config, services
from app.database import Base, SessionLocal, engine, get_db
from app.models import Camara, Sujeto, TipoEvento, Ubicacion, Usuario
from app.schemas import (AlertView, CamaraEstado, CamaraIn, EventCreate, EventView, Metrics,
                         SujetoIn, TipoEventoIn, UbicacionIn)
from app.seed import seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
        services.rebuild_structures(db)
    yield


app = FastAPI(title="SafeVision AI - Backend", version="1.0.0", lifespan=lifespan)

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


# ---------- Catalogs ----------
@app.get("/api/tipos-evento")
def list_event_types(db: Session = Depends(get_db)):
    return db.scalars(select(TipoEvento).order_by(TipoEvento.nivel_severidad.desc())).all()


@app.post("/api/tipos-evento", status_code=201)
def create_event_type(data: TipoEventoIn, db: Session = Depends(get_db)):
    item = TipoEvento(**data.model_dump())
    db.add(item)
    db.commit()
    return item


@app.get("/api/ubicaciones")
def list_locations(db: Session = Depends(get_db)):
    return db.scalars(select(Ubicacion)).all()


@app.post("/api/ubicaciones", status_code=201)
def create_location(data: UbicacionIn, db: Session = Depends(get_db)):
    if db.get(Usuario, data.id_usuario) is None:
        raise HTTPException(404, "Usuario no existe")
    item = Ubicacion(**data.model_dump())
    db.add(item)
    db.commit()
    return item


@app.get("/api/camaras")
def list_cameras(db: Session = Depends(get_db)):
    return db.scalars(select(Camara)).all()


@app.post("/api/camaras", status_code=201)
def create_camera(data: CamaraIn, db: Session = Depends(get_db)):
    if db.get(Ubicacion, data.id_ubicacion) is None:
        raise HTTPException(404, "Ubicación no existe")
    item = Camara(**data.model_dump())
    db.add(item)
    db.commit()
    return item


@app.patch("/api/camaras/{camera_id}/estado", dependencies=[Depends(require_iot_key)])
def update_camera_status(camera_id: int, data: CamaraEstado, db: Session = Depends(get_db)):
    camera = db.get(Camara, camera_id)
    if camera is None:
        raise HTTPException(404, "Cámara no existe")
    camera.estado = data.estado
    db.commit()
    return camera


@app.get("/api/sujetos")
def list_subjects(db: Session = Depends(get_db)):
    return db.scalars(select(Sujeto)).all()


@app.post("/api/sujetos", status_code=201)
def create_subject(data: SujetoIn, db: Session = Depends(get_db)):
    if db.get(Usuario, data.id_usuario) is None:
        raise HTTPException(404, "Usuario no existe")
    item = Sujeto(**data.model_dump())
    db.add(item)
    db.commit()
    return item
