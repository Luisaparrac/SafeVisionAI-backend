"""Protection of the endpoints: X-API-Key for the IoT module, session cookie for the panel."""

import hmac
from collections.abc import Mapping
from urllib.parse import urlsplit

from fastapi import Depends, Header, HTTPException, Request, WebSocket

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.dependencies import get_container
from safevision.adapters.inbound.http.sessions import SESSION, SESSION_COOKIE, WS_TICKET
from safevision.application.dto import UserView

NOT_AUTHENTICATED = "Inicia sesión para continuar"
# Documented on every /api router.
AUTH_RESPONSES: dict[int | str, dict] = {
    401: {"description": "Sin sesión válida ni X-API-Key válida"},
    403: {"description": "Cambio con cookie enviado desde un origen no permitido"},
}
UNTRUSTED_ORIGIN = "Origen no permitido"
# Methods that change data. Browsers send cookies with them from any site, so
# their origin is checked; GET and HEAD only read and cannot be read cross-site.
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def require_iot_key(
    x_api_key: str | None = Header(default=None),
    container: Container = Depends(get_container),
) -> None:
    """Rejects the request with 401 unless X-API-Key matches the configured key.

    The comparison takes constant time, so the key cannot be guessed from how
    long the answer takes.
    """
    if not _key_matches(x_api_key, container):
        raise HTTPException(401, "X-API-Key inválida")


def _key_matches(provided: str | None, container: Container) -> bool:
    return hmac.compare_digest((provided or "").encode(), container.iot_api_key.encode())


def session_user(request: Request, container: Container) -> UserView | None:
    """The user of a valid session cookie who still exists in the database, or None."""
    token = request.cookies.get(SESSION_COOKIE)
    user_id = None if not token else container.sessions.signer.read(token, SESSION)
    return None if user_id is None else container.get_session_user.execute(user_id)


def require_session(request: Request, container: Container = Depends(get_container)) -> UserView:
    """Rejects the request with 401 unless it carries a valid session cookie."""
    user = session_user(request, container)
    if user is None:
        raise HTTPException(401, NOT_AUTHENTICATED)
    return user


def require_panel_access(
    request: Request,
    x_api_key: str | None = Header(default=None),
    container: Container = Depends(get_container),
) -> None:
    """Routes of the panel: a valid session cookie, or the X-API-Key of the IoT module.

    The key lets the IoT module and the scripts read the catalogs. A request with
    a valid key skips the origin check: browsers never add that header on their
    own, so another site cannot make one carry it.
    """
    if x_api_key is not None and _key_matches(x_api_key, container):
        return
    require_session(request, container)
    ensure_trusted_origin(request, container)


def ensure_trusted_origin(request: Request, container: Container) -> None:
    """Rejects with 403 a cookie-authenticated change sent from another site (CSRF).

    The ``Origin`` header (or, if missing, the origin of ``Referer``) must be one
    of FRONTEND_ORIGINS or the backend itself (the /docs page). The backend is
    recognized by its host only: behind the hosting proxy the request reaches the
    server over http even when the browser used https. A request with neither
    header is rejected, because browsers always send ``Origin`` on these methods.
    """
    if request.method in UNSAFE_METHODS and not _trusted_origin(request.headers, container):
        raise HTTPException(403, UNTRUSTED_ORIGIN)


def _trusted_origin(headers: Mapping[str, str], container: Container) -> bool:
    origin = headers.get("origin") or _origin_of(headers.get("referer"))
    if origin is None:
        return False
    origin = origin.rstrip("/")
    return origin in container.cors_origins or urlsplit(origin).netloc == headers.get("host")


def _origin_of(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else None


def websocket_allowed(websocket: WebSocket, container: Container) -> bool:
    """Whether a client may open the live alert feed. Any one of these is enough:

    * ``?ticket=`` from GET /api/auth/ws-ticket, for pages that cannot send the
      cookie (another site, Safari); it lasts 60 seconds;
    * the X-API-Key header of the IoT module;
    * the session cookie, from a trusted origin: browsers send it with WebSocket
      handshakes from any site, and CORS does not apply to them.

    With a ticket or a cookie the user must still exist. It reads the database,
    so the endpoint runs it in a worker thread.
    """
    ticket = websocket.query_params.get("ticket")
    user_id = None if not ticket else container.sessions.signer.read(ticket, WS_TICKET)
    if user_id is None:
        provided = websocket.headers.get("x-api-key")
        if provided is not None and _key_matches(provided, container):
            return True
        token = websocket.cookies.get(SESSION_COOKIE)
        if token and _trusted_origin(websocket.headers, container):
            user_id = container.sessions.signer.read(token, SESSION)
    return user_id is not None and container.get_session_user.execute(user_id) is not None
