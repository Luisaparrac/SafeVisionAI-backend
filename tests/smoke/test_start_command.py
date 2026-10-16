"""Smoke test of the real start command against the PostgreSQL test database.

The command is read from render.yaml and only $PORT is replaced, so this checks
exactly what the hosting platform will run. Excluded from the default run;
execute it with ``pytest -m smoke`` (needs TEST_DATABASE_URL).
"""

import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke

ROOT = Path(__file__).resolve().parents[2]
KEY = "smoke-key"


def start_command() -> str:
    match = re.search(r"^\s*startCommand:\s*(.+)$", (ROOT / "render.yaml").read_text("utf-8"), re.M)
    assert match, "render.yaml has no startCommand"
    return match.group(1).strip()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def call(base: str, method: str, path: str, body: dict | None = None, key: str | None = None):
    headers = {"Content-Type": "application/json"}
    if key is not None:
        headers["X-API-Key"] = key
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


@pytest.fixture
def server(pg_seeded, tmp_path):
    port = free_port()
    args = shlex.split(start_command().replace("$PORT", str(port)))
    # The executable of this environment (the platform runs it from its PATH).
    search = os.pathsep.join([str(Path(sys.executable).parent), os.environ.get("PATH", "")])
    executable = shutil.which(args[0], path=search)
    assert executable, f"{args[0]} not found"
    env = os.environ | {
        "DATABASE_URL": pg_seeded.url.render_as_string(hide_password=False),
        "IOT_API_KEY": KEY,
        "FRONTEND_ORIGINS": "http://localhost:5173",
        "TIMEZONE": "America/Bogota",
        "PORT": str(port),
    }
    # A file, not a pipe: nobody reads the output while the server runs, and a full
    # pipe would block the server once it has logged enough lines.
    output = (tmp_path / "server.log").open("w+", encoding="utf-8")
    process = subprocess.Popen(
        [executable, *args[1:]],
        cwd=ROOT,
        env=env,
        stdout=output,
        stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 30
        while True:
            if process.poll() is not None:
                output.seek(0)
                pytest.fail(f"the server stopped:\n{output.read()}", pytrace=False)
            try:
                if call(base, "GET", "/health")[0] == 200:
                    break
            except OSError:
                pass
            if time.monotonic() > deadline:
                pytest.fail("the server did not answer /health within 30 s", pytrace=False)
            time.sleep(0.3)
        yield base
    finally:
        process.terminate()
        process.wait(timeout=10)
        output.close()


def test_start_command_serves_the_contract(server):
    assert call(server, "GET", "/health") == (200, {"status": "ok"})
    assert call(server, "GET", "/api/eventos") == (200, [])
    assert call(server, "GET", "/api/alertas/pendientes") == (200, [])
    assert call(server, "GET", "/api/metricas") == (200, {"total": 0, "pendientes": 0, "alto": 0})

    event = {"camera_id": 1, "event_type": "Caída", "zone_id": 1}
    status, body = call(server, "POST", "/api/eventos", event)
    assert (status, body) == (401, {"detail": "X-API-Key inválida"})

    status, created = call(server, "POST", "/api/eventos", event, key=KEY)
    assert status == 201
    assert (created["type"], created["location"], created["status"]) == (
        "Caída",
        "Casa · Escalera",
        "Pendiente",
    )
    assert call(server, "GET", "/api/eventos")[1] == [created]
    status, alerts = call(server, "GET", "/api/alertas/pendientes")
    assert [alert["event"] for alert in alerts] == [created]
    assert call(server, "GET", "/api/metricas")[1] == {"total": 1, "pendientes": 1, "alto": 1}
