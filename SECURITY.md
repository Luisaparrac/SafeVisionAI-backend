# Política de seguridad

## Versiones con soporte

Solo la rama `main`, que es la desplegada. Las correcciones de seguridad se
publican allí.

## Cómo reportar una vulnerabilidad

**No abras un issue público.** Usa el reporte privado de GitHub: en la pestaña
**Security** del repositorio, **Report a vulnerability**. Incluye:

- qué componente afecta (ruta, encabezado, configuración…);
- cómo reproducirlo, con datos ficticios;
- el impacto que ves posible.

No incluyas datos reales de usuarios, claves ni la URL del servicio en el
reporte si no es imprescindible. El equipo confirma la recepción en un plazo de
siete días y acuerda contigo cuándo publicar el detalle, después de la
corrección.

## Secretos del servicio

El backend usa tres secretos. Ninguno se escribe en el repositorio: viven en las
variables de entorno de Render y en el `.env` local de cada desarrollador, que
está en `.gitignore`.

| Secreto | Variable | Quién lo usa |
|---|---|---|
| Credenciales de la base | `DATABASE_URL` | El backend |
| Clave del módulo IoT | `IOT_API_KEY` | El backend y el dispositivo IoT |
| Clave de las sesiones | `SESSION_SECRET` | Solo el backend |

Las contraseñas de los usuarios del panel no son secretos del servicio: se
guardan en la base como hashes PBKDF2 (nunca en texto) y se generan con
`scripts/hash_password.py`, que no se conecta a la base.

### Rotación de `SESSION_SECRET`

1. Genera un valor nuevo de al menos 32 caracteres aleatorios.
2. Actualiza la variable en Render. Al reiniciar, **todas las sesiones se
   cierran** y los usuarios deben volver a iniciar sesión. Es también la forma
   de cerrar de golpe una sesión robada.

### Rotación de `IOT_API_KEY`

1. Genera un valor nuevo, largo y aleatorio (Render puede generarlo).
2. Actualiza la variable en Render; el servicio se reinicia con la clave nueva.
3. Actualiza la clave en el dispositivo IoT. Hasta entonces sus envíos reciben
   401, así que coordina el cambio con el equipo IoT.
4. Actualiza tu `.env` local si lo usas.

### Rotación de la contraseña de la base

1. Pide a quien administra la base que cambie la contraseña del usuario del
   backend.
2. Actualiza `DATABASE_URL` en Render (con los caracteres especiales
   codificados, por ejemplo `!` → `%21`).
3. Comprueba `GET /health/ready`: debe responder 200.
4. Actualiza tu `.env` local.

### Si un secreto se filtra

Rótalo **de inmediato** siguiendo los pasos de arriba. Borrarlo del repositorio
no basta: el historial de git es público y no se reescribe. Revisa después los
registros del servicio por usos indebidos.

## Protecciones del backend

- Comparación de `X-API-Key` en tiempo constante; la app no arranca sin
  `IOT_API_KEY`, `DATABASE_URL` ni `SESSION_SECRET` (de al menos 32
  caracteres).
- Rutas del panel y WebSocket solo con sesión o `X-API-Key`
  ([ADR 0007](docs/adr/0007-sesion-con-cookie-firmada.md)): cookie `HttpOnly`,
  `Secure` y firmada con HMAC-SHA256, contraseñas con PBKDF2-SHA256 (600 000
  iteraciones), mismo mensaje y tiempo similar ante cualquier fallo del login y
  límite de 5 fallos por correo en 15 minutos.
- Protección CSRF: los cambios hechos con la cookie exigen un `Origin` de
  `FRONTEND_ORIGINS` o del propio backend; el WebSocket con cookie también.
- El usuario de la base solo lee y escribe filas: el backend nunca ejecuta DDL.
- Registros sin datos sensibles: se ocultan credenciales de URLs y valores de
  claves; no se guarda la IP del cliente ni la cadena de consulta.
- Errores de base de datos e inesperados sin detalles internos.
- Cabeceras `X-Content-Type-Options`, `X-Frame-Options` y `Referrer-Policy`;
  CORS con credenciales limitado a `FRONTEND_ORIGINS` (no admite `*`).
- Límites de tamaño del cuerpo (64 KiB) y de los campos de texto.
- Dependencias revisadas por Dependabot y CI en cada pull request.

## Limitaciones conocidas

- Una sesión no se puede revocar en el servidor antes de que expire
  (`SESSION_TTL_HOURS`): no hay tabla de sesiones. Borrar al usuario o rotar
  `SESSION_SECRET` la invalida.
- El límite de intentos de inicio de sesión vive en memoria: se reinicia con el
  servicio y es por proceso.
- No hay roles: todo usuario con sesión ve y revisa todos los eventos.
- Registro, verificación de correo, recuperación de contraseña y OAuth son
  mejoras futuras: requieren cambios en la base o servicios externos.
