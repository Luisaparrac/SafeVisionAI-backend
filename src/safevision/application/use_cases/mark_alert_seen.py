"""Records that someone saw an alert; it stays pending until its event is closed."""

from safevision.application.dto import AlertView
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.presenter import EventPresenter
from safevision.domain.errors import NotFoundError
from safevision.domain.model.values import AlertStatus


class MarkAlertSeen:
    def __init__(self, uow: UnitOfWork, presenter: EventPresenter) -> None:
        self._uow = uow
        self._presenter = presenter

    def execute(self, alert_id: int) -> AlertView:
        """Repeating it is a no-op; a closed alert cannot be marked as seen."""
        with self._uow as uow:
            alert = uow.alerts.get(alert_id)
            if alert is None:
                raise NotFoundError("Alerta", alert_id)
            if alert.status is not AlertStatus.SEEN:
                alert.mark_seen()
                uow.alerts.update(alert)
                uow.commit()
            return self._presenter.present_alert(uow, alert)
