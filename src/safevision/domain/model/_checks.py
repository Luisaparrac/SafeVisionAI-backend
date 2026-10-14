"""Small validation helpers shared by the entities."""

from safevision.domain.errors import ValidationError


def required_text(value: object, field: str) -> str:
    """Returns the text without surrounding spaces; fails if it is missing or blank."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"El campo '{field}' es obligatorio")
    return value.strip()


def optional_text(value: object, field: str) -> str | None:
    """Returns ``None`` for missing or blank text, otherwise the trimmed text."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"El campo '{field}' debe ser texto")
    return value.strip() or None


def required_id(value: object, field: str) -> int:
    """Identifiers of related entities are positive integers."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValidationError(f"El campo '{field}' debe ser un identificador válido")
    return value


def optional_id(value: object, field: str) -> int | None:
    return None if value is None else required_id(value, field)
