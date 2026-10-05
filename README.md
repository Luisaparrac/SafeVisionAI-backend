# SafeVision AI — Backend

REST API in Python (FastAPI) for SafeVision AI. Reads and writes events and alerts in the
team's Azure PostgreSQL database, receives detections from the IoT module, and serves the
data to the frontend.

## Data structures

| Structure | File | Role in the system |
|---|---|---|
| Max-heap priority queue with position index | `app/structures/priority_queue.py` | Orders pending alerts by severity, then by age. Reviewing an alert removes it in O(log n). |
| Bounded doubly linked list | `app/structures/event_history.py` | Recent event history (newest at head). Insert O(1), drop oldest O(1), update by id O(1). |

The database is the source of truth; both structures are rebuilt from it on startup and
kept in sync on every create/review.

## Database

The backend connects to the team's **Azure PostgreSQL** database (`safevisionai`), whose
8 tables (`users`, `locations`, `cameras`, `zones`, `subjects`, `event_types`, `events`,
`alerts`) are created by `01_tables.sql` and owned by `safevision_admin`. The backend
**never creates or alters tables** and inserts no seed data: it connects as
`app_safevision`, which only has SELECT/INSERT/UPDATE/DELETE.

Database values are in English; the API translates them to the Spanish labels the
frontend uses:

| Database | Frontend |
|---|---|
| `events.status` pending / in_review | Pendiente |
| `events.status` resolved / false_alarm | Revisado |
| `event_types.severity_level` 3–4 / 2 / 1 | Alto / Medio / Bajo |

Reviewing an event sets `events.status = 'resolved'` and closes its open alerts
(`status = 'resolved'`, `attended_at = now()`).

## Run locally

Your public IP must be allowed in the Azure firewall first.

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env             # macOS/Linux: cp .env.example .env
# edit .env with the real password (URL-encoded: ! -> %21)
uvicorn app.main:app --reload
```

Interactive docs: http://localhost:8000/docs

Send a test event (simulates the IoT module):

```bash
python scripts/simulate_event.py --key YOUR_IOT_API_KEY
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
| `DATABASE_URL` | Azure PostgreSQL URL with `?sslmode=require`. Required. |
| `IOT_API_KEY` | Key required to create events. Empty = no check (local only). |
| `FRONTEND_ORIGINS` | Allowed CORS origins, comma separated. |
| `TIMEZONE` | Default `America/Bogota`. |

## Deploy on Render

1. Push to GitHub; Render redeploys automatically.
2. In the service's environment variables, set `DATABASE_URL` to the Azure URL.
3. Add the service's outbound IPs (Connect → Outbound) as firewall rules in Azure.

Free plan note: the service sleeps after 15 minutes without traffic and takes about a
minute to wake up.
