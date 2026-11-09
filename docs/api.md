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
| 400 | Enlace de recuperación inválido, vencido o ya usado (`"El enlace no es válido o expiró"`) |
| 401 | Sin sesión válida ni `X-API-Key` (`"Inicia sesión para continuar"`), clave incorrecta en una ruta del IoT (`"X-API-Key inválida"`) o credenciales incorrectas en el login (`"Correo o contraseña incorrectos"`) |
| 403 | Cambio con la cookie de sesión desde un origen no permitido (`"Origen no permitido"`); registro cerrado o código de invitación inválido |
| 404 | No existe el recurso o una referencia (cámara, tipo, sujeto, zona) |
| 409 | Transición no permitida (por ejemplo, falsa alarma sobre un evento ya resuelto), conflicto con datos que cambiaron o correo ya registrado |
| 413 | El cuerpo supera 64 KiB |
| 422 | Cuerpo o parámetros inválidos |
| 429 | Demasiados inicios de sesión fallidos con un correo, o demasiados registros o solicitudes de recuperación |
| 500 | Error inesperado: `{"detail": "Error interno del servidor"}`, sin detalles internos |
| 503 | La base de datos no está disponible, o la recuperación de contraseña no está configurada |

**Encabezados de respuesta.** Todas las respuestas llevan `X-Request-ID` (el
que envió el cliente si es seguro, o uno nuevo), `X-Content-Type-Options:
nosniff`, `X-Frame-Options: DENY` y `Referrer-Policy: no-referrer`. CORS
permite los orígenes de `FRONTEND_ORIGINS` con credenciales
(`Access-Control-Allow-Credentials: true` y el origen exacto, nunca `*`) y
expone `X-Duplicate` y `X-Request-ID`.

