from safevision.application.dto import UserView
from safevision.application.use_cases.get_session_user import GetSessionUser
from tests.fakes.users import TEST_EMAIL, TEST_FINGERPRINT, TEST_NAME


def test_existing_user(uow):
    assert GetSessionUser(uow).execute(1, TEST_FINGERPRINT) == UserView(
        id=1, name=TEST_NAME, email=TEST_EMAIL, password_fingerprint=TEST_FINGERPRINT
    )


def test_removed_user(uow):
    assert GetSessionUser(uow).execute(2, TEST_FINGERPRINT) is None


def test_session_of_an_older_password(uow):
    assert GetSessionUser(uow).execute(1, "0" * len(TEST_FINGERPRINT)) is None
