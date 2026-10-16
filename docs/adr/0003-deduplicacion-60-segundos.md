# ADR 0003: Deduplicar detecciones del IoT con una ventana de 60 s

- **Estado:** aceptada (sustituye la ventana inicial de 10 s)
- **Fecha:** 2026-10-15

## Contexto

El módulo IoT analiza varios cuadros por segundo y reporta la misma situación
una y otra vez mientras dura: una persona caída genera decenas de detecciones
idénticas. Sin control, cada una crearía un evento y una alerta, llenando la
cola de pendientes y el historial con duplicados.

El contrato del `POST /api/eventos` no podía cambiar: el IoT espera `201` con
un `EventView`.

## Decisión

1. Una detección es **repetida** si la misma combinación
   `(camera_id, event_type_id, subject_id)` se registró hace menos de
   `DEDUP_WINDOW_SECONDS`. Se compara el tipo ya resuelto, así que `event_type`
   por nombre y `event_type_id` cuentan igual.
2. Una repetida no crea evento ni alerta: responde **201 con el evento ya
   registrado** y el encabezado `X-Duplicate: true` (cambio aditivo; el IoT no
   necesita modificarse).
3. La ventana **cuenta desde la primera detección**: las repetidas no la
   renuevan. Una situación prolongada produce una alerta por ventana.
4. El valor por defecto es **60 s**. Con la ventana inicial de 10 s, una
   situación que dura un minuto habría generado seis alertas. `0` desactiva la
   deduplicación.
5. La ventana se registra **después del commit**, para que un fallo de la base
   no haga pasar el reintento del IoT por repetido.
6. Implementación: cola FIFO enlazada en orden de llegada más un diccionario
   con el último registro por clave; expirar y consultar cuestan O(1)
   amortizado (ver [estructuras.md](../estructuras.md#4-deduplicador-de-detecciones-cola--diccionario)).

## Consecuencias

- La cola de alertas refleja situaciones distintas, no cuadros de video.
- Si una situación termina y vuelve a ocurrir dentro de la ventana, la segunda
  no genera alerta. Se acepta: 60 s es corto frente al tiempo de atención.
- La ventana vive en memoria: tras un reinicio empieza vacía, y la primera
  detección después de reiniciar crea un evento nuevo.
- Dos peticiones idénticas simultáneas pueden crear dos eventos, porque la
  ventana se registra después del commit. Es raro y preferible a perder un
  evento.

## Alternativas consideradas

- **Deduplicar en el IoT:** el backend igual debía protegerse de reintentos y
  de varios dispositivos.
- **Restricción única en la base:** requiere DDL (ver ADR 0002) y no expresa
  una ventana de tiempo.
- **Ventana deslizante que se renueva con cada repetición:** una situación
  continua no volvería a alertar nunca.
- **Responder 409 a las repetidas:** rompía el contrato del IoT.
