"""Signed tokens of the panel: the session cookie and, later, short-lived tickets.

A token is ``<payload>.<signature>``, both base64url without padding. The
payload is JSON with the user id (``sub``), the purpose (``pur``), and the
issue and expiry instants in Unix seconds (``iat``, ``exp``); the signature is
HMAC-SHA256 of the payload with SESSION_SECRET. Nothing is stored on the
server, so a token stays valid until it expires (or the secret changes); the
user is read again from the database on every request.

The purpose is signed too, so a token issued for one use is never accepted
for another.
"""

import base64
import binascii
import hashlib
import hmac
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from fastapi import Response

SESSION_COOKIE = "sv_session"
SESSION = "session"


class TokenSigner:
    def __init__(self, secret: str, now: Callable[[], datetime]) -> None:
        self._key = secret.encode()
        self._now = now

    def issue(self, user_id: int, purpose: str, lifetime: timedelta) -> str:
        issued = int(self._now().timestamp())
        claims = {
            "sub": user_id,
            "pur": purpose,
            "iat": issued,
            "exp": issued + int(lifetime.total_seconds()),
        }
        payload = _encode(json.dumps(claims, separators=(",", ":")).encode())
        return f"{payload}.{self._sign(payload)}"

    def read(self, token: str, purpose: str) -> int | None:
        """The user id of a valid, unexpired token issued for ``purpose``; otherwise None."""
        payload, _, signature = token.partition(".")
        if not hmac.compare_digest(signature.encode(), self._sign(payload).encode()):
            return None
        try:
            claims = json.loads(_decode(payload))
            user_id, token_purpose, expires = claims["sub"], claims["pur"], claims["exp"]
        except (ValueError, TypeError, KeyError, binascii.Error):
            return None
        if token_purpose != purpose or not isinstance(expires, int):
            return None
        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
            return None
        return user_id if self._now().timestamp() < expires else None

    def _sign(self, payload: str) -> str:
        return _encode(hmac.new(self._key, payload.encode(), hashlib.sha256).digest())


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


@dataclass(frozen=True)
class SessionPolicy:
    """How session cookies are signed and sent (from SESSION_* settings)."""

    signer: TokenSigner = field(repr=False)
    lifetime: timedelta
    same_site: str  # "none" or "lax"

    def start(self, response: Response, user_id: int) -> None:
        """Sets the session cookie: HttpOnly (not readable from scripts), Secure, no Domain."""
        response.set_cookie(
            SESSION_COOKIE,
            self.signer.issue(user_id, SESSION, self.lifetime),
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
