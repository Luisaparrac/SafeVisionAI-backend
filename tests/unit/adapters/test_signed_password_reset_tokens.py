from datetime import timedelta

import pytest

from safevision.adapters.inbound.http.sessions import SESSION, WS_TICKET
from safevision.adapters.outbound.signed_password_reset_tokens import (
    PASSWORD_RESET,
    SignedPasswordResetTokens,
)
from safevision.adapters.outbound.token_signer import TokenSigner
from safevision.application.ports.password_reset_tokens import PasswordResetTokens
from tests.fakes.clock import FakeClock

SECRET = "test-session-secret-0123456789abcdef"
STAMP = "0123456789abcdef"


@pytest.fixture
def signer() -> TokenSigner:
    return TokenSigner(SECRET, FakeClock().now)


@pytest.fixture
def tokens(signer) -> SignedPasswordResetTokens:
    return SignedPasswordResetTokens(signer, timedelta(minutes=30))


def test_satisfies_the_port(tokens):
    assert isinstance(tokens, PasswordResetTokens)


def test_carries_the_user_and_the_fingerprint(tokens, signer):
    claims = signer.read(tokens.issue(7, STAMP), PASSWORD_RESET)
    assert (claims.user_id, claims.fingerprint) == (7, STAMP)


@pytest.mark.parametrize("other", [SESSION, WS_TICKET])
def test_is_neither_a_session_nor_a_ticket(tokens, signer, other):
    assert signer.read(tokens.issue(7, STAMP), other) is None
