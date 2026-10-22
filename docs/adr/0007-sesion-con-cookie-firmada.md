# ADR 0007: Sesión del panel con cookie firmada

- **Estado:** aceptada
- **Fecha:** 2026-10-22
- **Reemplaza a:** [ADR 0006](0006-websocket-sin-autenticacion.md)

## Contexto

Hasta ahora las rutas de lectura del panel y `/ws/alertas` eran públicas
(ADR 0006): cualquiera que conociera la URL del servicio podía leer eventos y
alertas, y también revisarlos. El panel ya tiene un formulario de inicio de
sesión y envía `credentials: "include"` en todas sus peticiones, así que espera
una sesión por cookie.

Restricciones:

- La base es compartida y el backend **no puede cambiar el esquema** (ADR
  0002): no hay tabla de sesiones ni columna de rol. La tabla `users` tiene
  `email` y `password_hash`, y `email` no es único.
- `requirements.txt` no cambia: nada de librerías de JWT, bcrypt o argon2.
- El panel llama directo al backend desde otro sitio, así que la cookie debe
  poder viajar entre sitios (`SameSite=None`), lo que la expone a CSRF.
- El módulo IoT y los scripts usan `X-API-Key` y deben seguir funcionando.

## Decisión

1. **Contraseñas** con PBKDF2-HMAC-SHA256 de la biblioteca estándar
   (600 000 iteraciones, sal aleatoria de 16 bytes, comparación en tiempo
   constante), guardadas como `pbkdf2_sha256$iteraciones$sal$hash`. Un hash en
   otro formato nunca valida. `scripts/hash_password.py` genera el valor que se
   aplica a mano en la base.
2. **Sesión sin estado en el servidor**: una cookie `sv_session` con el id del
   usuario, la emisión y la expiración (`SESSION_TTL_HOURS`, 8 h), firmada con
   HMAC-SHA256 y `SESSION_SECRET`. Atributos `HttpOnly`, `Secure`, `Path=/`,
   sin `Domain` y `SameSite` configurable (`none` por defecto, `lax` si el
   frontend sirve la API bajo su propio dominio). En cada petición el usuario
   se vuelve a leer de la base: si ya no existe, la sesión deja de valer.
3. **Inicio de sesión**: `POST /api/auth/login`. El correo se compara en
   minúsculas y debe pertenecer a exactamente un usuario. Todo fallo responde
   401 con el mismo mensaje y, si el correo no existe, la contraseña se
   verifica contra un hash descartable para que el tiempo tampoco lo revele.
   Cinco fallos con un correo en 15 minutos bloquean ese correo (429), con una
   ventana deslizante en memoria (cola enlazada + diccionario).
4. **CSRF**: los `POST`, `PUT`, `PATCH` y `DELETE` autenticados con la cookie
   exigen un `Origin` (o `Referer`) de `FRONTEND_ORIGINS` o del propio backend;
   si no, 403. CORS acepta credenciales solo para esos orígenes y la app no
   arranca si `FRONTEND_ORIGINS` contiene `*`.
5. **Rutas protegidas**: todo `/api` salvo iniciar y cerrar sesión exige la
   cookie o la `X-API-Key` del módulo IoT. Las rutas que escribe el IoT siguen
   exigiendo la clave.
6. **WebSocket**: `/ws/alertas` acepta un ticket firmado de 60 s
   (`GET /api/auth/ws-ticket`, en la URL como `?ticket=`), la `X-API-Key` o la
   cookie con un `Origin` de confianza. Sin credenciales se cierra con 4401.

## Consecuencias

- Los datos del panel dejan de ser públicos y el panel no maneja secretos: la
  cookie no es legible desde JavaScript.
- No hay cambios en la base ni dependencias nuevas.
- Una sesión no se puede revocar antes de que expire, salvo cambiando
  `SESSION_SECRET` (cierra todas) o borrando al usuario. Revocar sesiones
  sueltas requiere una tabla de sesiones: queda como mejora futura.
- El límite de intentos vive en memoria: es por proceso y se reinicia con el
  servicio. Basta para una sola instancia; con varias haría falta un almacén
  compartido.
- Los navegadores que bloquean cookies de terceros (Safari) no envían la
  cookie si el panel y la API están en sitios distintos. La solución es que el
  hosting del frontend reescriba `/api/*` hacia el backend y usar
  `SESSION_COOKIE_SAMESITE=lax`; el ticket cubre el WebSocket mientras tanto.
- Registro, recuperación de contraseña, roles y OAuth quedan fuera: requieren
  cambios en la base o servicios externos.

## Alternativas consideradas

- **JWT en `localStorage` con `Authorization: Bearer`:** legible por cualquier
  script inyectado en la página, y el panel ya envía cookies.
- **Tabla de sesiones en la base:** permitiría revocar, pero exige DDL que el
  backend no puede ejecutar.
- **bcrypt o argon2:** más resistentes por memoria, pero agregan
  dependencias; PBKDF2 con 600 000 iteraciones es la recomendación de OWASP
  para la biblioteca estándar.
- **Token anti-CSRF por formulario:** el panel es una SPA que llama a una API
  JSON; comprobar el `Origin` protege lo mismo sin que el frontend guarde otro
  secreto.
