"""Report schemas."""

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ExportFormat(str, enum.Enum):
    JSON = "json"
    CSV = "csv"
    HTML = "html"


class ReportJobInfo(BaseModel):
    id: int
    name: str
    job_type: str
    status: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    duration_seconds: float | None
    error_message: str | None


class ReportDeviceInfo(BaseModel):
    id: int
    name: str
    bmc_ip: str
    bmc_protocol: str
    model: str | None
    serial_number: str | None
    location: str | None


class ReportUserInfo(BaseModel):
    id: int
    username: str
    full_name: str | None


class ReportTimeline(BaseModel):
    event: str
    timestamp: datetime
    detail: str | None = None


class ReportLogSummary(BaseModel):
    total: int
    info_count: int
    warning_count: int
    error_count: int


class ReportData(BaseModel):
    job_info: ReportJobInfo
    device_info: ReportDeviceInfo
    user_info: ReportUserInfo
    test_config: dict[str, Any]
    results: dict[str, Any]
    timeline: list[ReportTimeline]
    log_summary: ReportLogSummary
    generated_at: datetime


class ReportSummary(BaseModel):
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    cancelled_jobs: int
    pass_rate: float
    avg_duration_seconds: float | None
    by_type: dict[str, dict[str, int]]  # {type: {completed: N, failed: N, ...}}
