"""E-mail senders for tests: nothing here talks to a real provider."""

from safevision.application.ports.email_sender import EmailMessage


class CapturingEmailSender:
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


class FailingEmailSender:
    def send(self, message: EmailMessage) -> None:
        raise RuntimeError(f"sin entrega a {message.to}")
