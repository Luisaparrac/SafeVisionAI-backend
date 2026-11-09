"""Application of the account smoke test: production wiring, except for the mail.

Messages go to the file named by SMOKE_OUTBOX, so the test reads the link there
and nothing ever calls the real provider. Run by uvicorn in an environment with
only the production dependencies, so it imports nothing else.
"""

import json
import os
from pathlib import Path

from safevision.adapters.inbound.http.app import create_app
from safevision.application.ports.email_sender import EmailMessage
from safevision.bootstrap import build_production_container
from safevision.config.settings import Settings


class FileOutbox:
    def __init__(self, path: Path) -> None:
        self._path = path

    def send(self, message: EmailMessage) -> None:
        with self._path.open("a", encoding="utf-8") as outbox:
            outbox.write(json.dumps({"to": message.to, "text": message.text}) + "\n")


app = create_app(
    build_production_container(
        Settings.from_env(), email_sender=FileOutbox(Path(os.environ["SMOKE_OUTBOX"]))
    )
)
