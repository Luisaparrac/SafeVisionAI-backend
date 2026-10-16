# Referencia de la API

Base: la URL del servicio (en local, `http://localhost:8000`). La especificación
OpenAPI generada está en `/openapi.json` y la interfaz interactiva en `/docs`.

Las rutas, códigos y formas JSON marcadas como **contrato** las usan el panel o
el módulo IoT y están fijadas por `tests/contract`: no cambian. Todo lo
agregado después es opcional y aditivo.

## Convenciones

**Errores.** Siempre `{"detail": ...}`. En errores de negocio `detail` es un
texto en español; en errores de validación del cuerpo o de los parámetros es la
lista que genera FastAPI.

| Código | Cuándo |
|---|---|
| 401 | Falta `X-API-Key` o no coincide (`{"detail": "X-API-Key inválida"}`) |
| 404 | No existe el recurso o una referencia (cámara, tipo, sujeto, zona) |
| 409 | Transición no permitida (por ejemplo, falsa alarma sobre un evento ya resuelto) o conflicto con datos que cambiaron |
| 413 | El cuerpo supera 64 KiB |
| 422 | Cuerpo o parámetros inválidos |
| 500 | Error inesperado: `{"detail": "Error interno del servidor"}`, sin detalles internos |
| 503 | La base de datos no está disponible |

**Encabezados de respuesta.** Todas las respuestas llevan `X-Request-ID` (el
que envió el cliente si es seguro, o uno nuevo), `X-Content-Type-Options:
nosniff`, `X-Frame-Options: DENY` y `Referrer-Policy: no-referrer`. CORS
permite los orígenes de `FRONTEND_ORIGINS` y expone `X-Duplicate` y
`X-Request-ID`.

**Autenticación.** Solo las rutas del módulo IoT exigen `X-API-Key`. Las del
panel no piden credenciales (la autenticación del panel es una mejora futura).

### EventView (contrato)

Forma de cada evento en todas las respuestas:

```json
{
  "id": 12,
  "type": "Caída",
  "subject": "Rosa",
  "location": "Casa · Escalera",
  "camera": "Sala",
  "date": "2026-10-14",
  "time": "07:05:31",
  "priority": "Alto",
  "status": "Pendiente",
  "description": "Persona en el piso"
}
```

| Campo | Significado |
|---|---|
| `type` | Nombre del tipo de evento |
| `subject` | Nombre del sujeto o, si no se identificó, la clase detectada: "Persona sin identificar", "Perro sin identificar", "Gato sin identificar", "Animal sin identificar" |
| `location` | Ubicación de la cámara y, si hay zona, " · " y el nombre de la zona |
| `date`, `time` | Fecha (`AAAA-MM-DD`) y hora (`HH:MM:SS`) en `TIMEZONE` |
| `priority` | `Alto` (severidad 3–4), `Medio` (2) o `Bajo` (1) |
| `status` | `Pendiente` (pending, in_review) o `Revisado` (resolved, false_alarm) |

---

## Salud

### `GET /` (contrato)

`200 {"servicio": "SafeVision AI backend", "docs": "/docs"}`

### `GET /health` (contrato)

Prueba de vida; no consulta la base. `200 {"status": "ok"}`

### `GET /health/ready`

Comprueba la base con una consulta trivial.
`200 {"status": "ok", "database": "ok"}` o
`503 {"status": "unavailable", "database": "error"}`.

## Eventos

### `GET /api/eventos` (contrato)

Historial de eventos, del más reciente al más antiguo. Lista de `EventView`.

| Parámetro | Tipo | Descripción |
|---|---|---|
| `q` | texto | Busca, sin distinguir mayúsculas, en el id, tipo, sujeto y ubicación |
| `prioridad` | `Alto` \| `Medio` \| `Bajo` | Un valor desconocido se ignora |
| `estado` | `Pendiente` \| `Revisado` | Un valor desconocido se ignora |
| `camara_id` | entero | Solo los eventos de esa cámara |
| `desde`, `hasta` | fecha `AAAA-MM-DD` | Días locales, ambos inclusivos; un rango invertido da 422 |
| `limit` | 1–500 | Tamaño de página; sin él se devuelve todo |
| `offset` | ≥ 0 | Eventos que se saltan (por defecto 0) |

Los parámetros se combinan. La paginación se aplica después de todos los filtros.

### `GET /api/eventos/recientes` (contrato)

Historial reciente (lista doblemente enlazada en memoria), del más nuevo al más
antiguo. No consulta la base. `limit` de 1 a 100 (por defecto 20).
Lista de `EventView`.

### `GET /api/eventos/{id}` (contrato)

`200 EventView` · `404 {"detail": "Evento 999 no existe"}` · `422` si el id no es entero.

### `POST /api/eventos` (contrato, módulo IoT)

