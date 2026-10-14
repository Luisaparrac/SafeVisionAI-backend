from safevision.application.use_cases.list_cameras import ListCameras
from safevision.application.use_cases.list_event_types import ListEventTypes
from safevision.application.use_cases.list_locations import ListLocations
from safevision.application.use_cases.list_subjects import ListSubjects
from safevision.application.use_cases.list_zones import ListZones


def test_event_types_most_severe_first(uow):
    types = ListEventTypes(uow).execute()
    assert [(t.name, t.priority.value) for t in types] == [
        ("Caída", "Alto"),
        ("Humo", "Alto"),
        ("Merodeo", "Medio"),
        ("Ruido", "Bajo"),
    ]


def test_locations(uow):
    assert [loc.name for loc in ListLocations(uow).execute()] == ["Casa"]


def test_cameras(uow):
    assert [(c.id, c.name) for c in ListCameras(uow).execute()] == [(1, "Sala"), (2, "Patio")]


def test_zones(uow):
    [zone] = ListZones(uow).execute()
    assert (zone.name, zone.camera_id, zone.is_active) == ("Escalera", 1, True)
    assert zone.polygon.to_list() == [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]


def test_subjects(uow):
    [subject] = ListSubjects(uow).execute()
    assert (subject.name, subject.subject_type.value) == ("Rosa", "elderly")


def test_queries_do_not_commit(uow):
    for query in (ListEventTypes, ListLocations, ListCameras, ListZones, ListSubjects):
        query(uow).execute()
    assert uow.commits == 0