**Autenticación.** Todas las rutas de `/api`, salvo `POST /api/auth/login`,
`POST /api/auth/logout`, `POST /api/auth/register`,
`POST /api/auth/password/forgot`, `POST /api/auth/password/reset` y
`GET /api/auth/options`, exigen la cookie de sesión del panel **o** la
`X-API-Key` del módulo IoT; `POST /api/eventos` y
`PATCH /api/camaras/{id}/estado` exigen siempre la clave. Son públicas
`GET /`, `/health`, `/health/ready`, `/docs` y `/openapi.json`. Detalle en
[Autenticación](#autenticación).

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
  "occurred_at": "2026-10-14T07:05:31-05:00",
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
| `occurred_at` | El mismo instante en ISO 8601 con la zona de `TIMEZONE` (por ejemplo `2026-10-14T07:05:31-05:00`) |
| `priority` | `Alto` (severidad 3–4), `Medio` (2) o `Bajo` (1) |
| `status` | `Pendiente` (pending, in_review) o `Revisado` (resolved, false_alarm) |

---

## Autenticación

Decisiones y alternativas en [ADR 0007](adr/0007-sesion-con-cookie-firmada.md)
y [ADR 0008](adr/0008-registro-y-recuperacion-sin-tabla.md).

### Sesión del panel

El inicio de sesión deja una cookie que el navegador envía sola en cada
petición (`credentials: "include"` en `fetch`). El panel nunca ve el token.

| Atributo | Valor |
|---|---|
| Nombre | `sv_session` |
| Contenido | Id del usuario, emisión, expiración y huella de la contraseña, firmados con HMAC-SHA256 y `SESSION_SECRET` |
| Duración | `SESSION_TTL_HOURS` (8 h por defecto), sin renovación |
| Atributos | `HttpOnly`, `Secure`, `Path=/`, sin `Domain`, `SameSite` de `SESSION_COOKIE_SAMESITE` (`none` por defecto o `lax`) |

En cada petición el usuario se vuelve a leer de la tabla `users`: si ya no
existe o **su contraseña cambió**, la sesión deja de valer (401). Como la cookie es `Secure`, el navegador
solo la envía por https (o a `localhost`).

**Protección CSRF.** Un `POST`, `PUT`, `PATCH` o `DELETE` con la cookie debe
traer `Origin` (o, si falta, `Referer`) de `FRONTEND_ORIGINS` o del propio
backend (la página `/docs`); si no, `403 {"detail": "Origen no permitido"}`. Los
navegadores envían `Origin` solos; el panel no tiene que hacer nada. Las
peticiones con una `X-API-Key` válida no pasan por esta comprobación.

### `POST /api/auth/login`

```http
POST /api/auth/login
Content-Type: application/json

{"email": "usuario@example.com", "password": "contraseña"}
```

```http
HTTP/1.1 200 OK
Set-Cookie: sv_session=<token>; HttpOnly; Max-Age=28800; Path=/; SameSite=none; Secure
Content-Type: application/json

{"authenticated": true, "user": {"id": 1, "name": "Usuario de prueba", "email": "usuario@example.com"}}
```

- El correo se compara sin distinguir mayúsculas ni espacios a los lados y debe
  pertenecer a **exactamente un** usuario (la columna no es única).
- `401 {"detail": "Correo o contraseña incorrectos"}` ante cualquier fallo, con
  el mismo mensaje y un tiempo de respuesta similar exista o no el correo.
- `429 {"detail": "Demasiados intentos fallidos. Intenta de nuevo en unos
  minutos."}` tras 5 fallos con el mismo correo en 15 minutos, hasta que el más
  antiguo cumple 15 minutos (aunque la contraseña sea correcta). Un inicio
  correcto borra la cuenta de fallos.
- `422` si falta un campo, el correo supera 320 caracteres o la contraseña
  1024.
- Las contraseñas se guardan en `users.password_hash` como
  `pbkdf2_sha256$600000$<sal>$<hash>` (base64). Un hash en otro formato nunca
  valida: esa cuenta recibe 401 hasta que se le asigna uno nuevo con
  `scripts/hash_password.py` (ver el README).

### `GET /api/auth/me`

Con la cookie: `200` con el mismo cuerpo que el login. Sin cookie, con una
cookie alterada o vencida, o si el usuario ya no existe:
`401 {"detail": "Inicia sesión para continuar"}`. El panel la llama al cargar
para decidir si muestra el formulario.

### `POST /api/auth/logout`

`204` sin cuerpo y `Set-Cookie: sv_session=""; Max-Age=0; ...` con los mismos
atributos, de modo que el navegador la borra. Funciona también sin sesión, así
que repetirlo no falla. Con la cookie, aplica la protección CSRF.

### `GET /api/auth/ws-ticket`

Requiere la cookie (la `X-API-Key` no basta). Responde
`{"ticket": "<token>", "expires_in": 60}`: un token firmado que solo sirve para
abrir `/ws/alertas?ticket=<token>` durante 60 segundos. Sirve cuando el
navegador no envía la cookie con el WebSocket.

### Política de datos de una cuenta

La aplican el registro y el restablecimiento. Un incumplimiento responde
`422 {"detail": "<mensaje>"}` con uno de estos textos:

| Campo | Regla | Mensaje |
|---|---|---|
| `password` | Mínimo 8 caracteres | `La contraseña debe tener al menos 8 caracteres` |
| `password` | Máximo 128 caracteres | `La contraseña no puede superar 128 caracteres` |
| `password` | Al menos una letra y un número | `La contraseña debe incluir al menos una letra y un número` |
| `name` | Sin espacios al inicio o al final | `El nombre no puede empezar ni terminar con espacios` |
| `name` | De 2 a 100 caracteres | `El nombre debe tener entre 2 y 100 caracteres` |
| `name` | Sin caracteres de control | `El nombre contiene caracteres no permitidos` |
| `email` | El patrón de `chk_users_email`, hasta 320 caracteres | `El correo no tiene un formato válido` |

Si falta un campo o su tipo es incorrecto, `detail` es la lista que genera
FastAPI.

### `GET /api/auth/options`

Pública. Indica qué botones puede mostrar el panel:

```json
{"registration": "invite", "password_recovery": true}
```

`registration` es `closed`, `invite` u `open`. El modo `invite` sin
`REGISTRATION_CODE` configurado se informa como `closed`, porque así se comporta.
`password_recovery` es `false` con `EMAIL_PROVIDER=disabled`.

### `POST /api/auth/register`

```http
POST /api/auth/register
Content-Type: application/json

{"name": "Usuario de ejemplo", "email": "Usuario@Example.com", "password": "contraseña1", "invitation_code": "<código>"}
```

```http
HTTP/1.1 201 Created
Set-Cookie: sv_session=<token>; HttpOnly; Max-Age=28800; Path=/; SameSite=none; Secure
Content-Type: application/json

{"authenticated": true, "user": {"id": 7, "name": "Usuario de ejemplo", "email": "usuario@example.com"}}
```

`invitation_code` solo se usa en modo `invite`. El correo se guarda en
minúsculas y la cuenta queda con la sesión iniciada.

| Código | `detail` | Cuándo |
|---|---|---|
| `201` | — | Cuenta creada |
| `403` | `El registro de cuentas no está habilitado` | Modo `closed`, o `invite` sin código configurado |
| `403` | `Código de invitación inválido` | Modo `invite` con el código ausente o incorrecto |
| `403` | `Origen no permitido` | Trae un `Origin` que no está en `FRONTEND_ORIGINS` |
| `409` | `Ya existe una cuenta con ese correo` | El correo ya existe, sin distinguir mayúsculas |
| `422` | Ver la política | Nombre, correo o contraseña inválidos |
| `429` | `Demasiadas solicitudes. Intenta de nuevo más tarde.` | 5 intentos con datos válidos desde la misma dirección en una hora, incluidos los rechazados |

Como el login, no exige `Origin`, porque todavía no hay una sesión que proteger.

### `POST /api/auth/password/forgot`

```http
POST /api/auth/password/forgot
Content-Type: application/json

{"email": "usuario@example.com"}
```

```http
HTTP/1.1 202 Accepted
Content-Type: application/json

{"detail": "Si el correo está registrado, recibirás un enlace para restablecer la contraseña."}
```

La respuesta es la misma exista o no el correo, y tarda lo mismo: la búsqueda y
el envío ocurren después de responder. Si el correo pertenece a exactamente un
usuario, recibe `PASSWORD_RESET_URL?token=<token>`, válido durante
`PASSWORD_RESET_TTL_MINUTES` (30 por defecto) y una sola vez.

| Código | `detail` | Cuándo |
|---|---|---|
| `202` | El mensaje de arriba | Siempre que la solicitud se acepta |
| `422` | Lista de FastAPI | Falta `email`, no es texto o supera 320 caracteres |
| `429` | `Demasiadas solicitudes. Intenta de nuevo más tarde.` | 3 solicitudes por correo o 10 por dirección en una hora |
| `503` | `La recuperación de contraseña no está disponible` | `EMAIL_PROVIDER=disabled` |

### `POST /api/auth/password/reset`

```http
POST /api/auth/password/reset
Content-Type: application/json

{"token": "<token del enlace>", "new_password": "contraseña2"}
```

`204` sin cuerpo si la contraseña cambió. **No inicia sesión**: el panel debe
llevar al usuario al login. Todas las sesiones anteriores de esa cuenta quedan
invalidadas (401).

| Código | `detail` | Cuándo |
|---|---|---|
| `204` | — | Contraseña cambiada |
| `400` | `El enlace no es válido o expiró` | Token alterado, vencido, ya usado o de una contraseña anterior |
| `422` | Ver la política | La contraseña no cumple la política; el enlace sigue sirviendo |
| `429` | `Demasiadas solicitudes. Intenta de nuevo más tarde.` | 10 intentos desde la misma dirección en una hora |

### Lo que el frontend detecta

- La ruta de sesión es `GET /api/auth/me` y la de inicio de sesión
  `POST /api/auth/login` (ambas en `/openapi.json`).
- La sesión es válida si la respuesta trae `authenticated: true` y `user.id`.
- Un `401` en cualquier ruta significa que hay que mostrar el login.

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

Con la sesión del panel o con la `X-API-Key` del módulo IoT, que los usa para
resolver cámaras y tipos.

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

Se acepta con **una** de estas credenciales:

| Credencial | Cómo |
|---|---|
| Ticket | `/ws/alertas?ticket=<token>` con un ticket de `GET /api/auth/ws-ticket` (60 s) |
| Cookie de sesión | La envía el navegador; el `Origin` debe ser de `FRONTEND_ORIGINS` o del backend |
| `X-API-Key` | Encabezado del saludo (módulo IoT, scripts) |

Sin credenciales válidas la conexión se acepta y se cierra de inmediato con el
código **4401**: el panel debe ir al login en lugar de reintentar. El servidor
envía JSON; los mensajes del cliente se ignoran.

| `tipo` | Contenido | Cuándo |
|---|---|---|
| `alerta_nueva` | `alerta`: misma forma que un elemento de `/api/alertas/pendientes` | Se registró un evento nuevo (no en detecciones repetidas) |
| `evento_revisado` | `evento`: `EventView` | Un evento se revisó o se marcó como falsa alarma |
| `ping` | — | 25 s sin otros mensajes |

Cada cliente tiene una cola de 100 mensajes: si no los lee a tiempo, pierde los
más nuevos en lugar de frenar al servidor. Ante una desconexión, el panel debe
reconectarse (con un ticket nuevo si usa tickets) y pedir
`/api/alertas/pendientes` para ponerse al día.
