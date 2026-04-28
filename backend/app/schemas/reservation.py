from datetime import datetime

from pydantic import BaseModel

from app.models.reservation import ReservationStatus
from app.schemas.common import TimestampSchema


class ReservationCreate(BaseModel):
    device_id: int
    expires_at: datetime
    reason: str | None = None


class ReservationRead(TimestampSchema):
    id: int
    device_id: int
    user_id: int
    status: ReservationStatus
    expires_at: datetime
    reason: str | None
    device_name: str | None = None
    username: str | None = None

    model_config = {"from_attributes": True}
