import logging
from datetime import timedelta

import pytest

from safevision.adapters.outbound.signed_password_reset_tokens import (
    PASSWORD_RESET,
    SignedPasswordResetTokens,
)
from safevision.adapters.outbound.token_signer import TokenSigner
from safevision.application.errors import PasswordRecoveryUnavailableError, TooManyRequestsError
from safevision.application.services.rate_limiter import SlidingWindowLimiter
from safevision.application.use_cases.request_password_reset import (
    RequestPasswordReset,
    reset_link,
)
from safevision.domain.model.user import User
from tests.fakes.clock import FakeClock
from tests.fakes.email import CapturingEmailSender, FailingEmailSender
from tests.fakes.users import TEST_EMAIL, TEST_FINGERPRINT

URL = "https://panel.example.com/restablecer"
SECRET = "test-session-secret-0123456789abcdef"


@pytest.fixture
def signer(clock) -> TokenSigner:
    return TokenSigner(SECRET, clock.now)


@pytest.fixture
def outbox() -> CapturingEmailSender:
    return CapturingEmailSender()


HOUR = timedelta(hours=1)
IP = "198.51.100.7"


def build(uow, signer, sender, minutes=30, clock=None):
    now = (clock or FakeClock()).now
    tokens = SignedPasswordResetTokens(signer, timedelta(minutes=minutes))
    return RequestPasswordReset(
        uow,
        tokens,
        sender,
        URL,
        minutes,
        SlidingWindowLimiter(now, 10, HOUR),
        SlidingWindowLimiter(now, 3, HOUR),
    )


@pytest.fixture
def recovery(uow, signer, outbox):
    return build(uow, signer, outbox)


def token_of(message) -> str:
    return message.text.split("?token=")[1].split("\n")[0]


def test_sends_the_link_to_the_registered_user(recovery, outbox, signer):
    recovery.accept(TEST_EMAIL, IP)
    recovery.deliver(f"  {TEST_EMAIL.upper()} ")
    [message] = outbox.sent
    assert message.to == TEST_EMAIL
    claims = signer.read(token_of(message), PASSWORD_RESET)
    assert (claims.user_id, claims.fingerprint) == (1, TEST_FINGERPRINT)


def test_message_in_spanish_with_link_lifetime_and_notice(recovery, outbox):
    recovery.deliver(TEST_EMAIL)
    [message] = outbox.sent
    link = f"{URL}?token={token_of(message)}"
    assert message.subject == "Restablece tu contraseña de SafeVision AI"
    for body in (message.text, message.html):
        assert link in body
        assert "30 minutos" in body
        assert "ignora este correo" in body
    assert f'href="{link}"' in message.html
    assert "Usuario de prueba" not in message.text  # no data of the panel


def test_singular_lifetime(uow, signer, outbox):
    build(uow, signer, outbox, minutes=1).deliver(TEST_EMAIL)
    assert "1 minuto " in outbox.sent[0].text


def test_secrets_stay_out_of_the_repr(recovery, outbox):
    recovery.deliver(TEST_EMAIL)
    shown = repr(outbox.sent[0])
    assert TEST_EMAIL not in shown
    assert "token" not in shown


@pytest.mark.parametrize("email", ["nadie@example.com", "no-es-correo", "a\x00@example.com"])
def test_nothing_is_sent_to_unknown_or_invalid_addresses(recovery, outbox, email):
    recovery.deliver(email)
    assert outbox.sent == []


def test_shared_email_gets_nothing(uow, recovery, outbox):
    uow.users.add(User(name="Otra", email=TEST_EMAIL, password_hash="x"))
    uow.commit()
    recovery.deliver(TEST_EMAIL)
    assert outbox.sent == []


def test_without_a_sender_it_is_unavailable(uow, signer):
    recovery = build(uow, signer, None)
    assert not recovery.available
    with pytest.raises(PasswordRecoveryUnavailableError) as error:
        recovery.accept(TEST_EMAIL, IP)
    assert error.value.message == "La recuperación de contraseña no está disponible"
    recovery.deliver(TEST_EMAIL)  # harmless


def test_a_delivery_failure_is_logged_without_the_address(uow, signer, caplog):
    with caplog.at_level(logging.ERROR):
        build(uow, signer, FailingEmailSender()).deliver(TEST_EMAIL)
    assert "EmailDeliveryError" in caplog.text
    assert TEST_EMAIL not in caplog.text


def test_a_database_failure_does_not_escape(signer, caplog):
    class BrokenUnitOfWork:
        def __enter__(self):
            raise RuntimeError("no conecta a usuario@example.com")

        def __exit__(self, *_):
            return None

    with caplog.at_level(logging.ERROR):
        build(BrokenUnitOfWork(), signer, CapturingEmailSender()).deliver(TEST_EMAIL)
    assert "RuntimeError" in caplog.text
    assert TEST_EMAIL not in caplog.text


@pytest.mark.parametrize(
    ("base", "expected"),
    [
        (URL, f"{URL}?token=a.b-c_d"),
        (URL + "?origen=correo", f"{URL}?origen=correo&token=a.b-c_d"),
    ],
)
def test_reset_link(base, expected):
    assert reset_link(base, "a.b-c_d") == expected


def test_three_requests_per_email(recovery):
    for spelling in (TEST_EMAIL, TEST_EMAIL.upper(), f" {TEST_EMAIL}"):
        recovery.accept(spelling, IP)
    with pytest.raises(TooManyRequestsError):
        recovery.accept(TEST_EMAIL, "203.0.113.9")


def test_ten_requests_per_address(recovery):
    for number in range(10):
        recovery.accept(f"persona{number}@example.com", IP)
    with pytest.raises(TooManyRequestsError):
        recovery.accept("otra@example.com", IP)
    recovery.accept("otra@example.com", "203.0.113.9")


def test_an_address_over_its_limit_does_not_use_the_count_of_the_email(recovery):
    for number in range(10):
        recovery.accept(f"persona{number}@example.com", IP)
    for _ in range(5):
        with pytest.raises(TooManyRequestsError):
            recovery.accept(TEST_EMAIL, IP)
    for _ in range(3):
        recovery.accept(TEST_EMAIL, "203.0.113.9")


def test_limits_end_after_an_hour(uow, signer, outbox, clock):
    recovery = build(uow, signer, outbox, clock=clock)
    for _ in range(3):
        recovery.accept(TEST_EMAIL, IP)
    with pytest.raises(TooManyRequestsError):
        recovery.accept(TEST_EMAIL, IP)
    clock.advance(3600)
    recovery.accept(TEST_EMAIL, IP)
