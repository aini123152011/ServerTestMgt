"""CI/CD integration schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CICDTriggerRequest(BaseModel):
    device_name: str | None = None
    device_tags: dict[str, Any] | None = None  # e.g. {"cpu": "intel", "model": "X12"}
    test_type: str  # stress | stability | performance
    config: dict[str, Any] | None = None
    job_name: str | None = None
    callback_url: str | None = None  # webhook URL for completion notification


class CICDTriggerResponse(BaseModel):
    job_id: int
    status: str
    monitor_url: str


class CICDStatusResponse(BaseModel):
    job_id: int
    status: str
    progress: dict[str, Any] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    result_url: str | None = None
    error_message: str | None = None


class APIKeyCreate(BaseModel):
    name: str
    description: str | None = None
    expires_in_days: int | None = None  # None = never expires


class APIKeyCreateResponse(BaseModel):
    id: int
    name: str
    key: str  # raw key, shown only once
    key_prefix: str
    created_at: datetime
    expires_at: datetime | None


class APIKeyRead(BaseModel):
    id: int
    name: str
    key_prefix: str
    user_id: int
    username: str | None = None
    is_active: bool
    description: str | None
    created_at: datetime
    expires_at: datetime | None

    model_config = {"from_attributes": True}
