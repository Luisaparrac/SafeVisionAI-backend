import pytest

from safevision.domain.model.identity import require_id


def test_stored_entities_have_an_id():
    assert require_id(7) == 7


def test_a_missing_id_is_a_programming_error():
    with pytest.raises(ValueError, match="stored"):
        require_id(None)
