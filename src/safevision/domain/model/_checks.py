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
