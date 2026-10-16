# ADR 0006: WebSocket de alertas sin autenticación

- **Estado:** aceptada
- **Fecha:** 2026-10-16

## Contexto

`/ws/alertas` envía cada alerta nueva y cada evento revisado. Había que decidir
si exigía credenciales.

Hoy el backend solo autentica al módulo IoT (`X-API-Key` en las rutas que
escriben datos de las cámaras). Las rutas de lectura del panel, entre ellas
`GET /api/alertas/pendientes` y `GET /api/eventos`, son públicas: el panel no
tiene inicio de sesión. La autenticación de usuarios quedó fuera del alcance
del proyecto.

Usar la clave del IoT en el navegador la expondría a cualquiera que abra el
panel, y con ella se podrían crear eventos falsos.

## Decisión

`/ws/alertas` no pide credenciales. Expone exactamente los mismos datos que
`GET /api/alertas/pendientes` y `GET /api/eventos/{id}`, que ya son públicos,
solo que en el momento en que ocurren. Es de solo lectura: los mensajes del
cliente se ignoran.

## Consecuencias

- El panel se conecta sin manejar secretos.
- El nivel de protección es el mismo del resto de lecturas: cualquiera que
  conozca la URL del servicio puede leer las alertas. Es un riesgo conocido y
  aceptado para el alcance del curso, y se mitiga con lo ya existente: CORS
  limitado a los orígenes del panel (los navegadores de otros sitios no pueden
  leer las respuestas HTTP), registros sin datos personales del cliente y
  cabeceras de seguridad.
- Cuando el panel tenga autenticación de usuarios, el WebSocket debe exigir el
  mismo token que las rutas de lectura (por ejemplo, en el primer mensaje o en
  la URL del saludo) y verificar el `Origin`. Queda registrado como mejora
  futura.

## Alternativas consideradas

- **Reutilizar `IOT_API_KEY`:** quedaría expuesta en el código del navegador y
  permitiría escribir datos.
- **Un token propio solo para el WebSocket:** también viviría en el navegador
  sin un inicio de sesión que lo proteja; no agrega seguridad real.
- **No ofrecer WebSocket hasta tener autenticación:** el panel seguiría
  consultando cada pocos segundos para ver los mismos datos públicos.
