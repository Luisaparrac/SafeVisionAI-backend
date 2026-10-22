"""Login of the panel with an e-mail and password of the users table.

The session travels in the ``sv_session`` cookie (see ``sessions``); the
browser keeps it and sends it back, so the panel never handles the token.
"""

from fastapi import APIRouter, Depends, Response

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.dependencies import get_container
from safevision.adapters.inbound.http.schemas import LoginIn, SessionOut
from safevision.adapters.inbound.http.security import require_session
from safevision.application.dto import UserView

router = APIRouter(prefix="/api/auth", tags=["autenticación"])


@router.post(
    "/login",
    response_model=SessionOut,
    summary="Iniciar sesión",
    responses={
        401: {"description": "Correo o contraseña incorrectos"},
        429: {"description": "5 intentos fallidos con ese correo en 15 minutos"},
    },
)
def login(
    data: LoginIn, response: Response, container: Container = Depends(get_container)
) -> SessionOut:
    """Checks the credentials and opens a session cookie (HttpOnly, Secure).

    The e-mail is compared in lower case. Any failure answers 401 with the same
    message, whether the e-mail exists or not. After 5 failures with one e-mail
    in 15 minutes that e-mail gets 429 until the oldest failure is 15 minutes old.
    """
    user = container.authenticate_user.execute(data.email, data.password)
    container.sessions.start(response, user.id)
    return SessionOut.from_view(user)


@router.get(
    "/me",
    response_model=SessionOut,
    summary="Usuario actual de la sesión",
    responses={401: {"description": "Sin sesión, sesión expirada o usuario eliminado"}},
)
def me(user: UserView = Depends(require_session)) -> SessionOut:
    """The panel calls it on load to know whether it must show the login form."""
    return SessionOut.from_view(user)


@router.post(
    "/logout",
    status_code=204,
    response_class=Response,
    summary="Cerrar sesión",
)
def logout(container: Container = Depends(get_container)) -> Response:
    """Expires the session cookie. Works without a session too, so repeating it is harmless."""
    response = Response(status_code=204)
    container.sessions.end(response)
    return response
