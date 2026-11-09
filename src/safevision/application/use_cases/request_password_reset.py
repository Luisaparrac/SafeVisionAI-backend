"""Sends the link that lets someone choose a new password.

The answer to the client is the same whether the e-mail exists or not, and takes
the same time: ``accept`` runs during the request and touches neither the users
table nor the e-mail provider, and ``deliver`` does both after the answer left.
"""

import html
import logging
from urllib.parse import urlencode, urlsplit, urlunsplit

from safevision.application.errors import PasswordRecoveryUnavailableError, TooManyRequestsError
from safevision.application.ports.email_sender import EmailMessage, EmailSender
from safevision.application.ports.password_reset_tokens import PasswordResetTokens
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.services.rate_limiter import SlidingWindowLimiter
from safevision.domain.model.account import is_valid_email, normalize_email
from safevision.domain.model.identity import require_id

logger = logging.getLogger(__name__)

SUBJECT = "Restablece tu contraseña de SafeVision AI"


class RequestPasswordReset:
    def __init__(
        self,
        uow: UnitOfWork,
        tokens: PasswordResetTokens,
        sender: EmailSender | None,
        reset_url: str,
        lifetime_minutes: int,
        per_client: SlidingWindowLimiter,
        per_email: SlidingWindowLimiter,
    ) -> None:
        self._uow = uow
        self._tokens = tokens
        self._sender = sender
        self._reset_url = reset_url
        self._lifetime_minutes = lifetime_minutes
        self._per_client = per_client
        self._per_email = per_email

    @property
    def available(self) -> bool:
        return self._sender is not None

    def accept(self, email: str, client: str) -> None:
        """Counts every request by address and by e-mail, registered or not.

        ``client`` is only a key in memory: it is never stored or logged.
        """
        if not self.available:
            raise PasswordRecoveryUnavailableError()
        if not self._per_client.try_acquire(client):
            raise TooManyRequestsError()
        if not self._per_email.try_acquire(normalize_email(email)):
            raise TooManyRequestsError()

    def deliver(self, email: str) -> None:
        """Never raises: nobody is waiting, and an error could carry the address."""
        try:
            self._send_link(normalize_email(email))
        except Exception as error:
            logger.error("password reset e-mail failed: %s", type(error).__name__)

    def _send_link(self, email: str) -> None:
        if self._sender is None or not is_valid_email(email):
            return
        with self._uow as uow:
            matches = uow.users.find_by_email(email)
        if len(matches) != 1:  # the column is not unique: same rule as the login
            return
        user = matches[0]
        token = self._tokens.issue(require_id(user.id), user.password_fingerprint)
        self._sender.send(self._message(user.email, token))

    def _message(self, to: str, token: str) -> EmailMessage:
        link = reset_link(self._reset_url, token)
        unit = "minuto" if self._lifetime_minutes == 1 else "minutos"
        lifetime = f"{self._lifetime_minutes} {unit}"
        return EmailMessage(
            to=to,
            subject=SUBJECT,
            text=(
                "Hola:\n\n"
                "Recibimos una solicitud para restablecer la contraseña de tu cuenta "
                "de SafeVision AI. Abre este enlace para elegir una nueva:\n\n"
                f"{link}\n\n"
                f"El enlace vale durante {lifetime} y solo se puede usar una vez.\n\n"
                "Si no lo pediste, ignora este correo: tu contraseña no cambiará.\n"
            ),
            html=(
                "<p>Hola:</p>"
                "<p>Recibimos una solicitud para restablecer la contraseña de tu cuenta "
                "de SafeVision AI.</p>"
                f'<p><a href="{html.escape(link, quote=True)}">Restablecer mi contraseña</a></p>'
                f"<p>El enlace vale durante {lifetime} y solo se puede usar una vez.</p>"
                "<p>Si no lo pediste, ignora este correo: tu contraseña no cambiará.</p>"
            ),
        )


def reset_link(base_url: str, token: str) -> str:
    parts = urlsplit(base_url)
    query = "&".join(part for part in (parts.query, urlencode({"token": token})) if part)
    return urlunsplit(parts._replace(query=query))
