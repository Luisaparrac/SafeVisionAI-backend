# Estructuras de datos del dominio

Implementadas a mano, sin `heapq`, `collections.deque`, `queue` ni `bisect`.
No dependen de ningún framework. La base de datos es la fuente de verdad: estas
estructuras son un índice en memoria que se reconstruye al arrancar.

| Estructura | Archivo | Para qué se usa |
|---|---|---|
| Cola de prioridad (max-heap con índice de posiciones) | `alert_priority_queue.py` | Ordena las alertas pendientes: primero la de mayor severidad y, si empatan, la más antigua. |
| Lista doblemente enlazada acotada | `event_history.py` | Historial de los eventos más recientes, del más nuevo al más antiguo. |
| Cola FIFO enlazada | `linked_queue.py` | Ventana deslizante del deduplicador de detecciones (`application/services/event_deduplicator.py`). |

## Cola de prioridad de alertas

Arreglo que representa un árbol binario completo: los hijos de la posición `i`
están en `2i + 1` y `2i + 2`, y ningún hijo supera a su padre. Un diccionario
`event_id → posición` permite quitar cualquier alerta (no solo la primera)
cuando su evento se revisa.

| Operación | Tiempo |
|---|---|
| `push` | O(log n) |
| `peek` | O(1) |
| `pop` | O(log n) |
| `remove(event_id)` | O(log n) |
| `top(k)` | O(k log k) |
| `len`, `in` | O(1) |

`top(k)` no copia el heap: lo recorre de mejor a peor con un heap auxiliar de
candidatos, porque la siguiente alerta más urgente siempre es la raíz o hija de
una alerta ya tomada.

**Por qué un heap y no una lista ordenada:** cada detección nueva entra en
O(log n) en lugar de O(n), y la más urgente se consulta en O(1).

## Historial de eventos

Lista doblemente enlazada con capacidad máxima y un diccionario
`id → nodo`. Los eventos nuevos entran por la cabeza; al superar la capacidad
se descarta la cola (el más antiguo).

| Operación | Tiempo |
|---|---|
| `add_newest` | O(1) |
| `add_oldest` | O(1) |
| `update` | O(1) |
| `newest(limit)` | O(limit) |
| `len`, `in` | O(1) |

**Por qué doblemente enlazada:** quitar la cola en O(1) exige conocer el nodo
anterior; con el diccionario, actualizar el estado de un evento no requiere
recorrer la lista.

## Cola FIFO enlazada

Lista simplemente enlazada con referencias al frente y al final.

| Operación | Tiempo |
|---|---|
| `enqueue` | O(1) |
| `dequeue` | O(1) |
| `peek` | O(1) |
| `len` | O(1) |

**Uso en el deduplicador:** las detecciones entran en orden de llegada, así que
las que salen de la ventana de tiempo siempre están al frente y se descartan en
O(1) cada una (O(1) amortizado por detección).
