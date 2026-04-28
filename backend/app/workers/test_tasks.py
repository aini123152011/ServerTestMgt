"""Celery tasks for test execution."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.drivers.factory import get_driver
from app.models.device import Device
from app.models.job import JobStatus, LogLevel, TestJob
from app.services.test_pipeline import (
    PIPELINE_MAP,
    add_job_log,
    publish_job_event,
    update_job_status,
)
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Sync engine for Celery workers (Celery tasks are synchronous)
_sync_engine = None
_sync_session_factory = None


def _get_sync_session() -> Session:
    global _sync_engine, _sync_session_factory
    if _sync_engine is None:
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace("postgresql+psycopg2", "postgresql+psycopg2")
        if "asyncpg" in settings.DATABASE_URL:
            sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
        else:
            sync_url = settings.DATABASE_URL
        _sync_engine = create_engine(sync_url, pool_size=5, max_overflow=5)
        _sync_session_factory = sessionmaker(bind=_sync_engine, expire_on_commit=False)
    return _sync_session_factory()


@celery_app.task(bind=True, name="test_tasks.run_test", acks_late=True)
def run_test(self, job_id: int):
    """Main entry point: dispatch to the correct pipeline based on job_type."""
    session = _get_sync_session()
    try:
        job = session.execute(select(TestJob).where(TestJob.id == job_id)).scalar_one_or_none()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        if job.status == JobStatus.CANCELLED:
            logger.info(f"Job {job_id} already cancelled, skipping")
            return

        device = session.execute(select(Device).where(Device.id == job.device_id)).scalar_one_or_none()
        if not device:
            update_job_status(session, job, JobStatus.FAILED, "Device not found")
            session.commit()
            return

        # Store celery task id
        job.celery_task_id = self.request.id
        update_job_status(session, job, JobStatus.RUNNING)
        session.commit()

        # Get hardware driver
        driver = get_driver(device.bmc_protocol, device.bmc_ip, device.bmc_username, device.bmc_password)

        # Get pipeline class
        pipeline_cls = PIPELINE_MAP.get(job.job_type)
        if not pipeline_cls:
            update_job_status(session, job, JobStatus.FAILED, f"Unknown job type: {job.job_type}")
            session.commit()
            return

        # Run pipeline
        pipeline = pipeline_cls(session, job, device, driver)
        pipeline.run()

        # Mark completed
        update_job_status(session, job, JobStatus.COMPLETED)
        add_job_log(session, job.id, "Job completed successfully")
        session.commit()

    except Exception as exc:
        session.rollback()
        try:
            job = session.execute(select(TestJob).where(TestJob.id == job_id)).scalar_one_or_none()
            if job and job.status not in (JobStatus.COMPLETED, JobStatus.CANCELLED):
                update_job_status(session, job, JobStatus.FAILED, str(exc))
                add_job_log(session, job.id, f"Job failed: {exc}", LogLevel.ERROR)
                session.commit()
        except Exception:
            logger.exception(f"Failed to update job {job_id} status after error")
        logger.exception(f"Test job {job_id} failed")
    finally:
        session.close()


@celery_app.task(bind=True, name="test_tasks.run_stress_test", acks_late=True)
def run_stress_test(self, job_id: int):
    """Convenience alias for stress tests."""
    return run_test(job_id)


@celery_app.task(bind=True, name="test_tasks.run_stability_test", acks_late=True)
def run_stability_test(self, job_id: int):
    """Convenience alias for stability tests."""
    return run_test(job_id)


@celery_app.task(bind=True, name="test_tasks.run_performance_test", acks_late=True)
def run_performance_test(self, job_id: int):
    """Convenience alias for performance tests."""
    return run_test(job_id)
