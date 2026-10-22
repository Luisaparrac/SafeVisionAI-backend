from safevision.application.dto import UserView
from safevision.application.use_cases.get_session_user import GetSessionUser
from tests.fakes.users import TEST_EMAIL, TEST_NAME


def test_existing_user(uow):
    assert GetSessionUser(uow).execute(1) == UserView(id=1, name=TEST_NAME, email=TEST_EMAIL)


def test_removed_user(uow):
    assert GetSessionUser(uow).execute(2) is None
