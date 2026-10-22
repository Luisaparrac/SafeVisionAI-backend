# SafeVision AI — Backend

API REST de SafeVision AI, escrita en Python con FastAPI. Recibe las detecciones
del módulo IoT (cámara con YOLO Pose), las guarda como eventos y alertas en la
base PostgreSQL del equipo y sirve al panel web los eventos, las alertas
pendientes en orden de urgencia, métricas, estadísticas y catálogos. Las alertas
nuevas también llegan al panel en vivo por WebSocket. El panel inicia sesión con
los usuarios de la base y una cookie firmada.

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
│   ├── inbound/http/        FastAPI: rutas, esquemas, sesiones, seguridad, WebSocket, middlewares
│   └── outbound/            SQLAlchemy (ORM, mappers, repositorios, unidad de trabajo), reloj y PBKDF2
├── config/settings.py      Configuración desde variables de entorno (falla al arrancar si falta algo)
└── bootstrap.py            Raíz de composición: conecta cada puerto con su adaptador
```

- **domain** no importa FastAPI, Pydantic ni SQLAlchemy; una prueba de
  arquitectura (`tests/architecture`) lo verifica recorriendo los imports.
- **application** define lo que necesita del exterior como puertos
  (`EventRepository`, `UserRepository`, `UnitOfWork`, `Clock`, `PasswordHasher`,
  `AlertNotifier`, `ReadinessProbe`)
  y orquesta el dominio en un caso de uso por archivo.
- **adapters** implementan esos puertos (PostgreSQL, reloj del sistema,
  WebSocket) y exponen los casos de uso por HTTP.

El detalle, con diagramas, está en [docs/arquitectura.md](docs/arquitectura.md).

## Estructuras de datos

| Estructura | Archivo | Uso |
|---|---|---|
| Max-heap con índice de posiciones | `domain/structures/alert_priority_queue.py` | Alertas pendientes: primero la más severa y, si empatan, la más antigua. Quitar la de un evento revisado cuesta O(log n). |
| Lista doblemente enlazada acotada | `domain/structures/event_history.py` | Historial reciente de eventos (`/api/eventos/recientes`). Insertar, descartar el más antiguo y actualizar por id cuestan O(1). |
| Cola FIFO enlazada | `domain/structures/linked_queue.py` | Ventanas deslizantes del deduplicador de detecciones repetidas del IoT y del límite de inicios de sesión fallidos. |

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
- El usuario de ejemplo (`dev@example.com`) no tiene un hash válido: para
  iniciar sesión, genera uno (ver [Cuentas del panel](#cuentas-del-panel)) y
  aplícalo con
  `docker compose exec db psql -U safevision -d safevision_dev -c "UPDATE users SET password_hash = '<hash>' WHERE email = 'dev@example.com'"`.
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
# Edita .env: DATABASE_URL, IOT_API_KEY y SESSION_SECRET (ver "Variables de entorno")
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
| `IOT_API_KEY` | Sí | — | Clave que el módulo IoT envía en `X-API-Key` para crear eventos y actualizar cámaras (también lee los catálogos). Usa un valor largo y aleatorio. |
| `SESSION_SECRET` | Sí | — | Clave que firma las cookies de sesión (HMAC-SHA256). Al menos 32 caracteres aleatorios; cambiarla cierra todas las sesiones. |
| `FRONTEND_ORIGINS` | No | `http://localhost:5173` | Orígenes del panel, separados por comas: CORS con credenciales y protección CSRF. No admite `*`. |
| `TIMEZONE` | No | `America/Bogota` | Zona horaria en la que se muestran `date` y `time` y se leen los filtros por fecha. |
| `HISTORY_CAPACITY` | No | `100` | Eventos que guarda el historial reciente en memoria. |
| `DEDUP_WINDOW_SECONDS` | No | `60` | Segundos, desde la primera detección, en los que una detección repetida reutiliza el evento. `0` desactiva la deduplicación. |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` o `CRITICAL`. |
| `SESSION_TTL_HOURS` | No | `8` | Horas que dura una sesión desde el inicio de sesión. |
| `SESSION_COOKIE_SAMESITE` | No | `none` | `none` si el panel llama a la API desde otro sitio; `lax` si el hosting del frontend reescribe `/api` hacia el backend (ver [Integración con el frontend](#integración-con-el-frontend)). |

Las claves nunca aparecen en los registros: un filtro oculta credenciales de
URLs y valores de campos como `password` o `api_key`.

## Cuentas del panel

Los usuarios son las filas de la tabla `users`; el backend no crea cuentas. La
contraseña se guarda en `users.password_hash` con PBKDF2-SHA256
(`pbkdf2_sha256$600000$<sal>$<hash>`). Para asignar o cambiar una contraseña:

```bash
python scripts/hash_password.py      # la pide dos veces sin mostrarla e imprime el hash
```

El script no se conecta a ninguna base. El hash se aplica a mano, por ejemplo
desde pgAdmin:

```sql
UPDATE users SET password_hash = '<hash>' WHERE user_id = <id>;
```

Un hash en otro formato nunca valida: esa cuenta recibe 401 hasta que se le
asigna uno nuevo así. El correo de cada cuenta debe ser único (la columna no lo
garantiza): si dos usuarios lo comparten, ninguno puede iniciar sesión.

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
- Variables: `DATABASE_URL` y `SESSION_SECRET` se definen a mano en el panel
  de Render (`sync: false`); `IOT_API_KEY` la genera Render y se comparte con
  el equipo IoT; `FRONTEND_ORIGINS`, `TIMEZONE` y `SESSION_COOKIE_SAMESITE`
  completan la configuración. Ningún secreto se escribe en el repositorio. Sin
  `SESSION_SECRET` el servicio no arranca: hay que definirla **antes** de
  desplegar esta versión.
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
| POST | `/api/auth/login` | Iniciar sesión (cookie `sv_session`) |
| GET | `/api/auth/me` | Usuario actual de la sesión |
| POST | `/api/auth/logout` | Cerrar sesión |
| GET | `/api/auth/ws-ticket` | Ticket de 60 s para el WebSocket |
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

Todas las rutas de `/api`, salvo iniciar y cerrar sesión, exigen la cookie de
sesión o la `X-API-Key`; las marcadas con `X-API-Key` exigen siempre la clave.
`/health`, `/health/ready`, `/`, `/docs` y `/openapi.json` son públicas.

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
  time, occurred_at, priority, status, description`) y crea su alerta con
  `level = severidad del tipo`.
