"""Protection of the endpoints: X-API-Key for the IoT module, session cookie for the panel."""

import hmac
import ipaddress
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


def client_address(request: Request) -> str:
    """The address the rate limits count by. It only lives in memory: it is never logged.

    The server sits behind proxies, so the connection itself shows the proxy for
    every visitor. CF-Connecting-IP is overwritten by the edge in front of the
    hosting platform; the last entry of X-Forwarded-For is added by the nearest
    proxy. The first entries of that list are sent by the client and can be faked.
    """
    forwarded = request.headers.get("x-forwarded-for", "").rsplit(",", 1)[-1]
    for candidate in (request.headers.get("cf-connecting-ip", ""), forwarded):
        try:
            return str(ipaddress.ip_address(candidate.strip()))
        except ValueError:
            continue
    return request.client.host if request.client else "unknown"


def _key_matches(provided: str | None, container: Container) -> bool:
    return hmac.compare_digest((provided or "").encode(), container.iot_api_key.encode())


def session_user(request: Request, container: Container) -> UserView | None:
    """The user of a valid session cookie who still exists with that password, or None."""
    token = request.cookies.get(SESSION_COOKIE)
    claims = None if not token else container.sessions.signer.read(token, SESSION)
    if claims is None:
        return None
    return container.get_session_user.execute(claims.user_id, claims.fingerprint)


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


def reject_foreign_origin(request: Request, container: Container) -> None:
    """Routes that open a session: there is none to protect yet, so no Origin is required.

    Clients that are not browsers send no Origin; when one comes, it must be trusted.
    """
    if "origin" in request.headers and not _trusted_origin(request.headers, container):
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

    With a ticket or a cookie the user must still exist with the same password.
    It reads the database, so the endpoint runs it in a worker thread.
    """
    ticket = websocket.query_params.get("ticket")
    claims = None if not ticket else container.sessions.signer.read(ticket, WS_TICKET)
    if claims is None:
        provided = websocket.headers.get("x-api-key")
        if provided is not None and _key_matches(provided, container):
            return True
        token = websocket.cookies.get(SESSION_COOKIE)
        if token and _trusted_origin(websocket.headers, container):
            claims = container.sessions.signer.read(token, SESSION)
    if claims is None:
        return False
    return container.get_session_user.execute(claims.user_id, claims.fingerprint) is not None
