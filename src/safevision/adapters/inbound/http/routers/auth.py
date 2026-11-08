"""Login of the panel with an e-mail and password of the users table.

The session travels in the ``sv_session`` cookie (see ``sessions``); the
browser keeps it and sends it back, so the panel never handles the token.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.dependencies import get_container
from safevision.adapters.inbound.http.schemas import (
    AuthOptionsOut,
    ForgotPasswordIn,
    LoginIn,
    MessageOut,
    RegisterIn,
    ResetPasswordIn,
    SessionOut,
    WsTicketOut,
)
from safevision.adapters.inbound.http.security import (
    client_address,
    ensure_trusted_origin,
    reject_foreign_origin,
    require_session,
)
from safevision.adapters.inbound.http.sessions import (
    SESSION_COOKIE,
    WS_TICKET,
    WS_TICKET_LIFETIME,
)
from safevision.application.dto import UserView

router = APIRouter(prefix="/api/auth", tags=["autenticación"])

RESET_REQUESTED = (
    "Si el correo está registrado, recibirás un enlace para restablecer la contraseña."
)


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
    container.sessions.start(response, user)
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
    responses={403: {"description": "Petición con cookie enviada desde un origen no permitido"}},
)
def logout(request: Request, container: Container = Depends(get_container)) -> Response:
    """Expires the session cookie. Works without a session too, so repeating it is harmless.

    With a cookie the origin is checked, so another site cannot end the session.
    """
    if SESSION_COOKIE in request.cookies:
        ensure_trusted_origin(request, container)
    response = Response(status_code=204)
    container.sessions.end(response)
    return response


@router.get(
    "/ws-ticket",
    response_model=WsTicketOut,
    summary="Ticket para el WebSocket de alertas",
    responses={401: {"description": "Sin sesión, sesión expirada o usuario eliminado"}},
)
def ws_ticket(
    user: UserView = Depends(require_session), container: Container = Depends(get_container)
) -> WsTicketOut:
    """Signed ticket, valid for 60 seconds, to open /ws/alertas?ticket=... .

    Useful when the browser does not send the cookie with the WebSocket. It only
    opens the feed: it is not accepted as a session anywhere else.
    """
    ticket = container.sessions.signer.issue(
        user.id, WS_TICKET, WS_TICKET_LIFETIME, user.password_fingerprint
    )
    return WsTicketOut(ticket=ticket, expires_in=int(WS_TICKET_LIFETIME.total_seconds()))


@router.post(
    "/register",
    status_code=201,
    response_model=SessionOut,
    summary="Crear cuenta",
    responses={
        403: {
            "description": "Registro no habilitado, código de invitación inválido "
            "u origen no permitido"
        },
        409: {"description": "Ya existe una cuenta con ese correo"},
        422: {"description": "Nombre, correo o contraseña no cumplen las reglas"},
        429: {"description": "5 intentos de registro desde esa dirección en una hora"},
    },
)
def register(
    data: RegisterIn,
    request: Request,
    response: Response,
    container: Container = Depends(get_container),
) -> SessionOut:
    """Creates the account in the users table and opens its session.

    The answer has the shape of the login and leaves the session cookie.
    REGISTRATION_MODE decides who can register: nobody, whoever has the
    invitation code, or anyone.
    """
    reject_foreign_origin(request, container)
    user = container.register_user.execute(data.to_registration(), client_address(request))
    container.sessions.start(response, user)
    return SessionOut.from_view(user)


@router.post(
    "/password/forgot",
    status_code=202,
    response_model=MessageOut,
    summary="Solicitar enlace para restablecer la contraseña",
    responses={
        429: {"description": "3 solicitudes por correo o 10 por dirección en una hora"},
        503: {"description": "La recuperación de contraseña no está configurada"},
    },
)
def forgot_password(
    data: ForgotPasswordIn,
    request: Request,
    tasks: BackgroundTasks,
    container: Container = Depends(get_container),
) -> MessageOut:
    """Answers the same whether the e-mail is registered or not.

    The e-mail is searched and sent after the answer, so the time does not
    reveal it either.
    """
    container.request_password_reset.accept(data.email, client_address(request))
    tasks.add_task(container.request_password_reset.deliver, data.email)
    return MessageOut(detail=RESET_REQUESTED)


@router.post(
    "/password/reset",
    status_code=204,
    response_class=Response,
    summary="Restablecer la contraseña",
    responses={
        400: {"description": "El enlace no es válido, expiró o ya se usó"},
        422: {"description": "La contraseña nueva no cumple la política"},
        429: {"description": "10 intentos desde esa dirección en una hora"},
    },
)
def reset_password(
    data: ResetPasswordIn, request: Request, container: Container = Depends(get_container)
) -> Response:
    """Saves the new password and ends the sessions opened with the previous one.

    It does not open a session: the user logs in with the new password.
    """
    container.reset_password.execute(data.token, data.new_password, client_address(request))
    return Response(status_code=204)


@router.get(
    "/options",
    response_model=AuthOptionsOut,
    summary="Opciones de autenticación disponibles",
)
def auth_options(container: Container = Depends(get_container)) -> AuthOptionsOut:
    """Which account actions this deployment allows; it is public and reveals no account.

    An invite mode without a configured code is reported as "closed", as it behaves.
    """
    return AuthOptionsOut(
        registration=container.register_user.mode,
        password_recovery=container.request_password_reset.available,
    )
