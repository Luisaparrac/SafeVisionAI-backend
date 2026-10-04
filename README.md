# SafeVision AI — Backend

REST API in Python (FastAPI) for SafeVision AI. Stores events and alerts in PostgreSQL
(the 7 tables from the project documentation), receives detections from the IoT module,
and serves the data to the frontend.

## Data structures

| Structure | File | Role in the system |
|---|---|---|
| Max-heap priority queue with position index | `app/structures/priority_queue.py` | Orders pending alerts by severity, then by age. Reviewing an alert removes it in O(log n). |
| Bounded doubly linked list | `app/structures/event_history.py` | Recent event history (newest at head). Insert O(1), drop oldest O(1), update by id O(1). |

The database is the source of truth; both structures are rebuilt from it on startup and
kept in sync on every create/review.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Without `DATABASE_URL` it uses a local SQLite file. Interactive docs: http://localhost:8000/docs

Send a test event (simulates the IoT module):

```bash
python scripts/simulate_event.py --tipo "Caída"
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
| GET/POST | `/api/tipos-evento`, `/api/ubicaciones`, `/api/camaras`, `/api/sujetos` | Catalogs |
| PATCH | `/api/camaras/{id}/estado` (header `X-API-Key`) | IoT module (camera heartbeat) |

### IoT contract

```http
POST /api/eventos
X-API-Key: <IOT_API_KEY>
Content-Type: application/json

{ "id_camara": 1, "id_sujeto": 1, "tipo_evento": "Caída", "descripcion": "optional" }
```

`tipo_evento` (name) or `id_tipo_evento` (id). The server sets date and time.

## Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL URL. Empty = local SQLite. |
| `IOT_API_KEY` | Key required to create events. Empty = no check (local only). |
| `FRONTEND_ORIGINS` | Allowed CORS origins, comma separated. |
| `TIMEZONE` | Default `America/Bogota`. |
| `SEED_DEMO_EVENTS` | `true` seeds 5 sample events on the first start. |

## Deploy on Render

1. Push this repo to GitHub.
2. Render → New → Blueprint → select this repo. `render.yaml` creates the web service and the database.
3. When asked, set `FRONTEND_ORIGINS` to the Vercel URL (e.g. `https://safevisionai.vercel.app`).
4. After deploy, copy `IOT_API_KEY` from the service's Environment tab for the IoT module.

Free plan notes: the service sleeps after 15 minutes without traffic and takes about a
minute to wake up; the free database expires 30 days after creation.
