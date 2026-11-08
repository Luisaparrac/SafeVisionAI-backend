"""Password reset tokens, signed with SESSION_SECRET for their own purpose.

The purpose is part of what is signed, so one of these never works as a session
cookie or a WebSocket ticket, nor those as one of these.
"""

from datetime import timedelta

from safevision.adapters.outbound.token_signer import TokenSigner

PASSWORD_RESET = "pwreset"


class SignedPasswordResetTokens:
    def __init__(self, signer: TokenSigner, lifetime: timedelta) -> None:
        self._signer = signer
        self._lifetime = lifetime

    def issue(self, user_id: int, fingerprint: str) -> str:
        return self._signer.issue(user_id, PASSWORD_RESET, self._lifetime, fingerprint)
