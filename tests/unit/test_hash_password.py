"""The hash script only asks, hashes and prints (no database, no files)."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fakes.users import FAST_HASHER

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "hash_password.py"
spec = importlib.util.spec_from_file_location("hash_password", SCRIPT)
hash_password = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hash_password)


def answers(*values):
    pending = list(values)
    return lambda prompt: pending.pop(0)


def test_prints_a_hash_that_verifies():
    encoded = hash_password.main(answers("clave-larga", "clave-larga"), FAST_HASHER)
    assert FAST_HASHER.verify("clave-larga", encoded)
    assert "clave-larga" not in encoded


def test_production_hasher_by_default(monkeypatch):
    monkeypatch.setattr(hash_password.Pbkdf2PasswordHasher, "hash", lambda self, p: "hashed")
    assert hash_password.main(answers("clave-larga", "clave-larga")) == "hashed"


@pytest.mark.parametrize(
    ("first", "second", "message"),
    [
        ("corta", "corta", "al menos 8 caracteres"),
        ("clave-larga", "clave-distinta", "no coinciden"),
    ],
)
def test_rejected_passwords(first, second, message):
    with pytest.raises(SystemExit) as info:
        hash_password.main(answers(first, second), FAST_HASHER)
    assert message in str(info.value.code)


def test_never_touches_a_database():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "sqlalchemy" not in source.lower()
    assert "DATABASE_URL" not in source


def test_runs_as_a_script_from_any_directory(tmp_path):
    # getpass reads the terminal, so the child process replaces it before running the script.
    code = (
        "import getpass, runpy; getpass.getpass = lambda prompt: 'corta'; "
        f"runpy.run_path({str(SCRIPT)!r}, run_name='__main__')"
    )
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
        timeout=60,
    )
    assert result.returncode == 1, result.stderr
    assert "al menos 8 caracteres" in result.stderr
