import pytest

from safevision.domain.errors import (
    DomainError,
    InvalidTransitionError,
    NotFoundError,
    ValidationError,
)


@pytest.mark.parametrize("error_type", [NotFoundError, ValidationError, InvalidTransitionError])
def test_all_errors_are_domain_errors(error_type):
    assert issubclass(error_type, DomainError)


def test_not_found_keeps_entity_and_id():
    error = NotFoundError("Evento", 7)
    assert error.message == "Evento 7 no existe"
    assert str(error) == error.message
    assert (error.entity, error.entity_id) == ("Evento", 7)


def test_invalid_transition_describes_both_states():
    error = InvalidTransitionError("Evento", "resolved", "pending")
    assert error.current == "resolved"
    assert error.target == "pending"
    assert "resolved" in error.message and "pending" in error.message


def test_validation_error_message():
    assert ValidationError("Confianza fuera de rango").message == "Confianza fuera de rango"
