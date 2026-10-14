from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Thread

from safevision.application.dto import EventView
from safevision.application.services.alert_board import AlertBoard
from safevision.domain.model.values import Severity
from safevision.domain.structures.alert_priority_queue import AlertEntry

T0 = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


def view(event_id: int, status: str = "Pendiente") -> EventView:
    return EventView(event_id, "Caída", "Rosa", "Casa", "Sala", "", "", "Alto", status, None)


def entry(event_id: int, severity: int, minutes: int = 0) -> AlertEntry:
    return AlertEntry(event_id, Severity(severity), T0 + timedelta(minutes=minutes))


def test_add_feeds_queue_and_history():
    board = AlertBoard(history_capacity=10)
    board.add(entry(1, 1), view(1))
    board.add(entry(2, 4, minutes=1), view(2))
    assert [e.event_id for e in board.pending(5)] == [2, 1]
    assert board.pending_count() == 2
    assert [v.id for v in board.recent(5)] == [2, 1]


def test_close_removes_from_queue_and_updates_history():
    board = AlertBoard(history_capacity=10)
    board.add(entry(1, 3), view(1))
    board.close(view(1, status="Revisado"))
    assert board.pending_count() == 0
    assert board.recent(1)[0].status == "Revisado"


def test_close_of_unknown_event_is_harmless():
    board = AlertBoard(history_capacity=10)
    board.close(view(7, status="Revisado"))
    assert board.pending_count() == 0
    assert board.recent(5) == []


def test_refresh_updates_history_only():
    board = AlertBoard(history_capacity=10)
    board.add(entry(1, 3), view(1))
    board.refresh(replace(view(1), description="en revisión"))
    assert board.recent(1)[0].description == "en revisión"
    assert board.pending_count() == 1


def test_history_is_bounded():
    board = AlertBoard(history_capacity=2)
    for i in range(1, 5):
        board.add(entry(i, 1), view(i))
    assert [v.id for v in board.recent(10)] == [4, 3]
    assert board.pending_count() == 4


def test_replace_swaps_everything():
    board = AlertBoard(history_capacity=2)
    board.add(entry(1, 1), view(1))
    board.replace([entry(5, 2), entry(6, 4)], [view(6), view(5), view(4)])
    assert [e.event_id for e in board.pending(10)] == [6, 5]
    assert [v.id for v in board.recent(10)] == [6, 5]


def test_concurrent_adds_are_not_lost():
    board = AlertBoard(history_capacity=1000)

    def worker(start: int) -> None:
        for i in range(start, start + 200):
            board.add(entry(i, i % 4 + 1), view(i))

    threads = [Thread(target=worker, args=(n * 1000,)) for n in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert board.pending_count() == 800
