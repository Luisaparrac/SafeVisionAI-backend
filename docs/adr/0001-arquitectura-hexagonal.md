# ADR 0001: Arquitectura hexagonal con migración por estrangulamiento

- **Estado:** aceptada
- **Fecha:** 2026-10-14

## Contexto

La primera versión del backend (`app/`) mezclaba en los mismos módulos las rutas
de FastAPI, las consultas SQLAlchemy, la traducción a etiquetas del panel y las
estructuras de datos. Probar una regla de negocio exigía una base de datos, y
cambiar de tecnología habría obligado a tocar todo. La retroalimentación del
curso pidió explícitamente arquitectura hexagonal.

Además, el backend ya estaba en producción: el panel web y el módulo IoT
dependían de sus rutas y de la forma exacta de sus respuestas.

## Decisión

1. Organizar el código en `src/safevision/` en tres capas con dependencias
   hacia el centro: **dominio** (entidades, value objects y estructuras de
   datos, sin frameworks), **aplicación** (casos de uso y puertos como
   `typing.Protocol`) y **adaptadores** (FastAPI de entrada; SQLAlchemy, reloj
   y WebSocket de salida). `bootstrap.py` es la única raíz de composición.
2. Construir la versión nueva **en paralelo** a `app/` (patrón estrangulador) y
   cambiar el arranque solo cuando las pruebas de contrato pasaran igual contra
   ambas. `app/` se eliminó después de verificar la nueva en producción.
3. Hacer cumplir la regla de dependencias con una prueba que recorre los
   imports con `ast`, no solo con la convención.

## Consecuencias

- Las reglas del dominio y los casos de uso se prueban sin base de datos, con
  repositorios en memoria que respetan los mismos puertos.
- Las pruebas de contrato corren las mismas peticiones contra la app con
  adaptadores en memoria y con PostgreSQL.
- Hay más archivos y una capa de traducción (mappers ORM ↔ dominio y esquemas
  HTTP ↔ DTO) que antes no existía. Se acepta por la independencia que da.
- El cambio de arranque fue un único commit en `render.yaml`, reversible.

## Alternativas consideradas

- **Refactorizar `app/` en el lugar:** más rápido, pero cada paso intermedio
  arriesgaba romper producción sin una red de seguridad.
- **Capas tradicionales (controlador → servicio → repositorio) sin puertos:**
  dejaba al servicio dependiendo de SQLAlchemy.
