"""EmailSender over the HTTPS API of Brevo, with the standard library only.

The hosting platform blocks the SMTP ports on its free plan, so the mail leaves
through port 443. There is one attempt per message: whoever needs the link can ask
for it again. Failures are logged with the HTTP status at most, because the body
of the request and of the answer may contain the address or the link.
"""

import http.client
import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from safevision.application.errors import EmailDeliveryError
from safevision.application.ports.email_sender import EmailMessage

logger = logging.getLogger(__name__)

API_URL = "https://api.brevo.com/v3/smtp/email"
TIMEOUT_SECONDS = 10.0
USER_AGENT = "safevision-backend"


class BrevoEmailSender:
    def __init__(
        self,
        api_key: str,
        sender_email: str,
        sender_name: str,
        urlopen: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self._api_key = api_key
        self._sender = {"email": sender_email, "name": sender_name}
        self._urlopen = urlopen

    def send(self, message: EmailMessage) -> None:
        body = {
            "sender": self._sender,
            "to": [{"email": message.to}],
            "subject": message.subject,
            "textContent": message.text,
            "htmlContent": message.html,
        }
        request = urllib.request.Request(
            API_URL,
            data=json.dumps(body).encode(),
            method="POST",
            headers={
                "api-key": self._api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with self._urlopen(request, timeout=TIMEOUT_SECONDS):
                pass
        except urllib.error.HTTPError as error:
            logger.error("e-mail provider refused the message: status=%d", error.code)
            error.close()
            raise EmailDeliveryError() from None
        except (OSError, http.client.HTTPException) as error:  # URLError is an OSError
            logger.error("e-mail provider unreachable: %s", type(error).__name__)
            raise EmailDeliveryError() from None
