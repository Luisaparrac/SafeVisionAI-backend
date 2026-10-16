def test_event_types(client):
    response = client.get("/api/tipos-evento")
    assert response.status_code == 200
    assert [(t["event_type_id"], t["priority"]) for t in response.json()] == [
        (1, "Alto"),
        (4, "Alto"),
        (2, "Medio"),
        (3, "Bajo"),
    ]


def test_locations(client):
    assert client.get("/api/ubicaciones").json() == [
        {"location_id": 1, "name": "Casa", "description": None}
    ]


def test_zones(client):
    [zone] = client.get("/api/zonas").json()
    assert zone["coordinates"] == [[0, 0], [1, 0], [1, 1], [0, 1]]
    assert (zone["zone_id"], zone["camera_id"], zone["is_active"]) == (1, 1, True)


def test_subjects(client):
    assert client.get("/api/sujetos").json() == [
        {"subject_id": 1, "name": "Rosa", "subject_type": "elderly", "description": None}
    ]
