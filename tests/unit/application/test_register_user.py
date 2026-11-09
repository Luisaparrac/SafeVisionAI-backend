from datetime import timedelta

import pytest

from safevision.application.errors import (
    EmailAlreadyRegisteredError,
    InvalidInvitationCodeError,
    RegistrationClosedError,
    TooManyRequestsError,
)
from safevision.application.services.rate_limiter import SlidingWindowLimiter
from safevision.application.use_cases.register_user import RegisterUser, Registration
from safevision.domain.errors import ValidationError
from tests.fakes.clock import FakeClock
from tests.fakes.users import FAST_HASHER, TEST_EMAIL

CODE = "código-secreto"
IP = "198.51.100.7"
NEW = Registration(name="Eva Ruiz", email=" Eva@Example.com ", password="clave123")


def limiter():
    return SlidingWindowLimiter(FakeClock().now, 5, timedelta(hours=1))


def use_case(uow, mode="open", code=CODE):
    return RegisterUser(uow, FAST_HASHER, mode, code, limiter())


def test_creates_the_user_with_a_hashed_password_and_lowercase_email(uow):
    view = use_case(uow).execute(NEW, IP)
    stored = uow.users.get(view.id)
    assert (view.name, view.email) == ("Eva Ruiz", "eva@example.com")
    assert stored.email == "eva@example.com"
    assert stored.password_hash != NEW.password
    assert FAST_HASHER.verify(NEW.password, stored.password_hash)
    assert view.password_fingerprint == stored.password_fingerprint
    assert uow.commits == 1
    assert uow.users.locked_emails == ["eva@example.com"]


def test_secrets_stay_out_of_the_repr():
    registration = Registration("Eva", "e@example.com", "clave123", "cod-unico")
    assert "clave123" not in repr(registration)
    assert "cod-unico" not in repr(registration)


def test_closed_mode_refuses_everything(uow):
    with pytest.raises(RegistrationClosedError) as error:
        use_case(uow, "closed").execute(Registration("", "", ""), IP)
    assert error.value.message == "El registro de cuentas no está habilitado"
    assert uow.commits == 0


@pytest.mark.parametrize("code", [None, "", "otro", CODE + "x"])
def test_invite_mode_needs_the_exact_code(uow, code):
    with pytest.raises(InvalidInvitationCodeError) as error:
        use_case(uow, "invite").execute(
            Registration("Eva Ruiz", "eva@example.com", "clave123", code), IP
        )
    assert error.value.message == "Código de invitación inválido"
    assert uow.users.find_by_email("eva@example.com") == []


def test_invite_mode_with_the_code(uow):
    registration = Registration("Eva Ruiz", "eva@example.com", "clave123", CODE)
    assert use_case(uow, "invite").execute(registration, IP).id == 2


def test_open_mode_ignores_the_code(uow):
    registration = Registration("Eva Ruiz", "eva@example.com", "clave123", "cualquiera")
    assert use_case(uow).execute(registration, IP).id == 2


@pytest.mark.parametrize("email", [TEST_EMAIL, TEST_EMAIL.upper(), f"  {TEST_EMAIL} "])
def test_existing_email_is_refused(uow, email):
    with pytest.raises(EmailAlreadyRegisteredError) as error:
        use_case(uow).execute(Registration("Eva Ruiz", email, "clave123"), IP)
    assert error.value.message == "Ya existe una cuenta con ese correo"
    assert uow.commits == 0


def test_email_taken_while_hashing_is_refused(uow):
    # Another request stored the e-mail after the first check.
    class RacingHasher:
        def hash(self, password):
            use_case(uow).execute(NEW, IP)
            return FAST_HASHER.hash(password)

    with pytest.raises(EmailAlreadyRegisteredError):
        RegisterUser(uow, RacingHasher(), "open", "", limiter()).execute(NEW, IP)
    assert len(uow.users.find_by_email("eva@example.com")) == 1


@pytest.mark.parametrize(
    "registration",
    [
        Registration("A", "eva@example.com", "clave123"),
        Registration("Eva Ruiz", "no-es-correo", "clave123"),
        Registration("Eva Ruiz", "eva@example.com", "corta1"),
    ],
)
def test_invalid_data_is_refused_before_touching_the_database(uow, registration):
    with pytest.raises(ValidationError):
        use_case(uow).execute(registration, IP)
    assert uow.commits == 0


def test_every_attempt_with_valid_data_counts(uow):
    register = RegisterUser(uow, FAST_HASHER, "invite", CODE, limiter())
    wrong = Registration("Eva Ruiz", "eva@example.com", "clave123", "mal")
    for _ in range(5):
        with pytest.raises(InvalidInvitationCodeError):
            register.execute(wrong, IP)
    with pytest.raises(TooManyRequestsError) as error:
        register.execute(wrong, IP)  # guessing the code stops here
    assert error.value.message == "Demasiadas solicitudes. Intenta de nuevo más tarde."
    with pytest.raises(InvalidInvitationCodeError):
        register.execute(wrong, "203.0.113.9")  # another address has its own count


def test_invalid_data_does_not_use_the_limit(uow):
    register = use_case(uow)
    for _ in range(6):
        with pytest.raises(ValidationError):
            register.execute(Registration("Eva Ruiz", "eva@example.com", "corta1"), IP)
    assert register.execute(NEW, IP).id == 2
