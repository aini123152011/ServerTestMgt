from datetime import datetime

from pydantic import BaseModel

from app.models.provision import ProvisionStatus
from app.schemas.common import TimestampSchema


class OSProfile(BaseModel):
    name: str
    os_type: str  # rhel | ubuntu | suse
    version: str
    kickstart_template: str


class ProvisionJobCreate(BaseModel):
    device_id: int
    os_profile: str
    custom_packages: list[str] | None = None
    post_install_script: str | None = None


class ProvisionJobRead(TimestampSchema):
    id: int
    device_id: int
    user_id: int
    os_profile: str
    status: ProvisionStatus
    kickstart_config: str | None
    custom_packages: dict | None
    post_install_script: str | None
    error_message: str | None
    celery_task_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    # joined
    device_name: str | None = None
    username: str | None = None


class ProvisionCallback(BaseModel):
    provision_job_id: int
    status: str = "completed"  # completed | failed
    message: str | None = None
