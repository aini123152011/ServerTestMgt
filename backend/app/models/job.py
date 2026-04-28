import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IDMixin, TimestampMixin


class JobType(str, enum.Enum):
    STRESS = "stress"
    STABILITY = "stability"
    PERFORMANCE = "performance"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COLLECTING = "collecting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LogLevel(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class TestJob(Base, IDMixin, TimestampMixin):
    __tablename__ = "test_jobs"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_type: Mapped[JobType] = mapped_column(Enum(JobType), nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True
    )
    config: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    device = relationship("Device", lazy="selectin")
    user = relationship("User", lazy="selectin")


class TestJobLog(Base, IDMixin):
    __tablename__ = "test_job_logs"

    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    level: Mapped[LogLevel] = mapped_column(Enum(LogLevel), default=LogLevel.INFO, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
