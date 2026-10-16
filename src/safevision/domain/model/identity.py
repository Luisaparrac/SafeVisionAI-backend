"""Identifiers of stored entities.

Entities have ``id: int | None`` because a new one has no id until it is
stored. Code that works with entities read from storage uses ``require_id``,
which states that assumption and fails loudly if it is ever broken.
"""


def require_id(entity_id: int | None) -> int:
    if entity_id is None:
        raise ValueError("the entity has not been stored yet")
    return entity_id
