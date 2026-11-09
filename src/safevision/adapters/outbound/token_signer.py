"""Signed tokens: session cookie, WebSocket ticket and password reset link.

A token is ``<payload>.<signature>``, both base64url without padding. The
payload is JSON with the user id (``sub``), the purpose (``pur``), the issue and
expiry instants in Unix seconds (``iat``, ``exp``) and the fingerprint of the
user's password (``pwf``); the signature is HMAC-SHA256 of the payload with
SESSION_SECRET. Nothing is stored on the server, so a token stays valid until it
expires, the secret changes or the password changes: the user is read again from
the database on every request and the fingerprint must still match.

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


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    fingerprint: str = field(repr=False)


class TokenSigner:
    def __init__(self, secret: str, now: Callable[[], datetime]) -> None:
        self._key = secret.encode()
        self._now = now

    def issue(self, user_id: int, purpose: str, lifetime: timedelta, fingerprint: str) -> str:
        issued = int(self._now().timestamp())
        claims = {
            "sub": user_id,
            "pur": purpose,
            "iat": issued,
            "exp": issued + int(lifetime.total_seconds()),
            "pwf": fingerprint,
        }
        payload = _encode(json.dumps(claims, separators=(",", ":")).encode())
        return f"{payload}.{self._sign(payload)}"

    def read(self, token: str, purpose: str) -> TokenClaims | None:
        """The claims of a valid, unexpired token issued for ``purpose``; otherwise None."""
        if not token.isascii():  # never issued, and it could not be encoded to check it
            return None
        payload, _, signature = token.partition(".")
        if not hmac.compare_digest(signature.encode(), self._sign(payload).encode()):
            return None
        try:
            claims = json.loads(_decode(payload))
            user_id, token_purpose, expires = claims["sub"], claims["pur"], claims["exp"]
            fingerprint = claims["pwf"]
        except (ValueError, TypeError, KeyError, binascii.Error):
            return None
        if token_purpose != purpose or not isinstance(expires, int):
            return None
        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
            return None
        if not isinstance(fingerprint, str) or self._now().timestamp() >= expires:
            return None
        return TokenClaims(user_id, fingerprint)

    def _sign(self, payload: str) -> str:
        return _encode(hmac.new(self._key, payload.encode(), hashlib.sha256).digest())


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
