"""CI/CD integration API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_password
from app.models.api_key import APIKey
from app.models.device import Device, DeviceState
from app.models.job import JobStatus, TestJob
from app.models.user import User
from app.schemas.cicd import CICDStatusResponse, CICDTriggerRequest, CICDTriggerResponse

router = APIRouter()


async def get_api_key_user(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate via API key header. Returns the user who owns the key."""
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-Key header")

    # Find candidate keys by prefix match
    prefix = x_api_key[:8]
    result = await db.execute(
        select(APIKey).where(APIKey.key_prefix == prefix, APIKey.is_active == True)  # noqa: E712
    )
    candidates = result.scalars().all()

    for api_key in candidates:
        if verify_password(x_api_key, api_key.key_hash):
            # Check expiration
            if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")
            user = api_key.user
            if not user or not user.is_active:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Key owner inactive")
            return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@router.post("/trigger", response_model=CICDTriggerResponse)
async def cicd_trigger(
    body: CICDTriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_api_key_user),
):
    """Trigger a test job from CI/CD pipeline."""
    device: Device | None = None

    if body.device_name:
        result = await db.execute(select(Device).where(Device.name == body.device_name))
        device = result.scalar_one_or_none()
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device '{body.device_name}' not found")
    elif body.device_tags:
        # Auto-select a READY device matching all tags
        query = select(Device).where(Device.state == DeviceState.READY)
        result = await db.execute(query)
        candidates = result.scalars().all()
        for candidate in candidates:
            tags = candidate.tags or {}
            if all(tags.get(k) == v for k, v in body.device_tags.items()):
                device = candidate
                break
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No READY device matching tags: {body.device_tags}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either device_name or device_tags",
        )

    if device.state not in (DeviceState.READY, DeviceState.RESERVED, DeviceState.TESTING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Device '{device.name}' is in state '{device.state.value}', must be ready/reserved/testing",
        )

    # Validate test type
    valid_types = {"stress", "stability", "performance"}
    if body.test_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid test_type '{body.test_type}', must be one of: {valid_types}",
        )

    # Store callback_url in config if provided
    config = body.config or {}
    if body.callback_url:
        config["_callback_url"] = body.callback_url

    job = TestJob(
        name=body.job_name or f"CI-{body.test_type}-{device.name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        device_id=device.id,
        user_id=current_user.id,
        job_type=body.test_type,
        config=config,
        status=JobStatus.PENDING,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    # Queue the Celery task
    from app.workers.test_tasks import run_test
    task = run_test.delay(job.id)
    job.celery_task_id = task.id
    job.status = JobStatus.QUEUED
    await db.flush()
    await db.refresh(job)

    return CICDTriggerResponse(
        job_id=job.id,
        status=job.status.value,
        monitor_url=f"/api/v1/cicd/status/{job.id}",
    )


@router.get("/status/{job_id}", response_model=CICDStatusResponse)
async def cicd_status(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_api_key_user),
):
    """Get job status for CI/CD polling."""
    result = await db.execute(select(TestJob).where(TestJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    duration = None
    if job.started_at:
        end = job.finished_at or datetime.now(timezone.utc)
        duration = (end - job.started_at).total_seconds()

    result_url = None
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
        result_url = f"/api/v1/reports/{job.id}"

    return CICDStatusResponse(
        job_id=job.id,
        status=job.status.value,
        progress=job.result if job.status == JobStatus.RUNNING else None,
        started_at=job.started_at,
        finished_at=job.finished_at,
        duration_seconds=round(duration, 1) if duration else None,
        result_url=result_url,
        error_message=job.error_message,
    )


@router.post("/webhook")
async def cicd_webhook_info():
    """Webhook info endpoint. Job completion webhooks are sent automatically
    when a callback_url is provided in the trigger request."""
    return {
        "description": "Webhook callbacks are sent automatically on job completion.",
        "usage": "Include 'callback_url' in your /cicd/trigger request body.",
        "payload_format": {
            "job_id": "int",
            "status": "completed | failed | cancelled",
            "duration_seconds": "float | null",
            "result_url": "string",
        },
    }
