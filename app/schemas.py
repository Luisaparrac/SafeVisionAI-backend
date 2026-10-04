from pydantic import BaseModel, Field


class EventView(BaseModel):
    """Exactly the shape the frontend's RiskEvent uses."""
    id: int
    type: str
    subject: str
    location: str
    camera: str
    date: str
    time: str
    priority: str   # Alto / Medio / Bajo
    status: str     # Pendiente / Revisado
    description: str | None = None


class AlertView(BaseModel):
    id_alerta: int
    nivel: str
    estado: str
    event: EventView


class EventCreate(BaseModel):
    """What the IoT module sends when it detects something."""
    id_camara: int
    id_sujeto: int
    id_tipo_evento: int | None = None
    tipo_evento: str | None = Field(None, description="Type name, alternative to id_tipo_evento")
    descripcion: str | None = None


class Metrics(BaseModel):
    total: int
    pendientes: int
    alto: int


class UbicacionIn(BaseModel):
    nombre: str
    descripcion: str | None = None
    id_usuario: int


class CamaraIn(BaseModel):
    nombre: str
    direccion_ip: str | None = None
    estado: str = "Sin conexión"
    id_ubicacion: int


class CamaraEstado(BaseModel):
    estado: str


class SujetoIn(BaseModel):
    nombre: str
    tipo: str
    descripcion: str | None = None
    id_usuario: int


class TipoEventoIn(BaseModel):
    nombre: str
    descripcion: str | None = None
    nivel_severidad: int = Field(ge=1, le=3)
