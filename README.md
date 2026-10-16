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

## Ejecución local

Se necesita Python 3.12 (la versión de producción) o Docker.

### Con Docker

Levanta el backend con un PostgreSQL local que ya tiene la estructura de la base
(`tests/integration/schema.sql`) y datos de ejemplo ficticios
(`scripts/seed_dev.sql`). No hace falta ninguna credencial real.

```bash
cp .env.compose.example .env.compose     # valores solo de desarrollo
docker compose up --build
```

- API en http://localhost:8000 y documentación interactiva en http://localhost:8000/docs.
- La clave del módulo IoT es la de `.env.compose` (`IOT_API_KEY`).
- `docker compose down --volumes` borra la base local; al volver a subir se
  cargan otra vez el esquema y los datos de ejemplo.

La imagen (`Dockerfile`) instala solo `requirements.txt` y arranca con el mismo
comando que `render.yaml`, así que se comporta como producción.

### Con un entorno virtual

```bash
python -m venv .venv
.venv\Scripts\activate                 # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt    # app + herramientas de desarrollo
copy .env.example .env                 # macOS/Linux: cp .env.example .env
# Edita .env: DATABASE_URL e IOT_API_KEY (ver "Variables de entorno")
uvicorn safevision.adapters.inbound.http.app:app --app-dir src --reload
```

`DATABASE_URL` puede apuntar al PostgreSQL de `docker compose` o a la base del
equipo; en ese caso la IP pública de tu equipo debe estar permitida en el
firewall de la base. `.env` está en `.gitignore` y nunca se sube.

### Enviar un evento de prueba

`scripts/simulate_event.py` se comporta como el módulo IoT. No tiene URL ni
clave por defecto:

```bash
python scripts/simulate_event.py --url http://localhost:8000 --key TU_IOT_API_KEY
# o con variables de entorno: BACKEND_URL e IOT_API_KEY
python scripts/simulate_event.py --url http://localhost:8000 --key TU_IOT_API_KEY --tipo "Caída" --camara 1
```

## Variables de entorno

`src/safevision/config/settings.py` las lee al arrancar. Si falta una
obligatoria o un valor es inválido, el proceso se detiene con un mensaje claro
en lugar de fallar en la primera petición. `.env.example` tiene la lista con
marcadores.

| Variable | Obligatoria | Valor por defecto | Descripción |
|---|---|---|---|
| `DATABASE_URL` | Sí | — | URL de PostgreSQL, por ejemplo `postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require`. Los caracteres especiales de la contraseña van codificados (`!` → `%21`). `postgres://` también se acepta. |
| `IOT_API_KEY` | Sí | — | Clave que el módulo IoT envía en `X-API-Key` para crear eventos y actualizar cámaras. Usa un valor largo y aleatorio. |
| `FRONTEND_ORIGINS` | No | `http://localhost:5173` | Orígenes permitidos por CORS, separados por comas. |
| `TIMEZONE` | No | `America/Bogota` | Zona horaria en la que se muestran `date` y `time` y se leen los filtros por fecha. |
| `HISTORY_CAPACITY` | No | `100` | Eventos que guarda el historial reciente en memoria. |
| `DEDUP_WINDOW_SECONDS` | No | `60` | Segundos, desde la primera detección, en los que una detección repetida reutiliza el evento. `0` desactiva la deduplicación. |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` o `CRITICAL`. |

Las claves nunca aparecen en los registros: un filtro oculta credenciales de
URLs y valores de campos como `password` o `api_key`.

## Despliegue en Render

El servicio se define en `render.yaml` (plan gratuito, Python 3.12) y Render lo
despliega **sin Docker**:

| Paso | Valor |
|---|---|
| Construcción | `pip install -r requirements.txt` (solo dependencias de producción) |
| Arranque | `uvicorn safevision.adapters.inbound.http.app:app --app-dir src --host 0.0.0.0 --port $PORT` |
| Chequeo de salud | `GET /health` (no consulta la base, para que un corte de la base no reinicie el servicio) |

- **Cada push a `main` redespliega producción.** El trabajo se hace en ramas y
  entra a `main` por pull request con "Create a merge commit" (ver
  [CONTRIBUTING.md](CONTRIBUTING.md)).
- Variables: `DATABASE_URL` se define a mano en el panel de Render
  (`sync: false`); `IOT_API_KEY` la genera Render y se comparte con el equipo
  IoT; `FRONTEND_ORIGINS` y `TIMEZONE` completan la configuración. Ninguna se
  escribe en el repositorio.
- Las IP de salida del servicio (en Render: *Connect → Outbound*) deben estar
  permitidas en el firewall de la base.
- `GET /health/ready` responde 503 si la base no contesta; sirve para
  monitoreo externo.
- En el plan gratuito el servicio se duerme tras 15 minutos sin tráfico y tarda
  cerca de un minuto en despertar. El panel debe reconectar el WebSocket
  cuando eso pasa.
- El arranque se valida en CI: el paso de humo
  arranca el comando de `render.yaml` en un entorno con solo
  `requirements.txt`.

## Contrato de la API

Resumen de las rutas; la referencia completa, con parámetros, respuestas y
errores, está en [docs/api.md](docs/api.md) y en `/docs` (OpenAPI).

| Método | Ruta | Uso |
|---|---|---|
| GET | `/health` | Prueba de vida del hosting |
| GET | `/health/ready` | Comprueba también la base (503 si no responde) |
| GET | `/api/eventos?q=&prioridad=&estado=&camara_id=&desde=&hasta=&limit=&offset=` | Historial de eventos con filtros opcionales |
| GET | `/api/eventos/recientes?limit=` | Historial reciente (lista doblemente enlazada) |
| GET | `/api/eventos/{id}` | Detalle de un evento |
| POST | `/api/eventos` (`X-API-Key`) | Módulo IoT: registrar una detección |
| PATCH | `/api/eventos/{id}/revisar` | Panel: marcar como revisado |
| PATCH | `/api/eventos/{id}/falsa-alarma` | Panel: marcar como falsa alarma |
| GET | `/api/alertas/pendientes?limit=` | Alertas pendientes en orden de la cola de prioridad |
| PATCH | `/api/alertas/{id}/vista` | Panel: alerta vista (sigue pendiente) |
| GET | `/api/metricas` | Totales del panel |
| GET | `/api/estadisticas/tipos?desde=&hasta=` | Eventos por tipo |
| GET | `/api/estadisticas/camaras?desde=&hasta=` | Eventos por cámara |
| GET | `/api/tipos-evento`, `/api/ubicaciones`, `/api/camaras`, `/api/zonas`, `/api/sujetos` | Catálogos de solo lectura |
| PATCH | `/api/camaras/{id}/estado` (`X-API-Key`) | Módulo IoT: estado de una cámara |
| WS | `/ws/alertas` | Alertas nuevas y eventos revisados en vivo |

Los parámetros que no estaban en la primera versión (`camara_id`, `desde`,
`hasta`, `limit`, `offset`) son opcionales: sin ellos la respuesta es la misma
de siempre. Las pruebas de contrato (`tests/contract`) fijan las rutas, los
códigos y la forma JSON de las que usan el panel y el módulo IoT.

### Módulo IoT: registrar una detección

```http
POST /api/eventos
X-API-Key: <IOT_API_KEY>
Content-Type: application/json

