"""E-mail sender port: the application does not know which provider delivers it."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class EmailMessage:
    """Addressee and bodies are left out of ``repr``: the bodies carry the reset link."""

    to: str = field(repr=False)
    subject: str
    text: str = field(repr=False)
    html: str = field(repr=False)


@runtime_checkable
class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None:
        """Delivers the message to the provider, or raises ``EmailDeliveryError``."""
        ...
