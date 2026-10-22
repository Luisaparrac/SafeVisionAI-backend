"""Protection of the endpoints: X-API-Key for the IoT module, session cookie for the panel."""

import hmac
from urllib.parse import urlsplit

from fastapi import Depends, Header, HTTPException, Request

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.dependencies import get_container
from safevision.adapters.inbound.http.sessions import SESSION, SESSION_COOKIE
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
    if request.method not in UNSAFE_METHODS:
        return
    origin = request.headers.get("origin") or _origin_of(request.headers.get("referer"))
    if origin is not None:
        origin = origin.rstrip("/")
        if origin in container.cors_origins:
            return
        if urlsplit(origin).netloc == request.headers.get("host"):
            return
    raise HTTPException(403, UNTRUSTED_ORIGIN)


def _origin_of(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else None
