"""FastAPI dependencies shared by the routers."""

from fastapi import Request

from safevision.adapters.inbound.http.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container
