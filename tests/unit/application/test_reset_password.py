from datetime import timedelta

import pytest

from safevision.adapters.outbound.signed_password_reset_tokens import SignedPasswordResetTokens
from safevision.adapters.outbound.token_signer import TokenSigner
from safevision.application.errors import InvalidResetTokenError, TooManyRequestsError
from safevision.application.services.rate_limiter import SlidingWindowLimiter
from safevision.application.use_cases.reset_password import ResetPassword
from safevision.domain.errors import ValidationError
from tests.fakes.users import FAST_HASHER, TEST_FINGERPRINT

IP = "198.51.100.7"
NEW = "clave-nueva-1"
SECRET = "test-session-secret-0123456789abcdef"


@pytest.fixture
def tokens(clock) -> SignedPasswordResetTokens:
    return SignedPasswordResetTokens(TokenSigner(SECRET, clock.now), timedelta(minutes=30))


@pytest.fixture
def reset(uow, tokens, clock) -> ResetPassword:
    limiter = SlidingWindowLimiter(clock.now, 10, timedelta(hours=1))
    return ResetPassword(uow, FAST_HASHER, tokens, limiter)


def test_changes_the_password(reset, uow, tokens):
    reset.execute(tokens.issue(1, TEST_FINGERPRINT), NEW, IP)
    assert FAST_HASHER.verify(NEW, uow.users.get(1).password_hash)
    assert uow.commits == 1


def test_a_link_works_only_once(reset, tokens):
    token = tokens.issue(1, TEST_FINGERPRINT)
    reset.execute(token, NEW, IP)
    with pytest.raises(InvalidResetTokenError) as error:
        reset.execute(token, "otra-clave-2", IP)
    assert error.value.message == "El enlace no es válido o expiró"


def test_expired_link(reset, tokens, clock):
    token = tokens.issue(1, TEST_FINGERPRINT)
    clock.advance(30 * 60)
    with pytest.raises(InvalidResetTokenError):
        reset.execute(token, NEW, IP)


@pytest.mark.parametrize("token", ["", "basura", "a.b"])
def test_garbage_link(reset, token):
    with pytest.raises(InvalidResetTokenError):
        reset.execute(token, NEW, IP)


def test_link_of_a_removed_user(reset, tokens, uow):
    token = tokens.issue(1, TEST_FINGERPRINT)
    uow.users._rows.pop(1)
    with pytest.raises(InvalidResetTokenError):
        reset.execute(token, NEW, IP)


def test_link_of_an_older_password(reset, tokens, uow):
    token = tokens.issue(1, TEST_FINGERPRINT)
    uow.users._rows[1].password_hash = FAST_HASHER.hash("cambiada-1")
    with pytest.raises(InvalidResetTokenError):
        reset.execute(token, NEW, IP)


def test_a_weak_password_does_not_spend_the_link(reset, tokens, uow):
    token = tokens.issue(1, TEST_FINGERPRINT)
    before = uow.users.get(1).password_hash
    with pytest.raises(ValidationError):
        reset.execute(token, "corta1", IP)
    assert uow.users.get(1).password_hash == before
    reset.execute(token, NEW, IP)


def test_an_invalid_link_wins_over_a_weak_password(reset):
    with pytest.raises(InvalidResetTokenError):
        reset.execute("basura", "corta1", IP)


def test_two_requests_with_the_same_link(uow, tokens, clock):
    # The other request changes the password while this one is hashing.
    limiter = SlidingWindowLimiter(clock.now, 10, timedelta(hours=1))

    class RacingHasher:
        def hash(self, password):
            uow.users._rows[1].password_hash = FAST_HASHER.hash("la-otra-gana-1")
            return FAST_HASHER.hash(password)

    token = tokens.issue(1, TEST_FINGERPRINT)
    with pytest.raises(InvalidResetTokenError):
        ResetPassword(uow, RacingHasher(), tokens, limiter).execute(token, NEW, IP)
    assert FAST_HASHER.verify("la-otra-gana-1", uow.users.get(1).password_hash)


def test_limit_per_address(reset):
    for _ in range(10):
        with pytest.raises(InvalidResetTokenError):
            reset.execute("basura", NEW, IP)
    with pytest.raises(TooManyRequestsError):
        reset.execute("basura", NEW, IP)
    with pytest.raises(InvalidResetTokenError):
        reset.execute("basura", NEW, "203.0.113.9")
