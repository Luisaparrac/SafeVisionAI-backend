"""Rules for the data of a panel account, shared by registration and password reset."""

import re

from safevision.domain.errors import ValidationError

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
MIN_NAME_LENGTH = 2
MAX_NAME_LENGTH = 100
MAX_EMAIL_LENGTH = 320  # RFC 5321 limit for an address
# Same pattern as the chk_users_email constraint of the users table. Used with
# ``fullmatch``: "$" would accept a final line break.
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    # isprintable: control characters (such as NUL) cannot be stored in a text column.
    return (
        len(email) <= MAX_EMAIL_LENGTH
        and email.isprintable()
        and _EMAIL.fullmatch(email) is not None
    )


def ensure_valid_email(email: str) -> None:
    if not is_valid_email(email):
        raise ValidationError("El correo no tiene un formato válido")


def ensure_valid_name(name: str) -> None:
    if name != name.strip():
        raise ValidationError("El nombre no puede empezar ni terminar con espacios")
    if not MIN_NAME_LENGTH <= len(name) <= MAX_NAME_LENGTH:
        raise ValidationError(
            f"El nombre debe tener entre {MIN_NAME_LENGTH} y {MAX_NAME_LENGTH} caracteres"
        )
    if not name.isprintable():
        raise ValidationError("El nombre contiene caracteres no permitidos")


def ensure_valid_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValidationError(f"La contraseña no puede superar {MAX_PASSWORD_LENGTH} caracteres")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise ValidationError("La contraseña debe incluir al menos una letra y un número")
