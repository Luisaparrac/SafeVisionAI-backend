import http.client
import json
import logging
import urllib.error

import pytest

from safevision.adapters.outbound.brevo_email_sender import (
    API_URL,
    TIMEOUT_SECONDS,
    BrevoEmailSender,
)
from safevision.application.errors import EmailDeliveryError
from safevision.application.ports.email_sender import EmailMessage, EmailSender

MESSAGE = EmailMessage(
    to="usuario@example.com",
    subject="Asunto",
    text="enlace ?token=secreto-unico",
    html="<p>enlace ?token=secreto-unico</p>",
)
API_KEY = "clave-ficticia-de-brevo"


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


class FakeOpener:
    """Stands in for urllib: no test opens a connection to the provider."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple] = []

    def __call__(self, request, timeout):
        self.calls.append((request, timeout))
        if self.error is not None:
            raise self.error
        return FakeResponse()


def sender(opener) -> BrevoEmailSender:
    return BrevoEmailSender(API_KEY, "avisos@example.com", "SafeVision AI", urlopen=opener)


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(API_URL, code, "motivo", {}, None)


def test_satisfies_the_port():
    assert isinstance(sender(FakeOpener()), EmailSender)


def test_request_of_the_api():
    opener = FakeOpener()
    sender(opener).send(MESSAGE)
    [(request, timeout)] = opener.calls
    assert request.full_url == "https://api.brevo.com/v3/smtp/email"
    assert request.get_method() == "POST"
    assert timeout == TIMEOUT_SECONDS
    assert request.get_header("Api-key") == API_KEY
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data) == {
        "sender": {"email": "avisos@example.com", "name": "SafeVision AI"},
        "to": [{"email": "usuario@example.com"}],
        "subject": "Asunto",
        "textContent": MESSAGE.text,
        "htmlContent": MESSAGE.html,
    }


@pytest.mark.parametrize("code", [400, 401, 429, 500])
def test_a_refused_message_logs_only_the_status(code, caplog):
    opener = FakeOpener(http_error(code))
    with caplog.at_level(logging.ERROR), pytest.raises(EmailDeliveryError) as error:
        sender(opener).send(MESSAGE)
    assert f"status={code}" in caplog.text
    for secret in (MESSAGE.to, "secreto-unico", API_KEY):
        assert secret not in caplog.text
        assert secret not in str(error.value)
    assert error.value.__cause__ is None
    assert len(opener.calls) == 1  # a single attempt


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.URLError("sin ruta usuario@example.com"),
        TimeoutError("tiempo agotado"),
        http.client.RemoteDisconnected("cerrada"),
    ],
)
def test_a_network_failure_logs_only_its_class(failure, caplog):
    with caplog.at_level(logging.ERROR), pytest.raises(EmailDeliveryError):
        sender(FakeOpener(failure)).send(MESSAGE)
    assert type(failure).__name__ in caplog.text
    assert MESSAGE.to not in caplog.text
