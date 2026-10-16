# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Cada versión agrupa las fases del plan de refactorización que entraron a `main`.
El contrato HTTP que usan el panel y el módulo IoT no cambió en ninguna: todo lo
nuevo es aditivo.

## [Sin publicar]

### Agregado
- Imagen Docker multi-etapa con solo dependencias de producción y el mismo
  comando de arranque que `render.yaml`.
- `docker compose` con PostgreSQL local, `schema.sql` y datos de ejemplo
  ficticios (`scripts/seed_dev.sql`); job de CI que construye la imagen y
  comprueba el stack.
- Cabeceras de seguridad (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`) en todas las respuestas.
- Límite de 64 KiB para el cuerpo de las peticiones (413).
- Mensaje `{"tipo": "ping"}` por `/ws/alertas` tras 25 s sin mensajes.
- Ejemplos OpenAPI para `POST /api/eventos` y `PATCH /api/camaras/{id}/estado`.
- Documentación en español: README, arquitectura, estructuras de datos,
  referencia de la API, ADR, guía de contribución y política de seguridad.

### Corregido
- Las conexiones WebSocket se registraban con la IP del cliente (línea de
  uvicorn); ahora se registran con request-id, ruta y resultado.

## [3.0.0] - 2026-10-16

Fases 8, 9 (resto) y 10.

### Agregado
- WebSocket `/ws/alertas` con alertas nuevas y eventos revisados.
- `GET /api/estadisticas/tipos` y `GET /api/estadisticas/camaras` con filtros
  `desde`/`hasta`.
- CI: cobertura con mínimo de 95 %, mypy estricto en dominio y aplicación,
  detección de código muerto con vulture y prueba de humo desde un entorno con
  solo `requirements.txt`.
- Configuración de pre-commit.

### Eliminado
- La aplicación anterior (`app/`) y sus pruebas: producción ya arrancaba la
  hexagonal.
- Código sin uso: caso de uso `StartReview`, entidad `User`, value object
  `Email` y métodos de dominio sin llamadas.

### Cambiado
- `scripts/simulate_event.py` exige URL y clave (argumentos o variables de
  entorno); ya no tiene valores por defecto.

## [2.4.0] - 2026-10-15

Cierre de la fase 6, fase 7 y la parte aditiva de la fase 9.

### Agregado
- Arranque de la app hexagonal en `render.yaml` y objeto `app` construido desde
  las variables de entorno existentes.
- Prueba de humo que arranca el comando de `render.yaml`.
- Middleware de request-id, registro de acceso sin datos sensibles y
  `LOG_LEVEL`.
- `GET /health/ready`, que comprueba la base.
- Límites de `description` (2000) y `evidence_url` (2048).
- Errores de base de datos sin detalles internos (503, 409, 500).
- `PATCH /api/eventos/{id}/falsa-alarma` y `PATCH /api/alertas/{id}/vista`.
- Filtros opcionales `camara_id`, `desde`, `hasta` y paginación `limit`/`offset`
  en `GET /api/eventos`.

### Cambiado
- Ventana de deduplicación por defecto de 10 a 60 s.

## [2.3.0] - 2026-10-15

Fases 5 y 6 (primera parte).

### Agregado
- Persistencia hexagonal: modelos ORM, mappers, repositorios SQLAlchemy,
  unidad de trabajo, fábrica de engine y `SystemClock`.
- Pruebas de integración sobre PostgreSQL con guarda de base `*_test` local.
- Adaptador HTTP nuevo (`create_app`, routers por recurso, esquemas Pydantic,
  seguridad `X-API-Key`, errores de dominio) y `bootstrap.py`.
- Pruebas de contrato que pasan igual contra la app anterior y la nueva.
- Encabezado `X-Duplicate: true` en detecciones repetidas.
- Integración continua con PostgreSQL 16.

## [2.2.0] - 2026-10-14

Fases 2, 3 y 4.

### Agregado
- Estructuras de datos en el dominio: heap con índice, lista doble acotada,
  cola enlazada y deduplicador de ventana deslizante.
- Puertos de la aplicación con implementaciones en memoria para pruebas.
- Casos de uso de registro, revisión, consultas, métricas y catálogos.

## [2.1.0] - 2026-10-14

Fases 0 y 1.

### Agregado
- `pyproject.toml`, ruff, pytest y estructura de pruebas.
- Dominio puro: errores, value objects y entidades con sus reglas.
- Prueba de arquitectura que impide frameworks en el dominio.

### Seguridad
- `X-API-Key` comparada en tiempo constante; la app no arranca sin
  `IOT_API_KEY`.
- `.env.example` y README sin datos reales.

## [2.0.0]

Versión inicial desplegada: API FastAPI en `app/` con cola de prioridad e
historial en memoria.
