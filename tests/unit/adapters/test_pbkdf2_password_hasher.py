import base64
import hashlib

import pytest

from safevision.adapters.outbound.pbkdf2_password_hasher import (
    DEFAULT_ITERATIONS,
    Pbkdf2PasswordHasher,
)
from safevision.application.ports.password_hasher import PasswordHasher

FAST = Pbkdf2PasswordHasher(iterations=1_000)


def test_satisfies_the_port():
    assert isinstance(FAST, PasswordHasher)


def test_production_iterations():
    assert DEFAULT_ITERATIONS == 600_000
    assert Pbkdf2PasswordHasher().hash("x").startswith("pbkdf2_sha256$600000$")


def test_format_and_round_trip():
    encoded = FAST.hash("contraseña segura")
    algorithm, iterations, salt, digest = encoded.split("$")
    assert (algorithm, iterations) == ("pbkdf2_sha256", "1000")
    assert len(base64.b64decode(salt)) == 16
    expected = hashlib.pbkdf2_hmac(
        "sha256", "contraseña segura".encode(), base64.b64decode(salt), 1000
    )
    assert base64.b64decode(digest) == expected
    assert FAST.verify("contraseña segura", encoded)
    assert not FAST.verify("contraseña Segura", encoded)


def test_each_hash_has_its_own_salt():
    assert FAST.hash("igual") != FAST.hash("igual")


def test_iterations_are_read_from_the_stored_hash():
    stored = Pbkdf2PasswordHasher(iterations=10).hash("clave")
    assert FAST.verify("clave", stored)


@pytest.mark.parametrize(
    "encoded",
    [
        "",
        "texto plano",
        "$2b$12$abcdefghijklmnopqrstuuJ1yW1N8Wm9a3pcl0Yl9uZLd2Gx1o3xG",  # bcrypt
        "pbkdf2_sha1$1000$c2FsdA==$aGFzaA==",
        "pbkdf2_sha256$mil$c2FsdA==$aGFzaA==",
        "pbkdf2_sha256$0$c2FsdA==$aGFzaA==",
        "pbkdf2_sha256$99999999999$c2FsdA==$aGFzaA==",
        "pbkdf2_sha256$1000$no base64$aGFzaA==",
        "pbkdf2_sha256$1000$c2FsdA==$",
        "pbkdf2_sha256$1000$c2FsdA==$aGFzaA==$extra",
    ],
)
def test_other_formats_never_verify(encoded):
    assert FAST.verify("clave", encoded) is False


def test_any_text_can_be_hashed():
    encoded = FAST.hash("\ud800")
    assert FAST.verify("\ud800", encoded)


def test_comparison_takes_constant_time(monkeypatch):
    import safevision.adapters.outbound.pbkdf2_password_hasher as module

    calls = []
    original = module.hmac.compare_digest
    monkeypatch.setattr(
        module.hmac, "compare_digest", lambda a, b: calls.append(1) or original(a, b)
    )
    FAST.verify("clave", FAST.hash("clave"))
    assert calls == [1]


@pytest.mark.parametrize("iterations", [0, 10_000_001])
def test_iterations_must_be_reasonable(iterations):
    with pytest.raises(ValueError):
        Pbkdf2PasswordHasher(iterations=iterations)