- Una detección repetida (misma cámara, tipo y sujeto) dentro de
  `DEDUP_WINDOW_SECONDS` responde **201 con el evento ya registrado** y el
  encabezado `X-Duplicate: true`; no crea otra alerta.
- Errores: 401 sin clave o con clave incorrecta, 404 si no existe la cámara,
  el tipo, el sujeto o la zona, 422 si el cuerpo es inválido, 413 si es
  demasiado grande.

Estado de una cámara: `PATCH /api/camaras/{id}/estado` con
`{"status": "disconnected"}` (`active`, `inactive`, `disconnected` o
`maintenance`) y el mismo encabezado `X-API-Key`. Con esa clave el módulo
también puede leer los catálogos (`GET /api/camaras`, `/api/tipos-evento`…).

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
- Se abre con un ticket (`/ws/alertas?ticket=...`, de
  `GET /api/auth/ws-ticket`), con la cookie de sesión desde un origen del panel
  o con `X-API-Key`. Sin credenciales se cierra con el código 4401
  ([ADR 0007](docs/adr/0007-sesion-con-cookie-firmada.md)).

## Integración con el frontend

Contrato completo en [docs/api.md](docs/api.md#autenticación). Lo que el panel
necesita:

1. **Todas las peticiones con `credentials: "include"`** (ya lo hace). El
   backend responde `Access-Control-Allow-Credentials: true` y el origen
   exacto, solo para los orígenes de `FRONTEND_ORIGINS`.
2. **Formulario de login** → `POST /api/auth/login` con
   `{"email", "password"}`. 200 trae `{"authenticated": true, "user": {...}}`;
   401 y 429 traen el mensaje en `detail`.
3. **Al cargar** → `GET /api/auth/me`: 200 es una sesión válida, 401 muestra
   el login. Un 401 en cualquier otra ruta significa lo mismo.
4. **Cerrar sesión** → `POST /api/auth/logout` (204, sin cuerpo).
5. **WebSocket** → pedir `GET /api/auth/ws-ticket` y abrir
   `/ws/alertas?ticket=<ticket>` antes de que pasen 60 s; si se cierra con
   4401, volver al login.

El panel no tiene que enviar ningún token: la cookie es `HttpOnly` y la pone y
la envía el navegador.

### Opcional: la API bajo el dominio del frontend

Algunos navegadores (Safari, y cualquiera con las cookies de terceros
bloqueadas) no envían una cookie de otro sitio aunque sea `SameSite=None`. La
solución es que el hosting del frontend reescriba las rutas del backend bajo su
propio dominio, para que la cookie sea del mismo sitio. En su archivo de
configuración de *rewrites*, con `BACKEND_HOST` como marcador:

```json
{
  "rewrites": [
    {"source": "/api/:path*", "destination": "https://BACKEND_HOST/api/:path*"},
    {"source": "/openapi.json", "destination": "https://BACKEND_HOST/openapi.json"},
    {"source": "/health", "destination": "https://BACKEND_HOST/health"}
  ]
}
```

Después:

- el panel llama a rutas relativas (`/api/eventos`, `/api/auth/login`…);
- en el backend, `SESSION_COOKIE_SAMESITE=lax` y `FRONTEND_ORIGINS` con la URL
  del frontend (las peticiones siguen llegando con su `Origin`);
- el WebSocket no pasa por la reescritura: sigue usando el ticket contra la URL
  del backend.

## Calidad

| Herramienta | Qué verifica | Cómo correrla |
|---|---|---|
| pytest | Pruebas unitarias, de arquitectura, de contrato e integración | `pytest` |
| ruff | Estilo (E, F, I, UP, B, SIM) y formato | `ruff check .` y `ruff format --check .` |
| mypy | Tipos de `domain` y `application` en modo estricto | `mypy` |
| vulture | Código muerto en `src` y `scripts` (las pruebas no cuentan como uso) | `vulture` |
| pytest-cov | Cobertura de ramas; el CI exige al menos 95 % | `pytest --cov` |

**Tipos de prueba** (`tests/`):

- `unit/`: dominio, estructuras, casos de uso con repositorios en memoria y
  adaptador HTTP con `TestClient`. No usan base de datos.
- `architecture/`: el dominio y la aplicación no importan frameworks ni capas
  exteriores, y el código no ejecuta DDL.
- `contract/`: las mismas peticiones contra la app con adaptadores en memoria
  y con PostgreSQL; fijan el contrato que usan el panel y el módulo IoT.
- `integration/`: repositorios y casos de uso sobre PostgreSQL. Usan **solo**
  `TEST_DATABASE_URL`, que debe apuntar a `localhost` y a una base cuyo nombre
  termine en `_test` (si no, fallan sin ejecutar nada); sin la variable se
  omiten. Recrean las tablas de `tests/integration/schema.sql`.
- `smoke/`: arranca uvicorn con el comando de `render.yaml` y prueba las rutas
  principales, el inicio y cierre de sesión, CORS con credenciales y el
  WebSocket (`pytest -m smoke`).

**Integración continua** (`.github/workflows/ci.yml`, en cada push y pull
request):

1. Job `test`, con Python 3.12 y un PostgreSQL 16 desechable: ruff, vulture,
   mypy, pytest con cobertura (se publica `coverage.xml`) y la prueba de humo
   desde un entorno que solo instala `requirements.txt`.
2. Job `docker`: construye la imagen, levanta `docker compose` y comprueba
   `/health`, `/health/ready`, los datos de ejemplo y que el servidor no corre
   como root.

**pre-commit**: `.pre-commit-config.yaml` corre ruff, vulture, mypy y pytest
antes de cada commit con las herramientas de `requirements-dev.txt`. Se activa
con `pre-commit install` dentro del entorno virtual.

## Documentación

- [docs/arquitectura.md](docs/arquitectura.md): capas, puertos, adaptadores y flujo de una detección.
- [docs/estructuras.md](docs/estructuras.md): estructuras de datos, complejidades y uso.
- [docs/api.md](docs/api.md): referencia completa de la API.
- [docs/adr/](docs/adr/): decisiones de arquitectura.
- [CHANGELOG.md](CHANGELOG.md), [CONTRIBUTING.md](CONTRIBUTING.md) y [SECURITY.md](SECURITY.md).