Encabezado `X-API-Key`. Cuerpo:

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `camera_id` | entero | Sí | Cámara que detectó |
| `event_type_id` | entero | Uno de los dos | Tipo por id |
| `event_type` | texto | Uno de los dos | Tipo por nombre, sin distinguir mayúsculas |
| `subject_id` | entero | No | Sujeto identificado |
| `zone_id` | entero | No | Debe pertenecer a la cámara |
| `detected_class` | `person` \| `dog` \| `cat` \| `other_animal` | No | Por defecto `person` |
| `confidence` | número 0–1 | No | Confianza del modelo |
| `evidence_url` | texto ≤ 2048 | No | Enlace a la evidencia |
| `description` | texto ≤ 2000 | No | Texto libre; en blanco se guarda vacío (NULL) |

Respuestas:

- `201 EventView`: evento creado, con su alerta (`level` = severidad del tipo).
  La alerta llega también por `/ws/alertas`.
- `201 EventView` con `X-Duplicate: true`: la misma cámara, tipo y sujeto se
  registraron hace menos de `DEDUP_WINDOW_SECONDS`; devuelve ese evento y no
  crea otro.
- `401`, `404` (cámara, tipo, sujeto o zona), `413`, `422` (por ejemplo
  `{"detail": "Envía event_type_id o event_type"}`).

### `PATCH /api/eventos/{id}/revisar` (contrato)

Marca el evento como resuelto y cierra sus alertas abiertas. Repetirlo devuelve
el evento sin cambios. `200 EventView` con `status: "Revisado"` · `404`.

### `PATCH /api/eventos/{id}/falsa-alarma`

Marca el evento como falsa alarma y descarta sus alertas abiertas. Repetirlo no
cambia nada. `200 EventView` · `404` · `409` si el evento ya fue resuelto (no se
reescribe el resultado de una revisión).

## Alertas y métricas

### `GET /api/alertas/pendientes` (contrato)

Alertas de eventos pendientes en orden de atención: mayor severidad primero y,
si empatan, la más antigua (cola de prioridad). `limit` de 1 a 100 (por defecto 10).

```json
[{"id_alerta": 2, "nivel": "Alto", "estado": "Activa", "event": {"id": 2, "...": "..."}}]
```

`estado`: `Activa`, `Vista`, `Atendida` o `Descartada`.

### `PATCH /api/alertas/{id}/vista`

Registra que alguien vio la alerta; sigue pendiente hasta que se cierre su
evento. `200` con la alerta (misma forma que arriba, `estado: "Vista"`) ·
`404 {"detail": "Alerta 999 no existe"}` · `409` si la alerta ya está cerrada.

### `GET /api/metricas` (contrato)

`200 {"total": 4, "pendientes": 2, "alto": 2}`: eventos totales, alertas en la
cola de pendientes y eventos de prioridad alta.

## Estadísticas

Ambas aceptan `desde` y `hasta` (días locales, inclusivos; 422 si el rango está
invertido) e incluyen los elementos sin eventos (total 0), ordenados del que
más tiene al que menos.

### `GET /api/estadisticas/tipos`

```json
[{"event_type_id": 1, "name": "Caída", "priority": "Alto", "total": 5}]
```

Empates por nombre.

### `GET /api/estadisticas/camaras`

```json
[{"camera_id": 1, "name": "Sala", "total": 7}]
```

Empates por id.

## Catálogos (contrato, solo lectura)

| Ruta | Elemento | Orden |
|---|---|---|
| `GET /api/tipos-evento` | `{"event_type_id", "name", "description", "severity_level", "priority"}` | Severidad descendente, luego nombre |
| `GET /api/ubicaciones` | `{"location_id", "name", "description"}` | Id |
| `GET /api/camaras` | `{"camera_id", "name", "ip_address", "status", "location_id"}` | Id |
| `GET /api/zonas` | `{"zone_id", "name", "description", "coordinates", "is_active", "camera_id"}` | Id |
| `GET /api/sujetos` | `{"subject_id", "name", "subject_type", "description"}` | Id |

`coordinates` es una lista de al menos tres puntos `[x, y]`.

### `PATCH /api/camaras/{id}/estado` (contrato, módulo IoT)

Encabezado `X-API-Key`. Cuerpo `{"status": "disconnected"}` con `active`,
`inactive`, `disconnected` o `maintenance`.
`200 {"camera_id": 2, "status": "disconnected"}` · `401` · `404` · `422`.

## WebSocket `/ws/alertas`

Conexión sin credenciales. El servidor envía JSON; los mensajes del cliente se
ignoran.

| `tipo` | Contenido | Cuándo |
|---|---|---|
| `alerta_nueva` | `alerta`: misma forma que un elemento de `/api/alertas/pendientes` | Se registró un evento nuevo (no en detecciones repetidas) |
| `evento_revisado` | `evento`: `EventView` | Un evento se revisó o se marcó como falsa alarma |
| `ping` | — | 25 s sin otros mensajes |

Cada cliente tiene una cola de 100 mensajes: si no los lee a tiempo, pierde los
más nuevos en lugar de frenar al servidor. Ante una desconexión, el panel debe
reconectarse y pedir `/api/alertas/pendientes` para ponerse al día.
