"""How the panel keeps its session: the signed cookie and the WebSocket ticket.

The tokens themselves are built by ``TokenSigner``; this module names their
purposes and sends the cookie.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from fastapi import Response

from safevision.adapters.outbound.token_signer import TokenSigner
from safevision.application.dto import UserView

SESSION_COOKIE = "sv_session"
SESSION = "session"
# Ticket that a browser page passes in the URL of the WebSocket (see security).
WS_TICKET = "ws"
WS_TICKET_LIFETIME = timedelta(seconds=60)


@dataclass(frozen=True)
class SessionPolicy:
    """How session cookies are signed and sent (from SESSION_* settings)."""

    signer: TokenSigner = field(repr=False)
    lifetime: timedelta
    same_site: str  # "none" or "lax"

    def start(self, response: Response, user: UserView) -> None:
        """Sets the session cookie: HttpOnly (not readable from scripts), Secure, no Domain."""
        response.set_cookie(
            SESSION_COOKIE,
            self.signer.issue(user.id, SESSION, self.lifetime, user.password_fingerprint),
            max_age=int(self.lifetime.total_seconds()),
            path="/",
            secure=True,
            httponly=True,
            samesite=self.same_site,
        )

    def end(self, response: Response) -> None:
        """Expires the cookie in the browser, with the same attributes it was set with."""
        response.delete_cookie(
            SESSION_COOKIE,
            path="/",
            secure=True,
            httponly=True,
            samesite=self.same_site,
        )
