import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IDMixin, TimestampMixin


class FirmwareJobStatus(str, enum.Enum):
    PENDING = "pending"
    UPGRADING = "upgrading"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class FirmwareJob(Base, IDMixin, TimestampMixin):
    __tablename__ = "firmware_jobs"

    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    component: Mapped[str] = mapped_column(String(128), nullable=False)
    image_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    current_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[FirmwareJobStatus] = mapped_column(
        Enum(FirmwareJobStatus), default=FirmwareJobStatus.PENDING, nullable=False, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    device = relationship("Device", lazy="selectin")
    user = relationship("User", lazy="selectin")
