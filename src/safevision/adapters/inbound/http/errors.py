"""Translation of domain and infrastructure errors to HTTP responses.

The body keeps the shape FastAPI already uses, ``{"detail": "..."}``, with a
Spanish message. Infrastructure failures and unexpected errors never expose
internal details: the client gets a generic message and the logs only the
error class and the request id.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from safevision.application.errors import (
    InvalidCredentialsError,
    PersistenceError,
    StorageConflictError,
    StorageUnavailableError,
    TooManyLoginAttemptsError,
)
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


logger = logging.getLogger(__name__)

STATUS_BY_PERSISTENCE_ERROR: dict[type[PersistenceError], int] = {
    StorageUnavailableError: 503,
    StorageConflictError: 409,
}
INTERNAL_ERROR_MESSAGE = "Error interno del servidor"


async def persistence_error_handler(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, PersistenceError)
    status = STATUS_BY_PERSISTENCE_ERROR.get(type(error), 500)
    logger.warning("persistence error: %s", type(error).__name__)
    return JSONResponse(status_code=status, content={"detail": error.message})


async def invalid_credentials_handler(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, InvalidCredentialsError)
    return JSONResponse(status_code=401, content={"detail": error.message})


async def too_many_attempts_handler(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, TooManyLoginAttemptsError)
    return JSONResponse(status_code=429, content={"detail": error.message})


async def unexpected_error_handler(_: Request, error: Exception) -> JSONResponse:
    logger.error("unexpected error: %s", type(error).__name__)
    return JSONResponse(status_code=500, content={"detail": INTERNAL_ERROR_MESSAGE})


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(PersistenceError, persistence_error_handler)
    app.add_exception_handler(InvalidCredentialsError, invalid_credentials_handler)
    app.add_exception_handler(TooManyLoginAttemptsError, too_many_attempts_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
