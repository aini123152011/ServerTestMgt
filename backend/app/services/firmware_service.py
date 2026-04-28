"""Firmware upgrade service - manages firmware operations via BMC drivers."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.firmware import FirmwareJob, FirmwareJobStatus

logger = logging.getLogger(__name__)


def update_firmware_status(
    session: Session, job: FirmwareJob, new_status: FirmwareJobStatus, error_message: str | None = None
):
    """Update firmware job status and timestamps."""
    job.status = new_status
    now = datetime.now(timezone.utc)
    if new_status == FirmwareJobStatus.UPGRADING and job.started_at is None:
        job.started_at = now
    if new_status in (FirmwareJobStatus.COMPLETED, FirmwareJobStatus.FAILED):
        job.finished_at = now
    if error_message:
        job.error_message = error_message
    session.flush()


def run_firmware_upgrade(session: Session, job: FirmwareJob, device, driver) -> None:
    """Execute firmware upgrade flow.

    Steps:
    1. Read current firmware version
    2. Trigger firmware update via driver
    3. Verify new version after update
    """
    update_firmware_status(session, job, FirmwareJobStatus.UPGRADING)
    session.commit()

    try:
        # 1. Get current firmware versions
        versions = asyncio.run(driver.get_firmware_versions())
        current = next((v for v in versions if v.component.lower() == job.component.lower()), None)
        if current:
            job.current_version = current.version
            session.flush()
            session.commit()

        # 2. Trigger firmware update
        logger.info("Starting firmware upgrade: device=%s, component=%s, image=%s", device.id, job.component, job.image_url)
        result = asyncio.run(driver.update_firmware(job.component, job.image_url))

        if isinstance(result, dict) and result.get("status") == "error":
            update_firmware_status(session, job, FirmwareJobStatus.FAILED, result.get("message", "Update failed"))
            session.commit()
            return

        # 3. Verify - re-read firmware versions
        update_firmware_status(session, job, FirmwareJobStatus.VERIFYING)
        session.commit()

        new_versions = asyncio.run(driver.get_firmware_versions())
        new_ver = next((v for v in new_versions if v.component.lower() == job.component.lower()), None)
        if new_ver:
            job.target_version = new_ver.version

        update_firmware_status(session, job, FirmwareJobStatus.COMPLETED)
        session.commit()
        logger.info("Firmware upgrade completed: device=%s, component=%s", device.id, job.component)

    except Exception as exc:
        update_firmware_status(session, job, FirmwareJobStatus.FAILED, str(exc))
        session.commit()
        raise
