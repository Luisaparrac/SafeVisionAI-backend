# Estructuras de datos

SafeVision usa estas estructuras implementadas a mano, sin `heapq`,
`collections.deque`, `queue` ni `bisect`. Viven en el dominio
(`src/safevision/domain/structures`) y en la aplicación
(`application/services/event_deduplicator.py`), no dependen de ningún
framework y documentan en su docstring la complejidad de cada operación.

| Estructura | Problema que resuelve | Dónde se usa |
|---|---|---|
| [Max-heap con índice de posiciones](#1-cola-de-prioridad-de-alertas-max-heap-con-índice) | Atender primero la alerta más urgente y quitar la de un evento ya revisado | `AlertBoard` → `GET /api/alertas/pendientes`, `GET /api/metricas` |
| [Lista doblemente enlazada acotada](#2-historial-reciente-lista-doblemente-enlazada-acotada) | Mantener los N eventos más recientes y actualizar su estado sin recorrerlos | `AlertBoard` → `GET /api/eventos/recientes` |
| [Cola FIFO enlazada](#3-cola-fifo-enlazada) | Descartar en orden de llegada lo que sale de una ventana de tiempo | Dentro del deduplicador |
| [Deduplicador de ventana deslizante](#4-deduplicador-de-detecciones-cola--diccionario) | Reconocer detecciones repetidas del IoT en O(1) | `RegisterEvent` → `POST /api/eventos` |
| [Árbol n-ario](#5-árbol-n-ario-de-instalaciones) | Resumir los pendientes y la severidad máxima por ubicación, cámara y zona | `GetInstallations` → `GET /api/instalaciones` |
| [Límite de intentos](#6-límite-de-intentos-cola--diccionario) | Frenar inicios de sesión fallidos, registros y solicitudes de recuperación | `SlidingWindowLimiter` → `/api/auth/*` |

**Relación con la base de datos.** PostgreSQL es la fuente de verdad. Las
estructuras son índices en memoria: al arrancar, `RebuildAlertBoard` las
reconstruye con los eventos abiertos y los más recientes, y cada caso de uso
las actualiza **después** de confirmar la transacción. Si el proceso se
reinicia no se pierde nada; si la base falla, la memoria no queda con datos
que no existen. El árbol n-ario es la excepción: no se conserva entre
peticiones, se construye desde la base cada vez
([ADR 0009](adr/0009-arbol-de-instalaciones.md)).

**Concurrencia.** El servidor atiende peticiones en varios hilos. `AlertBoard`
y `EventDeduplicator` protegen sus estructuras con un `threading.Lock`, de
modo que cada operación es atómica; las estructuras en sí no usan candados.

---

## 1. Cola de prioridad de alertas: max-heap con índice

Archivo: `domain/structures/alert_priority_queue.py` (`AlertPriorityQueue`).

### Problema

El panel muestra las alertas pendientes en orden de atención. Llegan en
cualquier momento (cada detección del IoT), se consulta seguido cuál es la más
urgente, y una alerta sale de la cola cuando su evento se revisa o se marca
como falsa alarma, **sin importar en qué posición esté**.

### Orden

`AlertEntry.outranks` define un orden total y determinista:

1. mayor severidad primero (4 > 3 > 2 > 1);
2. a igual severidad, la alerta más antigua primero (`created_at` menor);
3. a igual instante, el `event_id` menor.

El tercer criterio hace que dos alertas nunca empaten, así el resultado no
depende del orden de inserción.

### Representación

Un arreglo `_heap` guarda un **árbol binario completo**: la raíz está en la
posición 0 y los hijos de la posición `i` en `2i + 1` y `2i + 2` (el padre de
`i` está en `(i − 1) // 2`). La propiedad de heap es: *ningún nodo supera a su
padre* según `outranks`, por lo que la raíz es siempre la alerta más urgente.

Un diccionario `_position: event_id → posición` acompaña al arreglo. Cada vez
que dos elementos se intercambian (`_swap`) se actualiza el diccionario, así
que siempre se sabe en O(1) dónde está la alerta de un evento.

```
            [0] Caída sev 4 (08:00)
           /                       \
  [1] Humo sev 3 (08:05)    [2] Caída sev 4 (08:10)
     /                \
[3] Ruido sev 1   [4] Merodeo sev 2

_heap     = [Caída08:00, Humo, Caída08:10, Ruido, Merodeo]
_position = {e1: 0, e2: 1, e3: 2, e4: 3, e5: 4}
```

(El heap no está ordenado: `[2]` supera a `[1]`, pero solo se exige que cada
hijo no supere a su padre.)

### Operaciones

| Operación | Tiempo | Cómo funciona |
|---|---|---|
| `push(entry)` | O(log n) | Agrega al final y **sube** (`_sift_up`) intercambiando con el padre mientras lo supere. Rechaza un `event_id` repetido en O(1) con el índice. |
| `peek()` | O(1) | Devuelve `_heap[0]`. |
| `pop()` | O(log n) | Quita la raíz con `_remove_at(0)`. |
| `remove(event_id)` | O(log n) | Busca la posición en el índice (O(1)), pone el último elemento en el hueco y lo **sube o baja** según haga falta. |
| `top(k)` | O(k log k) | Las k más urgentes, en orden, sin modificar el heap (ver abajo). |
| `len`, `in` | O(1) | Tamaño del arreglo y búsqueda en el índice. |

Espacio: O(n) para el arreglo y O(n) para el índice.

**Por qué `remove` sube *o* baja.** El último elemento que llena el hueco
puede ser mejor que el nuevo padre (si venía de otra rama) o peor que sus
nuevos hijos. `_remove_at` llama a `_sift_up` y después a `_sift_down` sobre
la posición donde quedó; solo uno de los dos lo mueve. Cada uno recorre como
máximo la altura del árbol, ⌊log₂ n⌋.

**Cómo funciona `top(k)`.** Copiar el heap y hacer k `pop` costaría O(n + k
log n). En cambio, `top` recorre el heap "de mejor a peor" con un heap
auxiliar de **posiciones candidatas**: empieza con la raíz; cada vez que toma
la mejor candidata, agrega sus dos hijos. La siguiente alerta más urgente
siempre es la raíz o hija de una ya tomada (porque ningún hijo supera a su
padre), así que nunca se consideran más de 2k candidatas: cada una de las k
extracciones cuesta O(log k). El endpoint pide como máximo 100.

### Uso en el sistema

- `RegisterEvent` hace `push` de la alerta nueva.
- `ReviewEvent` y `MarkFalseAlarm` hacen `remove(event_id)`: la alerta puede
  estar en cualquier posición, y por eso existe el índice.
- `GetPendingAlerts` usa `top(limit)` para `GET /api/alertas/pendientes`.
- `GetMetrics` usa `len` para el contador de pendientes.
- `RebuildAlertBoard` hace un `push` por evento abierto al arrancar.

### Alternativas descartadas

| Alternativa | Insertar | Más urgente | Quitar una cualquiera | Problema |
|---|---|---|---|---|
| Lista sin ordenar | O(1) | O(n) | O(n) | Cada consulta del panel recorre todo. |
| Lista ordenada | O(n) | O(1) | O(n) | Cada detección desplaza elementos. |
| Heap sin índice | O(log n) | O(1) | O(n) | Hay que buscar la alerta antes de quitarla. |
| **Heap con índice** | **O(log n)** | **O(1)** | **O(log n)** | — |

### Pruebas

`tests/unit/structures/test_alert_priority_queue_properties.py` hace miles de
inserciones y eliminaciones aleatorias (con semillas fijas) y comprueba tras
cada operación que la raíz es la más urgente, que el índice coincide con el
arreglo y que vaciar la cola devuelve todo en orden de prioridad.

---

## 2. Historial reciente: lista doblemente enlazada acotada

Archivo: `domain/structures/event_history.py` (`EventHistory`).

### Problema

`GET /api/eventos/recientes` devuelve los últimos eventos sin consultar la
base. Los eventos nuevos entran por un extremo y, al llenarse, sale el más
antiguo por el otro. Además, cuando se revisa un evento su estado debe cambiar
en el historial sin moverlo de lugar.

### Representación

Nodos con `key` (id del evento), `value` (la vista del evento), `prev` y
`next`. La lista guarda la **cabeza** (el más nuevo) y la **cola** (el más
antiguo), una capacidad máxima (`HISTORY_CAPACITY`, 100 por defecto) y un
diccionario `id → nodo`.

```
cabeza                                         cola
  ↓                                             ↓
[e9] ⇄ [e8] ⇄ [e7] ⇄ … ⇄ [e2] ⇄ [e1]      índice = {9: nodo, 8: nodo, …}
```

### Operaciones

| Operación | Tiempo | Cómo funciona |
|---|---|---|
| `add_newest(id, vista)` | O(1) | Enlaza un nodo antes de la cabeza; si se supera la capacidad, descarta la cola. Si el id ya existe, solo actualiza su valor. |
| `add_oldest(id, vista)` | O(1) | Enlaza después de la cola; sirve para reconstruir desde filas ordenadas de la más nueva a la más antigua. |
| `update(id, vista)` | O(1) | Encuentra el nodo con el índice y reemplaza su valor sin moverlo. |
| `newest(limit)` | O(limit) | Recorre desde la cabeza. |
| `len`, `in` | O(1) | Tamaño e índice. |

Espacio: O(capacidad), nunca crece más allá.

**Por qué doblemente enlazada.** Descartar la cola en O(1) exige llegar al
penúltimo nodo sin recorrer la lista: el puntero `prev` de la cola lo da
directamente. Con una lista simple habría que recorrer n − 1 nodos.

**Por qué el diccionario.** Sin él, actualizar el estado de un evento
revisado obligaría a buscarlo recorriendo la lista (O(n)).

### Uso en el sistema

- `RegisterEvent` → `add_newest`.
- `ReviewEvent` y `MarkFalseAlarm` → `update` (el evento sigue en su lugar
  pero ahora dice "Revisado").
- `GetRecentEvents` → `newest(limit)`.
- `RebuildAlertBoard` → `add_oldest` con los eventos más recientes de la base.

### Alternativas descartadas

Un arreglo con `insert(0, …)` cuesta O(n) por inserción; una cola circular
sobre arreglo da O(1) en los extremos, pero actualizar por id seguiría siendo
O(n) sin un índice que se mantenga al desplazar elementos.

---

## 3. Cola FIFO enlazada

Archivo: `domain/structures/linked_queue.py` (`LinkedQueue`).

### Representación

Lista **simplemente** enlazada con punteros al **frente** (el próximo en
salir) y al **final** (el último en llegar), más un contador.

```
frente                         final
  ↓                              ↓
[a] → [b] → [c] → [d] → None
```

### Operaciones

| Operación | Tiempo | Cómo funciona |
|---|---|---|
| `enqueue(x)` | O(1) | Enlaza un nodo después del final. |
| `dequeue()` | O(1) | Avanza el frente; si queda vacía, también limpia el final. |
| `peek()` | O(1) | Valor del frente. |
| `len`, `bool` | O(1) | Contador. |

Espacio: O(n).

**Por qué basta una lista simple.** Solo se agrega por un extremo y se quita
por el otro; nunca hace falta el nodo anterior, así que `prev` sobraría.

---

## 4. Deduplicador de detecciones: cola + diccionario

Archivo: `application/services/event_deduplicator.py` (`EventDeduplicator`).

### Problema

La cámara reporta la misma situación varias veces por segundo. Sin control,
una caída generaría decenas de eventos y alertas. Una detección es
**repetida** si la misma combinación `(camera_id, event_type_id, subject_id)`
se registró hace menos de `DEDUP_WINDOW_SECONDS` (60 s por defecto). La
ventana cuenta desde la primera detección: una situación que dura produce una
alerta por ventana, no una por detección (ver
[ADR 0003](adr/0003-deduplicacion-60-segundos.md)).

### Representación

Dos estructuras trabajan juntas:

- una `LinkedQueue` con pares `(clave, instante)` **en orden de llegada**;
- un diccionario `clave → (instante, event_id)` con el último registro de
  cada clave.

```
cola:        [(k1, 10:00:00)] → [(k2, 10:00:20)] → [(k1, 10:01:05)]
diccionario: {k1: (10:01:05, e7), k2: (10:00:20, e5)}
```

### Operaciones

| Operación | Tiempo | Cómo funciona |
|---|---|---|
| `find_recent(clave)` | O(1) amortizado | Expira lo vencido y busca la clave en el diccionario. |
| `remember(clave, event_id)` | O(1) amortizado | Expira, guarda en el diccionario y encola. |
| `_expire(ahora)` | O(1) amortizado | Mientras el frente de la cola esté fuera de la ventana, lo desencola; si coincide con el registro del diccionario, borra la clave. |

Espacio: O(registros dentro de la ventana).

**Por qué la cola.** Como los registros entran en orden de llegada, los
vencidos **siempre están al frente**: expirar nunca recorre la cola completa,
solo saca lo que ya venció y se detiene en el primero vigente.

**Borrado perezoso.** Cuando una clave se vuelve a registrar, su entrada
anterior queda en la cola. Al vencer, ya no coincide con el diccionario (que
tiene el instante nuevo) y simplemente se descarta, sin buscarla.

**Análisis amortizado.** Cada registro se encola una vez y se desencola como
mucho una vez. En una secuencia de m operaciones el trabajo total de
`_expire` es O(m), es decir O(1) amortizado por operación, aunque una
llamada aislada pueda desencolar varios elementos.

### Uso en el sistema

`RegisterEvent` consulta `find_recent` antes de crear el evento. Si hay uno
reciente, responde 201 con ese mismo evento y el encabezado
`X-Duplicate: true`. Solo llama a `remember` después de confirmar la
transacción, para que un fallo de la base no oculte el reintento del IoT. El
reloj se inyecta, así las pruebas controlan el tiempo con un reloj falso.

---

## 5. Árbol n-ario de instalaciones

Archivo: `domain/structures/nary_tree.py` (`NaryTree`), usado por
`application/use_cases/get_installations.py` (`GetInstallations`).

### Problema

El operador necesita ver qué ubicación, qué cámara y qué zona concentran lo más
grave sin revisar los eventos uno por uno. Los datos ya son jerárquicos: una
ubicación tiene cámaras, una cámara tiene zonas y un evento pertenece a una
cámara y, a veces, a una zona. El resumen de cada nivel depende de todo lo que
cuelga de él.

### Por qué un árbol

Las estructuras lineales ordenan los elementos en una sola secuencia: el heap
por urgencia, la lista por antigüedad y la cola por llegada. Ninguna representa
la relación "pertenece a". Con listas planas, el total de una ubicación exigiría
buscar sus cámaras, luego las zonas de cada una y luego sus eventos, y repetirlo
en cada nivel. En un árbol cada elemento tiene un solo padre, así que un total
se calcula una vez y se reutiliza hacia arriba.

### Conceptos en SafeVision

| Concepto | Qué es aquí |
|---|---|
| Raíz | Nodo interno que representa toda la instalación. La respuesta solo expone sus totales. |
| Padre e hijo | La ubicación es padre de sus cámaras y la cámara, de sus zonas. |
| Hermanos | Las cámaras de una misma ubicación o las zonas de una misma cámara. Se ordenan por nombre y luego por id. |
| Hoja | Nodo sin hijos: toda zona, una cámara sin zonas o una ubicación sin cámaras. |
| Rama | Un nodo con todo lo que cuelga de él, como una ubicación con sus cámaras y zonas. |
| Nivel | La distancia a la raíz contada en nodos: raíz 1, ubicaciones 2, cámaras 3 y zonas 4. |
| Altura | El mayor nivel que existe: 4 si hay alguna zona y 1 si no hay ubicaciones. |
| Peso | El total de nodos: la raíz más las ubicaciones, las cámaras y las zonas. |
| Orden | El máximo de hijos que admite un nodo. Aquí no tiene límite, y por eso el árbol es n-ario. |
| Grado | El número de hijos de un nodo. El grado del árbol es el mayor de todos. |

### Representación

Cada nodo guarda `key`, `value`, `parent` y la lista ordenada `children`. El
árbol guarda la raíz y un diccionario `clave → nodo`. Las claves incluyen el
tipo, como `("camera", 3)`, porque una ubicación y una cámara pueden tener el
mismo id.

```
                 raíz
                /    \
            Bodega   Casa
                    /    \
                Patio    Sala
                           \
                         Escalera
```

### Operaciones

| Operación | Tiempo | Cómo funciona |
|---|---|---|
| `add_child(padre, clave, valor)` | O(1) | Busca al padre en el índice y agrega el nodo al final de sus hijos. Rechaza un padre inexistente o una clave repetida con `ValueError`. |
| `find(clave)` | O(1) | Consulta el índice. Sirve para ubicar el padre de cada fila y el nodo de cada evento. |
| `postorder()` | O(n) | Devuelve cada nodo después de todos sus hijos y la raíz al final. |

Espacio: O(n). El postorden es recursivo: su pila crece con la altura, que aquí
es como máximo 4.

### Propagar el riesgo en postorden

Cada evento pendiente suma en su zona. Si no tiene zona, si la zona ya no existe
o si es de otra cámara, suma directamente en su cámara. Ese es `own_pending`.

Luego una sola pasada en postorden completa los resúmenes. Cuando se visita un
nodo, sus hijos ya están listos, de modo que:

- `pending` = `own_pending` del nodo + la suma de `pending` de sus hijos;
- `max_severity` = el mayor valor entre la severidad propia y la de sus hijos;
- `priority` sale de `max_severity` con la regla de `Severity.priority`.

La misma pasada arma la respuesta, porque la vista de cada nodo necesita las de
sus hijos.

```
Escalera: propio 2, máx 4   →  pending 2, máx 4
Sala:     propio 1, máx 2   →  pending 1 + 2 = 3, máx 4
Patio:    propio 1, máx 1   →  pending 1, máx 1
Casa:     propio 0          →  pending 3 + 1 = 4, máx 4
raíz:     propio 0          →  pending 4, máx 4
```

"Pendiente" significa lo mismo que en la cola de alertas: los estados agrupados
en `ReviewLabel.PENDING`. Por eso el total de la raíz coincide con
`pendientes` de `/api/metricas`. Un evento abierto con una cámara o un tipo
inexistente es un error y no se omite, porque ocultarlo desajustaría ese total.

### Otros árboles del sistema

- `AlertPriorityQueue` también es un árbol: uno binario completo guardado en un
  arreglo, donde los hijos de la posición `i` están en `2i + 1` y `2i + 2`.
- PostgreSQL resuelve sus claves primarias e índices con árboles B, que
  mantienen las búsquedas en tiempo logarítmico sobre disco.

---

## 6. Límite de intentos: cola + diccionario

Archivo: `application/services/rate_limiter.py` (`SlidingWindowLimiter`).

### Problema

Sin límite, cualquiera podría probar contraseñas una tras otra contra un
correo. Un correo con **5 intentos fallidos en los últimos 15 minutos** queda
bloqueado (`POST /api/auth/login` responde 429) hasta que el más antiguo de
esos fallos cumple 15 minutos. Un inicio de sesión correcto borra su cuenta.

El registro y la recuperación de contraseña reutilizan la clase con claves y
ventanas propias (por dirección y por correo, en una hora). Allí `try_acquire`
comprueba y cuenta bajo el mismo candado, para que dos peticiones simultáneas
no superen el límite.

### Representación

La misma idea que el deduplicador:

- una `LinkedQueue` con ternas `(correo, generación, instante)` de cada fallo,
  **en orden de llegada**;
- un diccionario `correo → (generación, fallos)` con los fallos de cada
  correo que siguen dentro de la ventana.

```
cola:        [(a, 1, 10:00)] → [(b, 2, 10:03)] → [(a, 1, 10:07)]
diccionario: {a: (1, 2), b: (2, 1)}
```

### Operaciones

| Operación | Tiempo | Cómo funciona |
|---|---|---|
| `is_blocked(correo)` | O(1) amortizado | Expira lo vencido y compara los fallos del correo con el máximo. |
| `record_failure(correo)` | O(1) amortizado | Expira, suma un fallo en el diccionario y encola. |
| `clear(correo)` | O(1) | Borra el correo del diccionario. |
| `_expire(ahora)` | O(1) amortizado | Desencola los fallos vencidos del frente y resta uno al correo; si llega a cero, lo borra. |

Espacio: O(fallos dentro de la ventana). Un correo que deja de fallar
desaparece solo, así que la memoria no crece con correos inventados.

**Generaciones.** `clear` no recorre la cola: deja allí los fallos viejos.
Cada cuenta nueva recibe un número de generación distinto, y cuando esos
fallos viejos vencen ya no coinciden con el diccionario y se descartan.

El estado vive en memoria: es por proceso y empieza vacío al reiniciar, lo
que basta para la única instancia del servicio.

---

## Resumen de complejidades

| Estructura | Operación | Tiempo | Espacio |
|---|---|---|---|
| Max-heap con índice | push / pop / remove | O(log n) | O(n) |
| | peek / len / in | O(1) | |
| | top(k) | O(k log k) | |
| Lista doble acotada | add_newest / add_oldest / update | O(1) | O(capacidad) |
| | newest(limit) | O(limit) | |
| Cola enlazada | enqueue / dequeue / peek | O(1) | O(n) |
| Deduplicador | find_recent / remember | O(1) amortizado | O(ventana) |
| Árbol n-ario | add_child / find | O(1) | O(n) |
| | postorder | O(n) | |
| Límite de inicios de sesión | is_blocked / record_failure | O(1) amortizado | O(fallos en la ventana) |
| | clear | O(1) | |
