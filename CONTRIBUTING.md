# Cómo contribuir

## Preparar el entorno

```bash
python -m venv .venv
.venv\Scripts\activate             # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install                 # corre los chequeos del CI antes de cada commit
```

Para probar contra PostgreSQL sin tocar ninguna base real, usa `docker compose`
(ver el README) o define `TEST_DATABASE_URL` con una base local cuyo nombre
termine en `_test`.

## Ramas y pull requests

- **Nunca se trabaja ni se hace push directamente a `main`.** Cada push a
  `main` redespliega producción.
- Trabaja en una rama: `feat/<tema>`, `fix/<tema>`, `docs/<tema>`… (la
  refactorización usó `refactor/hexagonal`).
- Haz push de tu rama y abre un pull request hacia `main`. El CI debe estar en
  verde antes de fusionar.
- Fusiona con **"Create a merge commit"**. No uses "Squash and merge" ni
  "Rebase and merge": se conserva cada commit con su mensaje.
- No reescribas historial publicado: nada de `push --force`, `rebase` ni
  `commit --amend` sobre commits que ya están en el remoto.
- Avisa al equipo del panel y del módulo IoT antes de fusionar cambios que
  ellos deban conocer (rutas nuevas, mensajes nuevos del WebSocket).

## Mensajes de commit

[Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/) en
español, modo imperativo, primera línea de 72 caracteres o menos:

```
tipo(ámbito): descripción en imperativo

Cuerpo opcional que explica el porqué, no el qué.
```

| Tipo | Uso |
|---|---|
| `feat` | Funcionalidad nueva |
| `fix` | Corrección de un error |
| `refactor` | Cambio de código que no altera el comportamiento |
| `test` | Solo pruebas |
| `docs` | Solo documentación |
| `build`, `ci` | Empaquetado, dependencias o integración continua |
| `chore`, `style`, `perf` | Mantenimiento, formato, rendimiento |

Ámbitos habituales: `domain`, `structures`, `application`, `persistence`,
`api`, `config`, `security`, `deps`, `ci`, `docs`, `tests`, `scripts`.

Ejemplo: `feat(api): agregar estadísticas de eventos por tipo y por cámara`.

## Qué debe cumplir cada commit

- **Un commit, un cambio lógico completo**, con sus pruebas en el mismo commit.
- **Deja el proyecto funcionando.** Antes de cada commit:

  ```bash
  ruff check . && ruff format --check . && vulture && mypy && pytest
  ```

  (pre-commit lo hace por ti).
- Sin commits vacíos, de solo espacios ni cambios partidos artificialmente.

## Reglas del proyecto

- **Contrato HTTP.** Las rutas, parámetros y formas JSON que usan el panel y el
  módulo IoT no cambian; se pueden agregar parámetros opcionales y rutas
  nuevas. Las pruebas de `tests/contract` nunca se debilitan para que pasen:
  si fallan, el error está en el código.
- **Capas.** `domain` no importa frameworks y `application` no importa
  adaptadores; la prueba de arquitectura lo verifica.
- **Base de datos.** Nunca DDL contra la base real. Las pruebas de integración
  usan solo `TEST_DATABASE_URL`.
- **Estructuras de datos** hechas a mano (sin `heapq`, `collections.deque`,
  `queue` ni `bisect`), con la complejidad de cada operación documentada.
- **Secretos.** Nada de contraseñas, claves, hosts, usuarios, IPs o URLs reales
  en código, pruebas, documentación o mensajes de commit. Usa marcadores
  (`HOST`, `PASSWORD`) y ejemplos ficticios (`example.com`, `192.0.2.x`); una
  prueba revisa la documentación.
- **Idioma.** Identificadores y docstrings en inglés; mensajes de commit,
  documentación y mensajes de error para el usuario en español.
- **Python 3.12**, la versión de producción: no uses sintaxis exclusiva de
  versiones posteriores.
