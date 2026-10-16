"""Registers a detection sent by the IoT module: event + alert in one transaction."""

from dataclasses import dataclass

from safevision.application.dto import NEW_ALERT, AlertNotification, AlertView, EventView
from safevision.application.ports.clock import Clock
from safevision.application.ports.notifier import AlertNotifier
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.presenter import EventPresenter
from safevision.application.services.alert_board import AlertBoard
from safevision.application.services.event_deduplicator import EventDeduplicator
from safevision.domain.errors import NotFoundError, ValidationError
from safevision.domain.model.alert import Alert
from safevision.domain.model.event import Event
from safevision.domain.model.event_type import EventType
from safevision.domain.model.identity import require_id
from safevision.domain.structures.alert_priority_queue import AlertEntry


@dataclass(frozen=True)
class RegisterEventCommand:
    camera_id: int
    event_type_id: int | None = None
    event_type: str | None = None  # name, alternative to event_type_id
    subject_id: int | None = None
    zone_id: int | None = None
    detected_class: str = "person"
    confidence: float | None = None
    evidence_url: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class RegistrationResult:
    view: EventView
    created: bool  # False when the detection repeated a recent event


class RegisterEvent:
    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        board: AlertBoard,
        deduplicator: EventDeduplicator,
        presenter: EventPresenter,
        notifier: AlertNotifier | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._board = board
        self._deduplicator = deduplicator
        self._presenter = presenter
        self._notifier = notifier

    def execute(self, command: RegisterEventCommand) -> RegistrationResult:
        with self._uow as uow:
            camera = uow.cameras.get(command.camera_id)
            if camera is None:
                raise NotFoundError("Cámara", command.camera_id)
            if (
                command.subject_id is not None
                and uow.catalog.get_subject(command.subject_id) is None
            ):
                raise NotFoundError("Sujeto", command.subject_id)
            zone = None
            if command.zone_id is not None:
                zone = uow.cameras.get_zone(command.zone_id)
                if zone is None or not zone.belongs_to(command.camera_id):
                    raise NotFoundError(
                        "Zona", f"{command.zone_id} de la cámara {command.camera_id}"
                    )
            event_type = self._event_type(uow, command)

            key = (command.camera_id, require_id(event_type.id), command.subject_id)
            duplicate_id = self._deduplicator.find_recent(key)
            duplicate = None if duplicate_id is None else uow.events.get(duplicate_id)
            if duplicate is not None:
                return RegistrationResult(self._presenter.present(uow, duplicate), created=False)

            event = uow.events.add(
                Event.register(
                    camera=camera,
                    event_type=event_type,
                    occurred_at=self._clock.now(),
                    zone=zone,
                    subject_id=command.subject_id,
                    detected_class=command.detected_class,
                    confidence=command.confidence,
                    evidence_url=command.evidence_url,
                    description=command.description,
                )
            )
            alert = uow.alerts.add(Alert.for_event(event, event_type))
            view = self._presenter.present(uow, event)
            uow.commit()

        # Memory is updated only after the commit succeeded.
        event_id = require_id(event.id)
        self._board.add(AlertEntry(event_id, event_type.severity, event.occurred_at), view)
        self._deduplicator.remember(key, event_id)
        if self._notifier is not None:
            alert_view = AlertView(
                alert_id=require_id(alert.id),
                level=alert.level.priority.value,
                status=alert.status.label,
                event=view,
            )
            self._notifier.publish(AlertNotification(NEW_ALERT, view, alert_view))
        return RegistrationResult(view, created=True)

    @staticmethod
    def _event_type(uow: UnitOfWork, command: RegisterEventCommand) -> EventType:
        if command.event_type_id is not None:
            found = uow.event_types.get(command.event_type_id)
            reference: object = command.event_type_id
        elif command.event_type:
            found = uow.event_types.find_by_name(command.event_type)
            reference = repr(command.event_type)
        else:
            raise ValidationError("Envía event_type_id o event_type")
        if found is None:
            raise NotFoundError("Tipo de evento", reference)
        return found
