"""Smoke test of the real start command against the PostgreSQL test database.

The command is read from render.yaml and only $PORT is replaced, so this checks
exactly what the hosting platform will run. Excluded from the default run;
execute it with ``pytest -m smoke`` (needs TEST_DATABASE_URL). With SMOKE_BIN_DIR
the server runs from another environment, one with production dependencies only.
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
from websockets.sync.client import connect

from tests.fakes.users import TEST_EMAIL, TEST_NAME, TEST_PASSWORD

pytestmark = pytest.mark.smoke

ROOT = Path(__file__).resolve().parents[2]
KEY = "smoke-key"
PANEL_ORIGIN = "http://localhost:5173"


def start_command() -> str:
    match = re.search(r"^\s*startCommand:\s*(.+)$", (ROOT / "render.yaml").read_text("utf-8"), re.M)
    assert match, "render.yaml has no startCommand"
    return match.group(1).strip()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def send(base: str, method: str, path: str, body: dict | None = None, headers=None):
    """Status, headers and JSON body (None when the answer is not JSON) of one request."""
    data = None if body is None else json.dumps(body).encode()
    all_headers = {"Content-Type": "application/json"} | (headers or {})
    request = urllib.request.Request(base + path, data=data, headers=all_headers, method=method)
    try:
        response = urllib.request.urlopen(request, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        content = response.read()
        is_json = response.headers.get("Content-Type", "").startswith("application/json")
        return response.status, response.headers, json.loads(content) if is_json else None


def call(base: str, method: str, path: str, body: dict | None = None, key: str | None = None):
    status, _, content = send(base, method, path, body, {} if key is None else {"X-API-Key": key})
    return status, content


@pytest.fixture
def server(pg_seeded, tmp_path):
    port = free_port()
    args = shlex.split(start_command().replace("$PORT", str(port)))
    # SMOKE_BIN_DIR points to an environment with only requirements.txt installed, as
    # on the platform (CI sets it); by default, the executables of this environment.
    bin_dir = os.environ.get("SMOKE_BIN_DIR") or str(Path(sys.executable).parent)
    search = os.pathsep.join([bin_dir, os.environ.get("PATH", "")])
    executable = shutil.which(args[0], path=search)
    assert executable, f"{args[0]} not found"
    env = os.environ | {
        "DATABASE_URL": pg_seeded.url.render_as_string(hide_password=False),
        "IOT_API_KEY": KEY,
        "SESSION_SECRET": "smoke-session-secret-0123456789abcdef",
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
    assert call(server, "GET", "/health/ready") == (200, {"status": "ok", "database": "ok"})
    assert call(server, "GET", "/api/eventos")[0] == 401
    assert call(server, "GET", "/api/eventos", key=KEY) == (200, [])
    assert call(server, "GET", "/api/alertas/pendientes", key=KEY) == (200, [])
    metrics = call(server, "GET", "/api/metricas", key=KEY)
    assert metrics == (200, {"total": 0, "pendientes": 0, "alto": 0})

    event = {"camera_id": 1, "event_type": "Caída", "zone_id": 1}
    status, body = call(server, "POST", "/api/eventos", event)
    assert (status, body) == (401, {"detail": "X-API-Key inválida"})

    # The live feed works with the WebSocket support of the production server.
    feed_url = server.replace("http://", "ws://") + "/ws/alertas"
    with connect(feed_url, additional_headers={"X-API-Key": KEY}, open_timeout=10) as feed:
        status, created = call(server, "POST", "/api/eventos", event, key=KEY)
        assert status == 201
        message = json.loads(feed.recv(timeout=10))
    assert message["tipo"] == "alerta_nueva"
    assert message["alerta"]["event"] == created
    assert (created["type"], created["location"], created["status"]) == (
        "Caída",
        "Casa · Escalera",
        "Pendiente",
    )
    assert call(server, "GET", "/api/eventos", key=KEY)[1] == [created]
    status, alerts = call(server, "GET", "/api/alertas/pendientes", key=KEY)
    assert [alert["event"] for alert in alerts] == [created]
    metrics = call(server, "GET", "/api/metricas", key=KEY)[1]
    assert metrics == {"total": 1, "pendientes": 1, "alto": 1}


def test_start_command_serves_the_panel_session(server):
    """Login, session, a protected route, CORS with credentials, the ticket and logout.

    The server runs on plain http here, where clients do not send Secure cookies
    back, so the cookie is copied by hand; browsers do it over https.
    """
    credentials = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
    status, _, body = send(server, "POST", "/api/auth/login", credentials | {"password": "mala"})
    assert (status, body) == (401, {"detail": "Correo o contraseña incorrectos"})

    status, headers, body = send(server, "POST", "/api/auth/login", credentials)
    session = {"authenticated": True, "user": {"id": 1, "name": TEST_NAME, "email": TEST_EMAIL}}
    assert (status, body) == (200, session)
    set_cookie = headers["Set-Cookie"]
    assert {"HttpOnly", "Secure", "Path=/", "SameSite=none"} <= {
        part.strip() for part in set_cookie.split(";")
    }
    cookie = {"Cookie": set_cookie.split(";")[0]}
    panel = cookie | {"Origin": PANEL_ORIGIN}

    assert send(server, "GET", "/api/auth/me", headers=cookie)[::2] == (200, session)
    assert send(server, "GET", "/api/auth/me")[0] == 401
    assert send(server, "GET", "/api/eventos", headers=cookie)[::2] == (200, [])
    assert send(server, "GET", "/api/eventos")[0] == 401

    # The browser of the panel: preflight and credentialed answer for its exact origin.
    preflight = {
        "Origin": PANEL_ORIGIN,
        "Access-Control-Request-Method": "PATCH",
        "Access-Control-Request-Headers": "content-type",
    }
    status, headers, _ = send(server, "OPTIONS", "/api/eventos/1/revisar", headers=preflight)
    assert status == 200
    assert headers["Access-Control-Allow-Origin"] == PANEL_ORIGIN
    assert headers["Access-Control-Allow-Credentials"] == "true"
    _, headers, _ = send(server, "GET", "/api/metricas", headers=panel)
    assert headers["Access-Control-Allow-Origin"] == PANEL_ORIGIN
    assert headers["Access-Control-Allow-Credentials"] == "true"

    # A change with the cookie: from the panel it works, from another site it does not.
    status, created = call(
        server, "POST", "/api/eventos", {"camera_id": 2, "event_type_id": 3}, KEY
    )
    assert status == 201
    path = f"/api/eventos/{created['id']}/revisar"
    evil = cookie | {"Origin": "https://evil.example"}
    assert send(server, "PATCH", path, headers=evil)[0] == 403
    status, _, reviewed = send(server, "PATCH", path, headers=panel)
    assert (status, reviewed["status"]) == (200, "Revisado")

    status, _, ticket = send(server, "GET", "/api/auth/ws-ticket", headers=cookie)
    assert (status, ticket["expires_in"]) == (200, 60)
    feed_url = server.replace("http://", "ws://") + "/ws/alertas?ticket=" + ticket["ticket"]
    with connect(feed_url, open_timeout=10) as feed:
        assert call(server, "POST", "/api/eventos", {"camera_id": 1, "event_type_id": 1}, KEY)[0]
        assert json.loads(feed.recv(timeout=10))["tipo"] == "alerta_nueva"

    status, headers, body = send(server, "POST", "/api/auth/logout", headers=panel)
    assert (status, body) == (204, None)
    assert "Max-Age=0" in headers["Set-Cookie"]
