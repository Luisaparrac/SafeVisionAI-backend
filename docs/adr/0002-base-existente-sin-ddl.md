# ADR 0002: Usar la base existente sin DDL

- **Estado:** aceptada
- **Fecha:** 2026-10-14

## Contexto

La base PostgreSQL del equipo ya existía, con 8 tablas, restricciones `CHECK`
y llaves foráneas, y pertenece a otro rol. El usuario del backend solo tiene
permisos `SELECT`, `INSERT`, `UPDATE` y `DELETE`. Otros clientes del equipo
pueden escribir en las mismas tablas.

## Decisión

1. El backend **nunca crea, altera ni borra tablas**: nada de `create_all`,
   `drop_all`, migraciones ni DDL contra la base real. Una prueba de
   arquitectura falla si aparece DDL en el código fuente.
2. Los modelos ORM mapean las tablas tal como están. Una prueba compara sus
   columnas con `tests/integration/schema.sql`, copia de la estructura sin
   datos ni credenciales.
3. Las reglas del dominio replican las restricciones de la base (estados
   válidos, severidad 1–4, confianza 0–1, al menos tres puntos por zona,
   `attended_at ≥ created_at`) para fallar antes y con un mensaje claro.
4. La aplicación pone `occurred_at` con su propio reloj, y al cerrar alertas
   usa `max(ahora, created_at)` para no violar `chk_alerts_attended` si el
   reloj de la base va adelantado.
5. Las pruebas de integración usan **solo** `TEST_DATABASE_URL`. Antes de
   recrear tablas, una guarda exige `localhost` o `127.0.0.1` y un nombre de
   base terminado en `_test`; si no se cumple, fallan sin ejecutar nada.

## Consecuencias

- No hay riesgo de que un despliegue altere la estructura que comparten otros
  clientes.
- Si el equipo cambia el esquema, hay que actualizar `schema.sql`, los modelos
  ORM y los mappers; la prueba de columnas avisa de la diferencia.
- El entorno local (`docker compose`) y el CI usan el mismo `schema.sql`, así
  que se prueba contra la estructura real.
- Los valores de la base siguen en inglés (`pending`, `resolved`…); la
  traducción a las etiquetas del panel es responsabilidad de la aplicación.

## Alternativas consideradas

- **Migraciones con Alembic:** imposibles sin permisos de DDL y peligrosas en
  una base compartida.
- **Base propia del backend:** duplicaría datos que otros clientes ya usan.
