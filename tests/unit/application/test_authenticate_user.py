import pytest

from safevision.adapters.outbound.pbkdf2_password_hasher import Pbkdf2PasswordHasher
from safevision.application.dto import UserView
from safevision.application.errors import InvalidCredentialsError
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
def login(uow, hasher) -> AuthenticateUser:
    # User 1 is the test user of the reference catalog.
    uow.users.add(User(name="Ana", email="Ana@Example.com", password_hash=HASHER.hash("clave-1")))
    uow.commit()
    return AuthenticateUser(uow, hasher)


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


def test_hash_in_another_format_is_refused(uow, hasher):
    uow.users.add(User(name="Ana", email="ana@example.com", password_hash="texto-plano"))
    uow.commit()
    with pytest.raises(InvalidCredentialsError):
        AuthenticateUser(uow, hasher).execute("ana@example.com", "texto-plano")


def test_creating_the_use_case_hashes_nothing(uow, hasher):
    AuthenticateUser(uow, hasher)
    assert hasher.hashed == 0
