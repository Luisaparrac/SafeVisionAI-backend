import pytest

from safevision.domain.errors import ValidationError
from safevision.domain.model.account import (
    ensure_valid_email,
    ensure_valid_name,
    ensure_valid_password,
    is_valid_email,
    normalize_email,
)


@pytest.mark.parametrize("password", ["clave123", "a1" * 64, "contraseña1", "Ñandú 2024!"])
def test_valid_passwords(password):
    ensure_valid_password(password)


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("", "La contraseña debe tener al menos 8 caracteres"),
        ("clave12", "La contraseña debe tener al menos 8 caracteres"),
        ("a1" * 64 + "x", "La contraseña no puede superar 128 caracteres"),
        ("solo-letras", "La contraseña debe incluir al menos una letra y un número"),
        ("12345678", "La contraseña debe incluir al menos una letra y un número"),
    ],
)
def test_invalid_passwords(password, message):
    with pytest.raises(ValidationError) as error:
        ensure_valid_password(password)
    assert error.value.message == message


@pytest.mark.parametrize("name", ["Al", "Ana María", "x" * 100, "José O'Neil"])
def test_valid_names(name):
    ensure_valid_name(name)


@pytest.mark.parametrize(
    ("name", "message"),
    [
        (" Ana", "El nombre no puede empezar ni terminar con espacios"),
        ("Ana ", "El nombre no puede empezar ni terminar con espacios"),
        ("A", "El nombre debe tener entre 2 y 100 caracteres"),
        ("", "El nombre debe tener entre 2 y 100 caracteres"),
        ("x" * 101, "El nombre debe tener entre 2 y 100 caracteres"),
        ("Ana\nMaría", "El nombre contiene caracteres no permitidos"),
        ("Ana\x00", "El nombre contiene caracteres no permitidos"),
    ],
)
def test_invalid_names(name, message):
    with pytest.raises(ValidationError) as error:
        ensure_valid_name(name)
    assert error.value.message == message


@pytest.mark.parametrize("email", ["a@b.co", "ana.maria+x@example.com", "ñu@example.com"])
def test_valid_emails(email):
    assert is_valid_email(email)
    ensure_valid_email(email)


@pytest.mark.parametrize(
    "email",
    [
        "",
        "sin-arroba",
        "a@b",
        "a@@b.co",
        "a b@example.com",
        "a@example.com\n",
        "a\x00@example.com",
        "a\ud800@example.com",
        "a" * 310 + "@example.com",
    ],
)
def test_invalid_emails(email):
    assert not is_valid_email(email)
    with pytest.raises(ValidationError) as error:
        ensure_valid_email(email)
    assert error.value.message == "El correo no tiene un formato válido"


def test_normalize_email():
    assert normalize_email("  Ana@Example.COM ") == "ana@example.com"
