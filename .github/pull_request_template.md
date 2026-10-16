## Qué cambia y por qué

<!-- Resume el cambio y el motivo. Enlaza el issue si existe. -->

## Tipo de cambio

- [ ] Funcionalidad nueva (aditiva)
- [ ] Corrección
- [ ] Refactorización sin cambio de comportamiento
- [ ] Documentación, CI o dependencias

## Contrato HTTP

- [ ] No cambia ninguna ruta, parámetro ni forma JSON existente.
- [ ] Agrega rutas o parámetros opcionales (documentados en `docs/api.md`).
- [ ] Hay que avisar al equipo del panel o del módulo IoT antes de fusionar.

## Verificación

- [ ] `ruff check .`, `ruff format --check .`, `vulture`, `mypy` y `pytest` en verde.
- [ ] El CI está en verde (pruebas con PostgreSQL, humo y Docker).
- [ ] Las pruebas de contrato no se modificaron para que pasen.
- [ ] Sin secretos ni datos de infraestructura reales (solo marcadores o `example.com`, `192.0.2.x`).
- [ ] `render.yaml` y `requirements.txt` no cambian, o el cambio está justificado arriba.

## Al fusionar

Usa **"Create a merge commit"** (no squash ni rebase).
