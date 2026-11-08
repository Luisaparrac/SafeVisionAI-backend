# ADR 0008: Registro por invitación y recuperación de contraseña sin tabla nueva

- **Estado:** aceptada
- **Fecha:** 2026-11-08

## Contexto

El panel ya inicia sesión (ADR 0007), pero sus botones "Crear cuenta" y "Olvidé
mi contraseña" no tenían a qué llamar.

Restricciones:

- El backend **no puede cambiar el esquema** (ADR 0002): no hay tabla de tokens
  ni de sesiones, y `users.email` no es único.
- No hay roles: cualquier cuenta ve todos los datos, así que un registro abierto
  expondría el panel a cualquiera.
- El plan gratuito del hosting bloquea los puertos SMTP (25, 465 y 587).
- `requirements.txt` no cambia.

## Decisión

1. **Registro restringible** con `REGISTRATION_MODE`: `closed`, `invite` (por
   defecto) u `open`. El modo `invite` sin `REGISTRATION_CODE` se comporta como
   `closed`, de modo que un despliegue sin configurar no abre el registro. El
   código se compara en tiempo constante.
2. **Unicidad del correo en la aplicación.** La columna no es única, así que el
   registro busca el correo, calcula el hash fuera de la transacción y vuelve a
   buscarlo bajo un bloqueo consultivo de PostgreSQL por correo, que se libera
   al terminar la transacción y no es DDL.
3. **Enlaces de recuperación firmados y sin estado.** Con el mismo mecanismo que
   la cookie, HMAC-SHA256 y `SESSION_SECRET`, con el propósito `pwreset`: un
   enlace no sirve como cookie ni como ticket, ni al revés. Lleva el id del
   usuario, la expiración y una huella corta de `password_hash`.
4. **La huella hace de "un solo uso" y de revocación.** Al cambiar la contraseña
   cambia la huella, y con ella dejan de valer el enlace y todas las sesiones
   anteriores, que llevan la misma huella. El `UPDATE` se condiciona al hash
   leído, así que de dos peticiones simultáneas con un enlace solo una gana.
5. **Envío por la API HTTPS de Brevo**, detrás del puerto `EmailSender`, con
   `urllib`, timeout y un solo intento. Sin `EMAIL_PROVIDER=brevo` la
   recuperación responde 503.
6. **La solicitud no revela cuentas.** Responde 202 siempre; la búsqueda y el
   envío van en una tarea en segundo plano, y los límites cuentan exista o no
   el correo.
7. **Límites en memoria** con la ventana deslizante del login: 5 registros por
   dirección y hora; 3 solicitudes de recuperación por correo y 10 por
   dirección; 10 restablecimientos por dirección. La dirección sale de la
   cabecera del proxy de borde (`CF-Connecting-IP`) o de la última entrada de
   `X-Forwarded-For`, nunca de las primeras, que el cliente puede falsificar.

## Consecuencias

- No hay cambios de esquema ni tablas nuevas.
- Con esta versión las cookies emitidas antes dejan de valer, porque no traen
  huella: cada usuario inicia sesión una vez más.
- Hasta que expira, un enlace no se puede revocar salvo cambiando la contraseña
  o `SESSION_SECRET`. Por eso dura poco (30 minutos por defecto).
- Rotar `SESSION_SECRET` invalida sesiones y enlaces a la vez.
- `POST /api/auth/register` responde 409 si el correo existe, de modo que ese
  dato se puede averiguar; lo limitan el código de invitación y los 5 intentos
  por hora. Es una decisión de experiencia de uso.
- Cualquiera puede agotar las 3 solicitudes por hora de un correo ajeno.
- Los límites son por proceso y se reinician con el servicio. La cabecera del
  proxy de borde solo es fiable detrás de ese proxy; fuera de él (por ejemplo,
  en Docker local) un cliente podría variarla y evadir el límite por dirección.
- No se verifica la propiedad del correo al registrarse.

## Alternativas descartadas

- **Tabla de tokens de un solo uso:** exige DDL.
- **SMTP:** los puertos están bloqueados en el plan gratuito.
- **Librería cliente del proveedor o de JWT:** cambia `requirements.txt` para
  una sola petición HTTP o una firma que ya existe.
- **Registro abierto por defecto:** sin roles, equivale a publicar el panel.
- **Enviar el correo durante la petición:** el tiempo de respuesta revelaría qué
  correos existen.
