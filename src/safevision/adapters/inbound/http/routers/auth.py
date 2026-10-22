"""Login of the panel with an e-mail and password of the users table.

The session travels in the ``sv_session`` cookie (see ``sessions``); the
browser keeps it and sends it back, so the panel never handles the token.
"""

from fastapi import APIRouter, Depends, Response

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.dependencies import get_container
from safevision.adapters.inbound.http.schemas import LoginIn, SessionOut

router = APIRouter(prefix="/api/auth", tags=["autenticación"])


@router.post(
    "/login",
    response_model=SessionOut,
    summary="Iniciar sesión",
    responses={401: {"description": "Correo o contraseña incorrectos"}},
)
def login(data: LoginIn, response: Response, container: Container = Depends(get_container)):
    """Checks the credentials and opens a session cookie (HttpOnly, Secure).

    The e-mail is compared in lower case. Any failure answers 401 with the same
    message, whether the e-mail exists or not.
    """
    user = container.authenticate_user.execute(data.email, data.password)
    container.sessions.start(response, user.id)
    return SessionOut.from_view(user)
