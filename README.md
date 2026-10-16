# SafeVision AI — Backend

API REST de SafeVision AI, escrita en Python con FastAPI. Recibe las detecciones
del módulo IoT (cámara con YOLO Pose), las guarda como eventos y alertas en la
base PostgreSQL del equipo y sirve al panel web los eventos, las alertas
pendientes en orden de urgencia, métricas, estadísticas y catálogos. Las alertas
nuevas también llegan al panel en vivo por WebSocket.

Proyecto del curso **Estructuras de Datos**: la cola de alertas, el historial
reciente y la ventana de deduplicación usan estructuras implementadas a mano.

## Arquitectura

El código sigue la **arquitectura hexagonal** (puertos y adaptadores) y vive en
`src/safevision/`. Las dependencias apuntan siempre hacia el centro:
`adapters → application → domain`.

```
src/safevision/
├── domain/          Núcleo puro, sin frameworks
│   ├── model/       Entidades (Event, Alert, Camera…) y value objects (Severity, EventStatus…)
│   └── structures/  Heap con índice, lista doble acotada y cola enlazada
├── application/     Casos de uso, puertos (typing.Protocol) y servicios en memoria
├── adapters/
│   ├── inbound/http/        FastAPI: rutas, esquemas, seguridad, WebSocket, middlewares
│   └── outbound/persistence/ SQLAlchemy: modelos ORM, mappers, repositorios, unidad de trabajo
├── config/settings.py      Configuración desde variables de entorno (falla al arrancar si falta algo)
└── bootstrap.py            Raíz de composición: conecta cada puerto con su adaptador
```

- **domain** no importa FastAPI, Pydantic ni SQLAlchemy; una prueba de
  arquitectura (`tests/architecture`) lo verifica recorriendo los imports.
- **application** define lo que necesita del exterior como puertos
  (`EventRepository`, `UnitOfWork`, `Clock`, `AlertNotifier`, `ReadinessProbe`)
  y orquesta el dominio en un caso de uso por archivo.
- **adapters** implementan esos puertos (PostgreSQL, reloj del sistema,
  WebSocket) y exponen los casos de uso por HTTP.

El detalle, con diagramas, está en [docs/arquitectura.md](docs/arquitectura.md).

## Estructuras de datos

| Estructura | Archivo | Uso |
|---|---|---|
| Max-heap con índice de posiciones | `domain/structures/alert_priority_queue.py` | Alertas pendientes: primero la más severa y, si empatan, la más antigua. Quitar la de un evento revisado cuesta O(log n). |
| Lista doblemente enlazada acotada | `domain/structures/event_history.py` | Historial reciente de eventos (`/api/eventos/recientes`). Insertar, descartar el más antiguo y actualizar por id cuestan O(1). |
| Cola FIFO enlazada | `domain/structures/linked_queue.py` | Ventana deslizante del deduplicador de detecciones repetidas del IoT. |

La base de datos es la fuente de verdad: estas estructuras son índices en
memoria que se reconstruyen desde ella al arrancar. La justificación y las
complejidades están en [docs/estructuras.md](docs/estructuras.md).

## Base de datos

El backend usa la base PostgreSQL existente del equipo, con 8 tablas (`users`,
`locations`, `cameras`, `zones`, `subjects`, `event_types`, `events`, `alerts`)
que pertenecen a otro rol. **Nunca crea, altera ni borra tablas**: su usuario
solo puede leer y escribir filas. `tests/integration/schema.sql` reproduce la
estructura (sin datos) para las pruebas y el entorno local.

Los valores de la base están en inglés; la API los traduce a las etiquetas que
muestra el panel:

| Base de datos | Panel |
|---|---|
| `events.status` pending / in_review | Pendiente |
| `events.status` resolved / false_alarm | Revisado |
| `event_types.severity_level` 3–4 / 2 / 1 | Alto / Medio / Bajo |

## Run locally

Your public IP must be allowed in the database firewall first.

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env             # macOS/Linux: cp .env.example .env
# edit .env with your connection data (password URL-encoded: ! -> %21)
uvicorn safevision.adapters.inbound.http.app:app --app-dir src --reload
```

Interactive docs: http://localhost:8000/docs

Send a test event (simulates the IoT module):

```bash
python scripts/simulate_event.py --url http://localhost:8000 --key YOUR_IOT_API_KEY
```

## Endpoints

| Method | Path | Used by |
|---|---|---|
| GET | `/health` | Render health check |
| GET | `/api/eventos?q=&prioridad=&estado=` | Frontend (history table) |
| GET | `/api/eventos/recientes?limit=` | Frontend (linked-list history) |
| GET | `/api/eventos/{id}` | Frontend |
| POST | `/api/eventos` (header `X-API-Key`) | IoT module |
| PATCH | `/api/eventos/{id}/revisar` | Frontend (review button) |
| GET | `/api/alertas/pendientes?limit=` | Frontend (priority-queue order) |
| GET | `/api/metricas` | Frontend (metric cards) |
| GET | `/api/tipos-evento`, `/api/ubicaciones`, `/api/camaras`, `/api/zonas`, `/api/sujetos` | Catalogs (read only) |
| PATCH | `/api/camaras/{id}/estado` (header `X-API-Key`) | IoT module (camera status) |

### IoT contract

```http
POST /api/eventos
X-API-Key: <IOT_API_KEY>
Content-Type: application/json

{
  "camera_id": 1,
  "event_type": "Caída",
  "subject_id": null,
  "zone_id": null,
  "detected_class": "person",
  "confidence": 0.93,
  "evidence_url": null,
  "description": "optional"
}
```

`event_type` (name, case-insensitive) or `event_type_id`. `detected_class` is one of
person, dog, cat, other_animal. `confidence` is 0–1. `zone_id` must belong to the camera.
The database sets `occurred_at`; an alert with `level = severity_level` is created too.

Camera status: `PATCH /api/camaras/{id}/estado` with `{"status": "active"}`
(active, inactive, disconnected, maintenance).

## Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL URL with `?sslmode=require`. Required. |
| `IOT_API_KEY` | Key required to create events and update camera status. Required: the app does not start without it. |
| `FRONTEND_ORIGINS` | Allowed CORS origins, comma separated. |
| `TIMEZONE` | Default `America/Bogota`. |

## Deploy on Render

1. Push to GitHub; Render redeploys automatically.
2. In the service's environment variables, set `DATABASE_URL` to the database URL.
3. Add the service's outbound IPs (Connect → Outbound) as database firewall rules.

Free plan note: the service sleeps after 15 minutes without traffic and takes about a
minute to wake up.
