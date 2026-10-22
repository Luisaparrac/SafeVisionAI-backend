import base64
import json
from datetime import timedelta

import pytest

from safevision.adapters.inbound.http.sessions import SESSION, TokenSigner
from tests.fakes.clock import FakeClock

SECRET = "test-session-secret-0123456789abcdef"
HOUR = timedelta(hours=1)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def signer(clock) -> TokenSigner:
    return TokenSigner(SECRET, clock.now)


def claims(token: str) -> dict:
    payload = token.split(".")[0]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


def forge(payload: dict, signer: TokenSigner) -> str:
    text = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{text}.{signer._sign(text)}"


def test_round_trip(signer, clock):
    token = signer.issue(7, SESSION, HOUR)
    assert signer.read(token, SESSION) == 7
    start = int(clock.now().timestamp())
    assert claims(token) == {"sub": 7, "pur": SESSION, "iat": start, "exp": start + 3600}


def test_token_is_cookie_safe(signer):
    token = signer.issue(7, SESSION, HOUR)
    assert set(token) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.")


def test_expires(signer, clock):
    token = signer.issue(7, SESSION, HOUR)
    clock.advance(3599)
    assert signer.read(token, SESSION) == 7
    clock.advance(1)
    assert signer.read(token, SESSION) is None


def test_purpose_is_checked(signer):
    assert signer.read(signer.issue(7, "ws", HOUR), SESSION) is None


def test_another_secret_does_not_validate(signer, clock):
    other = TokenSigner("another-secret-0123456789abcdefghij", clock.now)
    assert other.read(signer.issue(7, SESSION, HOUR), SESSION) is None


def test_tampered_payload_is_rejected(signer):
    token = signer.issue(7, SESSION, HOUR)
    payload, signature = token.split(".")
    changed = base64.urlsafe_b64encode(json.dumps(claims(token) | {"sub": 1}).encode()).rstrip(b"=")
    assert signer.read(f"{changed.decode()}.{signature}", SESSION) is None
    assert signer.read(f"{payload}.{signature[:-2]}", SESSION) is None


@pytest.mark.parametrize("token", ["", ".", "abc", "abc.def", "a.b.c", "ñ.ñ"])
def test_garbage_is_rejected(signer, token):
    assert signer.read(token, SESSION) is None


@pytest.mark.parametrize(
    "payload",
    [
        [],
        "texto",
        {"pur": SESSION, "exp": 2**40},
        {"sub": 7, "pur": SESSION},
        {"sub": 7, "pur": SESSION, "exp": "mañana"},
        {"sub": "7", "pur": SESSION, "exp": 2**40},
        {"sub": True, "pur": SESSION, "exp": 2**40},
        {"sub": 0, "pur": SESSION, "exp": 2**40},
    ],
)
def test_correctly_signed_but_invalid_claims_are_rejected(signer, payload):
    assert signer.read(forge(payload, signer), SESSION) is None


def test_signed_payload_that_is_not_json_is_rejected(signer):
    text = base64.urlsafe_b64encode(b"\xff\xfe").rstrip(b"=").decode()
    assert signer.read(f"{text}.{signer._sign(text)}", SESSION) is None
