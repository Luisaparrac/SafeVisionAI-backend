"""Locations, cameras and zones of the installation, as a tree.

A camera always hangs from one location and a zone from one camera: a row that
points to a missing parent breaks that rule and is reported as NotFoundError,
as the presenter does with the same references. The same goes for an open event
of a missing camera or event type. Skipping any of them would hide it from the
totals, which must match the pending count of the alert queue.

The zone of an event is optional. An event with no zone, with a zone that no
longer exists or with a zone of another camera (``RegisterEvent`` rejects those)
counts directly in its camera.
"""

from dataclasses import dataclass
from typing import Protocol

from safevision.application.dto import InstallationNodeView, InstallationsView
from safevision.application.ports.repositories import EventFilter
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.domain.errors import NotFoundError
from safevision.domain.model.event import Event
from safevision.domain.model.identity import require_id
from safevision.domain.model.values import ReviewLabel, Severity
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
    own_pending: int = 0
    own_severity: int | None = None

    def count(self, severity: int) -> None:
        self.own_pending += 1
        self.own_severity = max(self.own_severity or 0, severity)


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


def _owner(tree: NaryTree[_Key, _Monitored], event: Event) -> _Monitored:
    """The node where an event counts: its zone or, failing that, its camera."""
    camera = tree.find((_CAMERA, event.camera_id))
    if camera is None:
        raise NotFoundError("Cámara", event.camera_id)
    zone = None if event.zone_id is None else tree.find((_ZONE, event.zone_id))
    return zone.value if zone is not None and zone.parent is camera else camera.value


def _count_pending_events(uow: UnitOfWork, tree: NaryTree[_Key, _Monitored]) -> None:
    severities = {t.id: t.severity.level for t in uow.event_types.list_all()}
    for event in uow.events.find(EventFilter(statuses=ReviewLabel.PENDING.statuses)):
        if event.event_type_id not in severities:
            raise NotFoundError("Tipo de evento", event.event_type_id)
        _owner(tree, event).count(severities[event.event_type_id])


class GetInstallations:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self) -> InstallationsView:
        with self._uow as uow:
            tree = _hierarchy(uow)
            _count_pending_events(uow, tree)
        # In postorder the children are ready when their parent needs their totals.
        views: dict[_Key, InstallationNodeView] = {}
        for node in tree.postorder():
            children = tuple(views[child.key] for child in node.children)
            highest = max(
                (
                    level
                    for level in (node.value.own_severity, *(c.max_severity for c in children))
                    if level is not None
                ),
                default=None,
            )
            views[node.key] = InstallationNodeView(
                id=node.key[1],
                name=node.value.name,
                status=node.value.status,
                own_pending=node.value.own_pending,
                pending=node.value.own_pending + sum(child.pending for child in children),
                max_severity=highest,
                priority=None if highest is None else Severity(highest).priority.value,
                children=children,
            )
        root = views[_ROOT]
        return InstallationsView(root.pending, root.max_severity, root.priority, root.children)
