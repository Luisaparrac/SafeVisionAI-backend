import ipaddress

import pytest
from sqlalchemy import select

from safevision.adapters.outbound.persistence.orm import CameraRow, ZoneRow
from safevision.adapters.outbound.persistence.repositories import SqlAlchemyCameraRepository
from safevision.application.ports.repositories import CameraRepository
from safevision.domain.errors import NotFoundError
from safevision.domain.model.camera import Camera
from safevision.domain.model.values import CameraStatus

pytestmark = pytest.mark.integration


@pytest.fixture
def repo(session):
    return SqlAlchemyCameraRepository(session)


def test_satisfies_the_port(repo):
    assert isinstance(repo, CameraRepository)


def test_get_reads_the_inet_address(repo):
    sala = repo.get(1)
    assert sala.name == "Sala"
    assert sala.ip_address == ipaddress.ip_address("192.0.2.1")
    assert sala.status is CameraStatus.ACTIVE
    assert repo.get(99) is None


def test_list_all_by_id(repo):
    assert [c.name for c in repo.list_all()] == ["Sala", "Patio"]


def test_update_stores_the_new_status(repo, session):
    camera = repo.get(2)
    camera.change_status("maintenance")
    repo.update(camera)
    stored = session.scalar(select(CameraRow.status).where(CameraRow.camera_id == 2))
    assert stored == "maintenance"


def test_update_of_missing_camera_fails(repo):
    with pytest.raises(NotFoundError):
        repo.update(Camera(id=99, name="X", ip_address="192.0.2.9", location_id=1))


def test_zones(repo, session):
    session.add(
        ZoneRow(name="Puerta", coordinates=[[0, 0], [2, 0], [2, 2]], is_active=False, camera_id=2)
    )
    session.flush()
    escalera = repo.get_zone(1)
    assert escalera.belongs_to(1)
    assert escalera.polygon.to_list() == [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    assert repo.get_zone(99) is None
    assert [(z.name, z.camera_id, z.is_active) for z in repo.list_zones()] == [
        ("Escalera", 1, True),
        ("Puerta", 2, False),
    ]
