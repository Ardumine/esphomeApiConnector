from typing import Any

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    id: str = Field(..., examples=["greenhouse"])
    address: str = Field(..., examples=["esp-movimento.local"])
    api_key: str | None = Field(default=None, examples=["ZcNzgkp3P3Zk0tX3Z1bjB961UxOZ0GU0JpueBy2obtc"])


class DeviceSummary(BaseModel):
    id: str
    connected: bool
    entity_count: int


class EntityValue(BaseModel):
    name: str
    type: str
    value: Any
    unit: str | None = None


class DeviceEntities(BaseModel):
    device_id: str
    connected: bool
    entities: dict[str, EntityValue]


class MessageResponse(BaseModel):
    detail: str
