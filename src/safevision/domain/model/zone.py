from dataclasses import dataclass

from safevision.domain.model._checks import optional_text, required_id, required_text
from safevision.domain.model.values import ZonePolygon


@dataclass(kw_only=True)
class Zone:
    """Area inside the image of one camera where detections matter."""

    name: str
    camera_id: int
    polygon: ZonePolygon
    description: str | None = None
    is_active: bool = True
    id: int | None = None

    def __post_init__(self) -> None:
        self.name = required_text(self.name, "name")
        self.camera_id = required_id(self.camera_id, "camera_id")
        if not isinstance(self.polygon, ZonePolygon):
            self.polygon = ZonePolygon.from_list(self.polygon)
        self.description = optional_text(self.description, "description")
        self.is_active = bool(self.is_active)
        self.id = None if self.id is None else required_id(self.id, "id")

    def belongs_to(self, camera_id: int) -> bool:
        return self.camera_id == camera_id

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False
