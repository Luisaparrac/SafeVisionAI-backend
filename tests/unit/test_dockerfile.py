"""The Docker image runs what the hosting platform runs (checked without Docker)."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")


def render_start_command() -> str:
    text = (ROOT / "render.yaml").read_text(encoding="utf-8")
    return re.search(r"^\s*startCommand:\s*(.+)$", text, re.M).group(1).strip()


def test_image_starts_with_the_render_command():
    cmd = re.search(r"^CMD (.+)$", DOCKERFILE, re.M).group(1)
    shell, flag, command = json.loads(cmd)
    assert (shell, flag) == ("sh", "-c")
    assert command == render_start_command()


def test_image_installs_only_production_dependencies():
    installs = re.findall(r"pip install [^\n\\]*-r (\S+)", DOCKERFILE)
    assert installs == ["requirements.txt"]
    assert "requirements-dev.txt" not in DOCKERFILE


def test_image_uses_the_python_version_of_the_platform():
    assert re.findall(r"^FROM python:(\S+?)-slim", DOCKERFILE, re.M) == ["3.12", "3.12"]


def test_server_does_not_run_as_root():
    assert re.search(r"^USER app$", DOCKERFILE, re.M)


def test_build_context_leaves_secrets_and_tests_out():
    ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert {".env", ".env.*", "tests", ".git", ".venv"} <= set(ignored)
