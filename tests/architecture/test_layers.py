"""Dependency rules between layers, checked statically with ``ast``.

Direction allowed: adapters -> application -> domain. Never the other way.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "safevision"

FRAMEWORKS = {"fastapi", "pydantic", "sqlalchemy", "starlette", "psycopg", "dotenv", "uvicorn"}

RULES = {
    "domain": FRAMEWORKS | {"safevision.application", "safevision.adapters", "safevision.config"},
    "application": FRAMEWORKS | {"safevision.adapters", "safevision.config"},
}


def imported_modules(source: str) -> set[str]:
    """Absolute module names imported by the source (relative imports are ignored)."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def violations(source: str, forbidden: set[str]) -> set[str]:
    return {
        module
        for module in imported_modules(source)
        for prefix in forbidden
        if module == prefix or module.startswith(prefix + ".")
    }


def layer_files(layer: str) -> list[Path]:
    return sorted((SRC / layer).rglob("*.py"))


@pytest.mark.parametrize("layer", sorted(RULES))
def test_layer_has_no_forbidden_imports(layer):
    files = layer_files(layer)
    assert files, f"layer {layer} not found"
    found = {
        str(path.relative_to(SRC)): sorted(bad)
        for path in files
        if (bad := violations(path.read_text(encoding="utf-8"), RULES[layer]))
    }
    assert found == {}


def test_checker_detects_violations():
    source = "import os\nfrom sqlalchemy.orm import Session\nimport fastapi\nfrom . import x\n"
    assert violations(source, RULES["domain"]) == {"sqlalchemy.orm", "fastapi"}


def test_checker_does_not_confuse_similar_names():
    assert violations("import pydantic_settings_like\n", {"pydantic"}) == set()
    assert violations("from safevision.domain import x\n", RULES["application"]) == set()


DDL_CALLS = ("create_all", "drop_all", "CREATE TABLE", "ALTER TABLE", "DROP TABLE")


def test_source_never_runs_ddl():
    """The production tables belong to another role: the backend only reads and writes rows."""
    found = {
        str(path.relative_to(SRC)): [call for call in DDL_CALLS if call in text]
        for path in sorted(SRC.rglob("*.py"))
        if any(call in (text := path.read_text(encoding="utf-8")) for call in DDL_CALLS)
    }
    assert found == {}
