import pytest

from safevision.application.ports.repositories import CameraRepository
from safevision.domain.errors import NotFoundError
from safevision.domain.model.camera import Camera
from safevision.domain.model.values import CameraStatus
from safevision.domain.model.zone import Zone
from tests.fakes.repositories import InMemoryCameraRepository

SQUARE = [[0, 0], [1, 0], [1, 1]]


@pytest.fixture
def repo() -> InMemoryCameraRepository:
    repo = InMemoryCameraRepository()
    repo.add(Camera(name="Sala", ip_address="192.0.2.1", location_id=1))
    repo.add(Camera(name="Patio", ip_address="192.0.2.2", location_id=1))
    repo.zones.add(Zone(name="Escalera", camera_id=1, polygon=SQUARE))
    return repo


def test_fake_satisfies_the_port(repo):
    assert isinstance(repo, CameraRepository)


def test_cameras(repo):
    assert [c.name for c in repo.list_all()] == ["Sala", "Patio"]
    camera = repo.get(2)
    camera.change_status("maintenance")
    repo.update(camera)
    assert repo.get(2).status is CameraStatus.MAINTENANCE
    assert repo.get(9) is None


def test_update_of_missing_camera_fails(repo):
    with pytest.raises(NotFoundError):
        repo.update(Camera(id=9, name="X", ip_address="192.0.2.9", location_id=1))


def test_zones(repo):
    assert repo.get_zone(1).camera_id == 1
    assert repo.get_zone(2) is None
    assert [z.name for z in repo.list_zones()] == ["Escalera"]


def test_snapshot_covers_zones(repo):
    state = repo.snapshot()
    repo.zones.add(Zone(name="Puerta", camera_id=2, polygon=SQUARE))
    repo.restore(state)
    assert len(repo.list_zones()) == 1
