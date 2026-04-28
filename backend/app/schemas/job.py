from datetime import datetime

from pydantic import BaseModel

from app.models.job import JobStatus, JobType, LogLevel
from app.schemas.common import TimestampSchema


# --- Test config schemas (typed JSONB) ---

class StressTestConfig(BaseModel):
    tool: str = "stressapptest"  # stressapptest | memtester | fio
    duration_seconds: int = 3600
    cpu_workers: int | None = None
    memory_mb: int | None = None
    io_target: str | None = None  # block device or file path for fio
    extra_args: str | None = None


class StabilityTestConfig(BaseModel):
    cycle_type: str = "reboot"  # ac_cycle | dc_cycle | reboot
    cycle_count: int = 10
    interval_seconds: int = 60
    wait_boot_seconds: int = 300
    check_sel: bool = True


class PerformanceTestConfig(BaseModel):
    benchmark: str = "unixbench"  # specpu2017 | specjvm | specjbb | unixbench
    config_file: str | None = None
    iterations: int = 1
    extra_args: str | None = None


# --- Job CRUD schemas ---

class TestJobCreate(BaseModel):
    name: str
    device_id: int
    job_type: JobType
    config: dict | None = None


class TestJobUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None


class TestJobRead(TimestampSchema):
    id: int
    name: str
    device_id: int
    user_id: int
    job_type: JobType
    status: JobStatus
    config: dict | None
    result: dict | None
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    celery_task_id: str | None
    # joined fields
    device_name: str | None = None
    username: str | None = None


class TestJobLogRead(BaseModel):
    id: int
    job_id: int
    level: LogLevel
    message: str
    timestamp: datetime

    model_config = {"from_attributes": True}
