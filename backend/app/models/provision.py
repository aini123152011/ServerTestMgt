import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IDMixin, TimestampMixin


class ProvisionStatus(str, enum.Enum):
    PENDING = "pending"
    PROVISIONING = "provisioning"
    INSTALLING = "installing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProvisionJob(Base, IDMixin, TimestampMixin):
    __tablename__ = "provision_jobs"

    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    os_profile: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[ProvisionStatus] = mapped_column(
        Enum(ProvisionStatus), default=ProvisionStatus.PENDING, nullable=False, index=True
    )
    kickstart_config: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_packages: Mapped[dict | None] = mapped_column(JSONB, default=list)
    post_install_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    device = relationship("Device", lazy="selectin")
    user = relationship("User", lazy="selectin")
