"""Protection of the endpoints used by the IoT module."""

import hmac

from fastapi import Depends, Header, HTTPException

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.dependencies import get_container


def require_iot_key(
    x_api_key: str | None = Header(default=None),
    container: Container = Depends(get_container),
) -> None:
    """Rejects the request with 401 unless X-API-Key matches the configured key.

    The comparison takes constant time, so the key cannot be guessed from how
    long the answer takes.
    """
    provided = (x_api_key or "").encode()
    if not hmac.compare_digest(provided, container.iot_api_key.encode()):
        raise HTTPException(401, "X-API-Key inválida")
