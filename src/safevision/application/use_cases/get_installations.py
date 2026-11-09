"""Locations, cameras and zones of the installation, as a tree.

A camera always hangs from one location and a zone from one camera: a row that
points to a missing parent breaks that rule and is reported as NotFoundError,
as the presenter does with the same references.
"""

from dataclasses import dataclass
from typing import Protocol

from safevision.application.dto import InstallationNodeView, InstallationsView
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.domain.errors import NotFoundError
from safevision.domain.model.identity import require_id
from safevision.domain.structures.nary_tree import NaryTree

_Key = tuple[str, int]

_ROOT: _Key = ("root", 0)
_LOCATION = "location"
_CAMERA = "camera"
_ZONE = "zone"


class _Named(Protocol):
    name: str
    id: int | None


@dataclass
class _Monitored:
    name: str = ""
    status: str | None = None


def _by_name[T: _Named](rows: list[T]) -> list[T]:
    return sorted(rows, key=lambda row: (row.name, require_id(row.id)))


def _hierarchy(uow: UnitOfWork) -> NaryTree[_Key, _Monitored]:
    """The tree without events; siblings are ordered by name and then by id."""
    tree: NaryTree[_Key, _Monitored] = NaryTree(_ROOT, _Monitored())
    for location in _by_name(uow.catalog.list_locations()):
        tree.add_child(_ROOT, (_LOCATION, require_id(location.id)), _Monitored(location.name))
    for camera in _by_name(uow.cameras.list_all()):
        parent = (_LOCATION, camera.location_id)
        if tree.find(parent) is None:
            raise NotFoundError("Ubicación", camera.location_id)
        node = _Monitored(camera.name, camera.status.value)
        tree.add_child(parent, (_CAMERA, require_id(camera.id)), node)
    for zone in _by_name(uow.cameras.list_zones()):
        parent = (_CAMERA, zone.camera_id)
        if tree.find(parent) is None:
            raise NotFoundError("Cámara", zone.camera_id)
        tree.add_child(parent, (_ZONE, require_id(zone.id)), _Monitored(zone.name))
    return tree


class GetInstallations:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self) -> InstallationsView:
        with self._uow as uow:
            tree = _hierarchy(uow)
        views: dict[_Key, InstallationNodeView] = {}
        for node in tree.postorder():
            views[node.key] = InstallationNodeView(
                id=node.key[1],
                name=node.value.name,
                status=node.value.status,
                own_pending=0,
                pending=0,
                max_severity=None,
                priority=None,
                children=tuple(views[child.key] for child in node.children),
            )
        root = views[_ROOT]
        return InstallationsView(root.pending, root.max_severity, root.priority, root.children)
