"""Protection of the endpoints: X-API-Key for the IoT module, session cookie for the panel."""

import hmac

from fastapi import Depends, Header, HTTPException, Request

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.dependencies import get_container
from safevision.adapters.inbound.http.sessions import SESSION, SESSION_COOKIE
from safevision.application.dto import UserView

NOT_AUTHENTICATED = "Inicia sesión para continuar"


def require_iot_key(
    x_api_key: str | None = Header(default=None),
    container: Container = Depends(get_container),
) -> None:
    """Rejects the request with 401 unless X-API-Key matches the configured key.

    The comparison takes constant time, so the key cannot be guessed from how
    long the answer takes.
    """
    provided = (x_api_key or "").encode()
    if not hmac.compare_digest(provided, container.iot_api_key.encode()):
        raise HTTPException(401, "X-API-Key inválida")


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
