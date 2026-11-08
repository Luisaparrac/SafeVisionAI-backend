from datetime import timedelta

import pytest

from safevision.adapters.inbound.http.sessions import SESSION, WS_TICKET
from safevision.adapters.outbound.signed_password_reset_tokens import (
    PASSWORD_RESET,
    SignedPasswordResetTokens,
)
from safevision.adapters.outbound.token_signer import TokenSigner
from safevision.application.ports.password_reset_tokens import PasswordResetTokens, ResetTicket
from tests.fakes.clock import FakeClock

SECRET = "test-session-secret-0123456789abcdef"
STAMP = "0123456789abcdef"


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def signer(clock) -> TokenSigner:
    return TokenSigner(SECRET, clock.now)


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


def test_round_trip(tokens):
    assert tokens.read(tokens.issue(7, STAMP)) == ResetTicket(7, STAMP)


def test_ticket_does_not_show_the_fingerprint():
    assert STAMP not in repr(ResetTicket(7, STAMP))


def test_expires(tokens, clock):
    token = tokens.issue(7, STAMP)
    clock.advance(30 * 60 - 1)
    assert tokens.read(token) is not None
    clock.advance(1)
    assert tokens.read(token) is None


@pytest.mark.parametrize("other", [SESSION, WS_TICKET])
def test_sessions_and_tickets_are_not_reset_tokens(tokens, signer, other):
    assert tokens.read(signer.issue(7, other, timedelta(hours=1), STAMP)) is None


@pytest.mark.parametrize("garbage", ["", "abc", "a.b", "ñ.ñ"])
def test_garbage(tokens, garbage):
    assert tokens.read(garbage) is None
