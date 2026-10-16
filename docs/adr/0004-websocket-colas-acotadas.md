# ADR 0004: Alertas en vivo por WebSocket con colas acotadas por cliente

- **Estado:** aceptada
- **Fecha:** 2026-10-16

## Contexto

El panel solo se enteraba de una alerta nueva consultando
`/api/alertas/pendientes` cada cierto tiempo. Para una caída, cada segundo
cuenta.

Los casos de uso corren en los hilos del servidor que atienden las rutas
síncronas, mientras que cada conexión WebSocket vive en el bucle de eventos de
asyncio. Publicar no debe bloquear una petición del IoT ni depender de que el
panel esté conectado.

## Decisión

1. Un puerto de la aplicación, `AlertNotifier`, con un solo método
   `publish(notification)`. `RegisterEvent` publica la alerta creada y
   `ReviewEvent`/`MarkFalseAlarm` publican el cierre, siempre **después del
   commit** y solo si algo cambió.
2. El adaptador `AlertBroadcaster` mantiene, por cliente, una
   `asyncio.Queue` acotada (100 mensajes) junto con su bucle de eventos.
   `publish` se llama desde cualquier hilo y entrega con
   `loop.call_soon_threadsafe`, así nunca bloquea.
3. Si la cola de un cliente está llena, **ese cliente pierde el mensaje**; los
   demás y las peticiones no se ven afectados. Si su bucle ya cerró, se le da
   de baja.
4. Mensajes en español como el resto de la API: `alerta_nueva` con la forma de
   `/api/alertas/pendientes`, `evento_revisado` con un `EventView`, y `ping`
   tras 25 s sin mensajes para que los proxies no corten la conexión y el panel
   sepa que sigue viva.
5. La ruta `/ws/alertas` es aditiva: ninguna ruta existente cambia.

## Consecuencias

- El panel recibe las alertas al instante y puede dejar de consultar
  periódicamente; `/api/alertas/pendientes` sigue siendo la forma de ponerse al
  día tras conectarse o reconectarse.
- La entrega es "a lo sumo una vez": un cliente lento o desconectado puede
  perder mensajes. La base sigue siendo la fuente de verdad.
- Las suscripciones viven en memoria del proceso: con varias instancias del
  servidor, cada una avisaría solo a sus clientes. Hoy hay una sola instancia
  (plan gratuito); escalar exigiría un canal compartido.
- Los casos de uso no conocen WebSocket: en pruebas se usa un notificador que
  solo registra lo publicado.

## Alternativas consideradas

- **Consulta periódica del panel:** más simple, pero con retraso y tráfico
  constante.
- **Server-Sent Events:** suficiente para un solo sentido, pero el plan pedía
  WebSocket y uvicorn ya lo soporta con `uvicorn[standard]`.
- **Cola sin límite:** un cliente que no lee haría crecer la memoria sin fin.
- **Enviar directamente desde el hilo del caso de uso:** mezclaría hilos y
  bucle de eventos y bloquearía la petición del IoT mientras se envía.
