from safevision.application.dto import AlertNotification


class RecordingNotifier:
    """Keeps every published notification, in order."""

    def __init__(self) -> None:
        self.published: list[AlertNotification] = []

    def publish(self, notification: AlertNotification) -> None:
        self.published.append(notification)
