from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.device import Device, DeviceState
from app.models.job import JobStatus, TestJob, TestJobLog
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse, PageResult
from app.schemas.job import TestJobCreate, TestJobLogRead, TestJobRead

router = APIRouter()


def _job_to_read(job: TestJob) -> TestJobRead:
    return TestJobRead(
        id=job.id,
        name=job.name,
        device_id=job.device_id,
        user_id=job.user_id,
        job_type=job.job_type,
        status=job.status,
        config=job.config,
        result=job.result,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error_message=job.error_message,
        celery_task_id=job.celery_task_id,
        created_at=job.created_at,
        updated_at=job.updated_at,
        device_name=job.device.name if job.device else None,
        username=job.user.username if job.user else None,
    )


@router.post("/", response_model=TestJobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: TestJobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TESTER)),
):
    # Verify device exists and is in a valid state for testing
    result = await db.execute(select(Device).where(Device.id == body.device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    if device.state not in (DeviceState.READY, DeviceState.RESERVED, DeviceState.TESTING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Device is in state '{device.state.value}', must be ready/reserved/testing",
        )

    job = TestJob(
        name=body.name,
        device_id=body.device_id,
        user_id=current_user.id,
        job_type=body.job_type,
        config=body.config or {},
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

    return _job_to_read(job)


@router.get("/", response_model=PageResult[TestJobRead])
async def list_jobs(
    page: int = 1,
    size: int = 20,
    status_filter: JobStatus | None = None,
    device_id: int | None = None,
    job_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(TestJob)
    count_query = select(func.count(TestJob.id))

    if status_filter:
        query = query.where(TestJob.status == status_filter)
        count_query = count_query.where(TestJob.status == status_filter)
    if device_id:
        query = query.where(TestJob.device_id == device_id)
        count_query = count_query.where(TestJob.device_id == device_id)
    if job_type:
        query = query.where(TestJob.job_type == job_type)
        count_query = count_query.where(TestJob.job_type == job_type)

    total = (await db.execute(count_query)).scalar_one()
    offset = (page - 1) * size
    result = await db.execute(query.offset(offset).limit(size).order_by(TestJob.id.desc()))
    items = [_job_to_read(j) for j in result.scalars().all()]
    return PageResult(items=items, total=total, page=page, size=size, pages=(total + size - 1) // size)


@router.get("/{job_id}", response_model=TestJobRead)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(TestJob).where(TestJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _job_to_read(job)


@router.post("/{job_id}/cancel", response_model=MessageResponse)
async def cancel_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.TESTER)),
):
    result = await db.execute(select(TestJob).where(TestJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Job already in terminal state: {job.status.value}")

    # Revoke Celery task if possible
    if job.celery_task_id:
        from app.workers.celery_app import celery_app
        celery_app.control.revoke(job.celery_task_id, terminate=True)

    job.status = JobStatus.CANCELLED
    from datetime import datetime, timezone
    job.finished_at = datetime.now(timezone.utc)
    await db.flush()

    # Publish cancel event
    from app.core.websocket import ws_manager
    await ws_manager.publish(f"job:{job_id}:status", {"type": "status", "status": "cancelled"})

    return MessageResponse(message="Job cancelled")


@router.get("/{job_id}/logs", response_model=PageResult[TestJobLogRead])
async def get_job_logs(
    job_id: int,
    page: int = 1,
    size: int = 50,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # Verify job exists
    job_result = await db.execute(select(TestJob).where(TestJob.id == job_id))
    if not job_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    count_query = select(func.count(TestJobLog.id)).where(TestJobLog.job_id == job_id)
    total = (await db.execute(count_query)).scalar_one()
    offset = (page - 1) * size
    query = select(TestJobLog).where(TestJobLog.job_id == job_id).order_by(TestJobLog.timestamp).offset(offset).limit(size)
    result = await db.execute(query)
    items = list(result.scalars().all())
    return PageResult(items=items, total=total, page=page, size=size, pages=(total + size - 1) // size)
