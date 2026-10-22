import pytest

from safevision.adapters.outbound.pbkdf2_password_hasher import Pbkdf2PasswordHasher
from safevision.application.dto import UserView
from safevision.application.errors import InvalidCredentialsError, TooManyLoginAttemptsError
from safevision.application.services.login_throttle import LoginThrottle
from safevision.application.use_cases.authenticate_user import AuthenticateUser
from safevision.domain.model.user import User

HASHER = Pbkdf2PasswordHasher(iterations=1_000)


class CountingHasher:
    """Records every verification, to check that failures cost the same work."""

    def __init__(self) -> None:
        self.verified: list[str] = []
        self.hashed = 0

    def hash(self, password: str) -> str:
        self.hashed += 1
        return HASHER.hash(password)

    def verify(self, password: str, encoded: str) -> bool:
        self.verified.append(encoded)
        return HASHER.verify(password, encoded)


@pytest.fixture
def hasher() -> CountingHasher:
    return CountingHasher()


@pytest.fixture
def throttle(clock) -> LoginThrottle:
    return LoginThrottle(clock.now)


@pytest.fixture
def login(uow, hasher, throttle) -> AuthenticateUser:
    # User 1 is the test user of the reference catalog.
    uow.users.add(User(name="Ana", email="Ana@Example.com", password_hash=HASHER.hash("clave-1")))
    uow.commit()
    return AuthenticateUser(uow, hasher, throttle)


def test_valid_credentials_return_the_user(login):
    assert login.execute(" ANA@example.com ", "clave-1") == UserView(
        id=2, name="Ana", email="Ana@Example.com"
    )


@pytest.mark.parametrize(
    ("email", "password"),
    [("ana@example.com", "clave-2"), ("ana@example.com", ""), ("nadie@example.com", "clave-1")],
)
def test_wrong_credentials_get_the_same_error(login, email, password):
    with pytest.raises(InvalidCredentialsError) as error:
        login.execute(email, password)
    assert error.value.message == "Correo o contraseña incorrectos"


def test_unknown_email_still_checks_a_hash(login, hasher):
    with pytest.raises(InvalidCredentialsError):
        login.execute("nadie@example.com", "clave-1")
    with pytest.raises(InvalidCredentialsError):
        login.execute("otro@example.com", "clave-1")
    assert len(hasher.verified) == 2
    assert hasher.hashed == 1  # the throwaway hash is built once


def test_shared_email_is_refused(uow, login, hasher):
    # The column is not unique: with two owners nobody can tell whose account it is.
    uow.users.add(User(name="Ana B", email="ana@example.com", password_hash=HASHER.hash("clave-1")))
    uow.commit()
    with pytest.raises(InvalidCredentialsError):
        login.execute("ana@example.com", "clave-1")
    assert len(hasher.verified) == 1


def test_hash_in_another_format_is_refused(uow, hasher, throttle):
    uow.users.add(User(name="Ana", email="ana@example.com", password_hash="texto-plano"))
    uow.commit()
    with pytest.raises(InvalidCredentialsError):
        AuthenticateUser(uow, hasher, throttle).execute("ana@example.com", "texto-plano")


def test_creating_the_use_case_hashes_nothing(uow, hasher, throttle):
    AuthenticateUser(uow, hasher, throttle)
    assert hasher.hashed == 0


def fail(login, email="ana@example.com", times=1):
    for _ in range(times):
        with pytest.raises(InvalidCredentialsError):
            login.execute(email, "mala")


def test_fifth_failure_blocks_the_email(login, hasher):
    fail(login, times=5)
    checked = len(hasher.verified)
    with pytest.raises(TooManyLoginAttemptsError) as error:
        login.execute("ana@example.com", "clave-1")  # even with the right password
    assert error.value.message == "Demasiados intentos fallidos. Intenta de nuevo en unos minutos."
    assert len(hasher.verified) == checked  # blocked attempts check nothing


def test_block_is_per_email_and_ignores_case(login):
    fail(login, email="ANA@example.com ", times=5)
    with pytest.raises(TooManyLoginAttemptsError):
        login.execute("ana@example.com", "clave-1")
    fail(login, email="otra@example.com")  # another e-mail is still checked


def test_unknown_emails_are_limited_too(login):
    fail(login, email="nadie@example.com", times=5)
    with pytest.raises(TooManyLoginAttemptsError):
        login.execute("nadie@example.com", "clave-1")


def test_block_ends_when_the_oldest_failure_leaves_the_window(login, clock):
    fail(login)
    clock.advance(600)
    fail(login, times=4)
    with pytest.raises(TooManyLoginAttemptsError):
        login.execute("ana@example.com", "clave-1")
    clock.advance(300)  # the first failure is now 15 minutes old
    assert login.execute("ana@example.com", "clave-1").id == 2


def test_success_clears_the_failures(login):
    fail(login, times=4)
    login.execute("ana@example.com", "clave-1")
    fail(login, times=4)
    assert login.execute("ana@example.com", "clave-1").id == 2
