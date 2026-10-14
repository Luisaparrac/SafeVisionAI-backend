import ipaddress
from dataclasses import dataclass

from safevision.domain.errors import ValidationError
from safevision.domain.model._checks import required_id, required_text
from safevision.domain.model.values import CameraStatus

IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


@dataclass(kw_only=True)
class Camera:
    """Camera installed in a location and watched by the IoT module."""

    name: str
    ip_address: IpAddress
    location_id: int
    status: CameraStatus = CameraStatus.ACTIVE
    id: int | None = None

    def __post_init__(self) -> None:
        self.name = required_text(self.name, "name")
        self.ip_address = self._parse_ip(self.ip_address)
        self.location_id = required_id(self.location_id, "location_id")
        if isinstance(self.status, str):
            self.status = CameraStatus.parse(self.status)
        self.id = None if self.id is None else required_id(self.id, "id")

    @staticmethod
    def _parse_ip(value: object) -> IpAddress:
        if isinstance(value, IpAddress):
            return value
        try:
            return ipaddress.ip_address(value.strip() if isinstance(value, str) else value)
        except ValueError:
            raise ValidationError(f"Dirección IP inválida: {value!r}") from None

    def change_status(self, status: CameraStatus | str) -> None:
        self.status = CameraStatus.parse(status)