{
  "camera_id": 1,
  "event_type": "Caída",
  "subject_id": null,
  "zone_id": 1,
  "detected_class": "person",
  "confidence": 0.93,
  "evidence_url": "https://example.com/evidencias/0001.jpg",
  "description": "opcional"
}
```

- `event_type` (nombre, sin distinguir mayúsculas) o `event_type_id`.
- `detected_class`: `person`, `dog`, `cat` u `other_animal`. `confidence`: 0 a 1.
- `zone_id` debe pertenecer a la cámara. `description` admite hasta 2000
  caracteres y `evidence_url` hasta 2048; el cuerpo completo, hasta 64 KiB.
- Responde **201** con el evento (`id, type, subject, location, camera, date,
  time, priority, status, description`) y crea su alerta con
  `level = severidad del tipo`.
- Una detección repetida (misma cámara, tipo y sujeto) dentro de
  `DEDUP_WINDOW_SECONDS` responde **201 con el evento ya registrado** y el
  encabezado `X-Duplicate: true`; no crea otra alerta.
- Errores: 401 sin clave o con clave incorrecta, 404 si no existe la cámara,
  el tipo, el sujeto o la zona, 422 si el cuerpo es inválido, 413 si es
  demasiado grande.

Estado de una cámara: `PATCH /api/camaras/{id}/estado` con
`{"status": "disconnected"}` (`active`, `inactive`, `disconnected` o
`maintenance`) y el mismo encabezado `X-API-Key`.

### Panel: alertas en vivo por WebSocket

Al conectarse a `/ws/alertas` el panel recibe mensajes JSON:

```json
{"tipo": "alerta_nueva", "alerta": {"id_alerta": 7, "nivel": "Alto", "estado": "Activa", "event": {"id": 7, "type": "Caída", "...": "..."}}}
{"tipo": "evento_revisado", "evento": {"id": 7, "status": "Revisado", "...": "..."}}
{"tipo": "ping"}
```

- `alerta` y `evento` tienen la misma forma que en `/api/alertas/pendientes` y
  `/api/eventos/{id}`.
- `ping` llega tras 25 s sin mensajes para mantener viva la conexión. El panel
  debe ignorar los tipos que no conozca y reconectarse si la conexión se cae.
- No pide clave, igual que las demás rutas de lectura del panel
  ([ADR 0006](docs/adr/0006-websocket-sin-autenticacion.md)).
