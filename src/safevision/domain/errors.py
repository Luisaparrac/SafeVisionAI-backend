"""Domain errors. Messages are in Spanish because they reach the end user."""


class DomainError(Exception):
    """Base class for every rule violation detected by the domain."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """A referenced entity does not exist."""

    def __init__(self, entity: str, entity_id: object) -> None:
        super().__init__(f"{entity} {entity_id} no existe")
        self.entity = entity
        self.entity_id = entity_id


class ValidationError(DomainError):
    """A value does not satisfy the rules of the domain."""


class InvalidTransitionError(DomainError):
    """A state change is not allowed from the current state."""

    def __init__(self, entity: str, current: str, target: str) -> None:
        super().__init__(f"{entity}: no se puede pasar de '{current}' a '{target}'")
        self.current = current
        self.target = target
