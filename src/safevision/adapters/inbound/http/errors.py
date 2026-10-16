"""Translation of domain errors to HTTP responses.

The body keeps the shape FastAPI already uses, ``{"detail": "..."}``, with the
Spanish message written by the domain.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from safevision.domain.errors import (
    DomainError,
    InvalidTransitionError,
    NotFoundError,
    ValidationError,
)

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    NotFoundError: 404,
    InvalidTransitionError: 409,
    ValidationError: 422,
}


def status_for(error: DomainError) -> int:
    """Most specific registered class wins; any other domain error is a 400."""
    for cls in type(error).__mro__:
        if cls in STATUS_BY_ERROR:
            return STATUS_BY_ERROR[cls]
    return 400


async def domain_error_handler(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, DomainError)
    return JSONResponse(status_code=status_for(error), content={"detail": error.message})


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
