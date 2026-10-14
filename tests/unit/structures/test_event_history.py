from app.structures import EventHistory


def ids(items) -> list[int]:
    return [item["id"] for item in items]


def test_newest_is_returned_first():
    history = EventHistory(capacity=5)
    for i in range(1, 4):
        history.add_newest(i, {"id": i})
    assert ids(history.newest(10)) == [3, 2, 1]
    assert ids(history.oldest(10)) == [1, 2, 3]


def test_capacity_drops_the_oldest():
    history = EventHistory(capacity=3)
    for i in range(1, 6):
        history.add_newest(i, {"id": i})
    assert len(history) == 3
    assert ids(history.newest(10)) == [5, 4, 3]
    assert history.update(1, {"id": 1}) is False


def test_limit_is_respected():
    history = EventHistory(capacity=10)
    for i in range(1, 8):
        history.add_newest(i, {"id": i})
    assert ids(history.newest(2)) == [7, 6]
    assert ids(history.oldest(2)) == [1, 2]


def test_update_replaces_data_in_place():
    history = EventHistory(capacity=3)
    history.add_newest(1, {"id": 1, "status": "Pendiente"})
    history.add_newest(2, {"id": 2, "status": "Pendiente"})
    assert history.update(1, {"id": 1, "status": "Revisado"}) is True
    assert [item["status"] for item in history.newest(2)] == ["Pendiente", "Revisado"]


def test_add_newest_with_existing_id_updates_without_duplicating():
    history = EventHistory(capacity=3)
    history.add_newest(1, {"id": 1, "v": "a"})
    history.add_newest(1, {"id": 1, "v": "b"})
    assert len(history) == 1
    assert next(history.newest(1))["v"] == "b"


def test_add_oldest_rebuilds_in_order_and_stops_at_capacity():
    history = EventHistory(capacity=2)
    for i in (9, 8, 7):  # rows arrive newest first
        history.add_oldest(i, {"id": i})
    assert ids(history.newest(10)) == [9, 8]
    history.add_newest(10, {"id": 10})
    assert ids(history.newest(10)) == [10, 9]


def test_drop_until_single_element_keeps_links_consistent():
    history = EventHistory(capacity=1)
    history.add_newest(1, {"id": 1})
    history.add_newest(2, {"id": 2})
    assert ids(history.newest(5)) == [2]
    assert ids(history.oldest(5)) == [2]
