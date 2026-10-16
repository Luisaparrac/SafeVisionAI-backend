# Decisiones de arquitectura (ADR)

Cada archivo registra una decisión: el contexto, lo que se decidió, sus
consecuencias y las alternativas descartadas. Una decisión que se reemplaza no
se borra: se marca como sustituida y se enlaza la nueva.

| ADR | Decisión | Estado |
|---|---|---|
| [0001](0001-arquitectura-hexagonal.md) | Arquitectura hexagonal con migración por estrangulamiento | Aceptada |
| [0002](0002-base-existente-sin-ddl.md) | Usar la base existente sin DDL | Aceptada |
| [0003](0003-deduplicacion-60-segundos.md) | Deduplicar detecciones del IoT con una ventana de 60 s | Aceptada |
| [0004](0004-websocket-colas-acotadas.md) | Alertas en vivo por WebSocket con colas acotadas por cliente | Aceptada |
| [0005](0005-humo-dependencias-produccion.md) | Prueba de humo con el comando real y solo dependencias de producción | Aceptada |
