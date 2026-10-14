"""Most recent events, served from the in-memory history without touching the database."""

from safevision.application.dto import EventView
from safevision.application.services.alert_board import AlertBoard


class GetRecentEvents:
    def __init__(self, board: AlertBoard) -> None:
        self._board = board

    def execute(self, limit: int) -> list[EventView]:
        """Newest first, at most ``limit`` (bounded by the history capacity). O(limit)."""
        return self._board.recent(limit)
