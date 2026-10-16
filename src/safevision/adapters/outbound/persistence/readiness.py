"""Readiness probe that runs a trivial query on the database."""

import logging

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class DatabaseReadinessProbe:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def is_ready(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            # Only the class name: the driver message may include host and user.
            logger.warning("database not ready: %s", type(error).__name__)
            return False
        return True
