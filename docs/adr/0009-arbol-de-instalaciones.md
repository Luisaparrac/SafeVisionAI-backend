# ADR 0009: Árbol de instalaciones construido en cada petición

- **Estado:** aceptada
- **Fecha:** 2026-11-08

## Contexto

El panel necesita ver qué ubicación, qué cámara y qué zona tienen lo más grave.
La base ya modela esa jerarquía, pero sumar por niveles sobre listas planas
obliga a repetir el recorrido en cada nivel. El resumen debe coincidir con los
pendientes de la cola de alertas y no puede cambiar el esquema (ADR 0002).

## Decisión

1. `GET /api/instalaciones` construye un **árbol n-ario en memoria** con las
   ubicaciones, las cámaras y las zonas, y cuenta en él los eventos pendientes.
2. Un **postorden** propaga los totales y la severidad máxima hacia arriba y
   arma la respuesta en la misma pasada.
3. El árbol se **construye en cada petición** desde PostgreSQL. No se conserva
   entre peticiones ni se cachea.
4. La raíz es interna: la respuesta solo expone sus totales.
5. `NaryTree` contiene solo las operaciones que usa el sistema: agregar un hijo,
   buscar por clave y recorrer en postorden.
6. **Datos incoherentes.** Una cámara o zona cuyo padre no existe, o un evento
   abierto con una cámara o un tipo inexistente, son errores (`NotFoundError`),
   como en `EventPresenter` y `RebuildAlertBoard`: omitirlos desajustaría el
   total. La zona de un evento es opcional, así que una zona inexistente o de
   otra cámara cuenta en la cámara del evento, como la que rechaza
   `RegisterEvent`.

## Consecuencias

- Cada petición cuesta O(n log n + p): n nodos, ordenados por nombre, y p eventos
  pendientes. Hace cuatro lecturas de catálogo y una de eventos.
- El resultado siempre refleja la base, también si alguien cambia un catálogo
  directamente en ella, para lo cual la aplicación no recibe ningún aviso.
- Cada petición tiene su propio árbol, así que no hacen falta candados.
- Una instalación tiene pocas ubicaciones, cámaras y zonas, y los eventos
  pendientes se atienden y salen del conteo. Si la cantidad de pendientes
  creciera mucho, la lectura de eventos sería lo primero en optimizar.
- Entre dos lecturas puede confirmarse un cambio, y el total puede diferir por
  un instante de `/api/metricas`, igual que dos consultas consecutivas.

## Alternativas descartadas

- **Mantener el árbol sincronizado en memoria:** cada evento revisado y cada
  cambio de catálogo tendría que actualizarlo, y los catálogos se editan fuera
  de la aplicación, sin aviso.
- **Cachear con expiración:** el panel mostraría conteos viejos justo cuando se
  atiende una alerta, a cambio de ahorrar poco en un volumen pequeño.
- **Agregar con SQL:** resuelve los conteos, pero repartiría la regla de
  "pendiente" y la de la zona de un evento entre la aplicación y las consultas.
