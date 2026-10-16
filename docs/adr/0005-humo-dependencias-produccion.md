# ADR 0005: Prueba de humo con el comando real y solo dependencias de producción

- **Estado:** aceptada
- **Fecha:** 2026-10-16

## Contexto

Las pruebas unitarias y de contrato usan `TestClient`, que importa la app
dentro del proceso de pytest. Eso no detecta fallos de arranque:

- un error en el comando de `render.yaml` (módulo equivocado, falta
  `--app-dir src`);
- una variable de entorno que la app exige y Render no tiene;
- un paquete que solo está en `requirements-dev.txt` pero que la app usa en
  producción (por ejemplo, la librería de WebSocket).

Render instala únicamente `requirements.txt` y ejecuta `startCommand`. Un fallo
así solo aparecería después de fusionar a `main`, con producción caída.

## Decisión

1. La prueba de humo (`tests/smoke`) **lee `startCommand` de `render.yaml`** y
   solo reemplaza `$PORT`, así que prueba exactamente lo que ejecutará Render.
2. Arranca uvicorn como proceso aparte contra un PostgreSQL de prueba con
   `schema.sql` y comprueba `/health`, `/health/ready`, eventos, alertas,
   métricas, el registro con y sin clave y una alerta recibida por
   `/ws/alertas`.
3. En CI el servidor corre desde un **entorno virtual que instala solo
   `requirements.txt`**; el paso verifica que `pytest` no esté instalado ahí.
   La variable `SMOKE_BIN_DIR` indica de qué entorno tomar `uvicorn`.
4. Se pasan solo las variables que Render ya tiene (`DATABASE_URL`,
   `IOT_API_KEY`, `FRONTEND_ORIGINS`, `TIMEZONE`).
5. El `Dockerfile` usa el mismo comando y solo `requirements.txt`; una prueba
   mantiene iguales el `CMD` y `startCommand`.

## Consecuencias

- El cambio de arranque a la app hexagonal se fusionó con la prueba de humo en
  verde y funcionó en producción al primer intento.
- Quitar una dependencia de `requirements.txt` que la app necesita hace fallar
  el CI antes de llegar a `main`.
- La prueba queda fuera de la corrida normal (`-m "not smoke"`) porque arranca
  un proceso y necesita PostgreSQL; se ejecuta con `pytest -m smoke` y en un
  paso propio del CI.

## Alternativas consideradas

- **Confiar en `TestClient`:** no cubre el comando ni las dependencias reales.
- **Probar solo con Docker:** Render no usa Docker; la imagen podría funcionar
  y el despliegue real no. Se hacen ambas cosas, pero la referencia es
  `render.yaml`.
