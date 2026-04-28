from datetime import datetime

from pydantic import BaseModel

from app.models.firmware import FirmwareJobStatus
from app.schemas.common import TimestampSchema


class FirmwareUpgradeCreate(BaseModel):
    device_id: int | None = None
    device_ids: list[int] | None = None
    component: str
    image_url: str
    target_version: str | None = None


class FirmwareJobRead(TimestampSchema):
    id: int
    device_id: int
    user_id: int
    component: str
    image_url: str
    current_version: str | None
    target_version: str | None
    status: FirmwareJobStatus
    error_message: str | None
    celery_task_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    # joined
    device_name: str | None = None
    username: str | None = None


class FirmwareVersionRead(BaseModel):
    component: str
    version: str
    updateable: bool = True
