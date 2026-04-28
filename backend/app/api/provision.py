from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.drivers.factory import get_driver
from app.models.device import Device, DeviceState
from app.models.provision import ProvisionJob, ProvisionStatus
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse, PageResult
from app.schemas.provision import ProvisionCallback, ProvisionJobCreate, ProvisionJobRead
from app.services.pxe_service import PXEService

router = APIRouter()
pxe = PXEService()


@router.get("/profiles")
async def list_profiles():
    return pxe.get_profiles()


@router.get("/", response_model=PageResult[ProvisionJobRead])
async def list_provisions(
    page: int = 1, size: int = 20,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    total = (await db.execute(select(func.count(ProvisionJob.id)))).scalar_one()
    offset = (page - 1) * size
    result = await db.execute(
        select(ProvisionJob).offset(offset).limit(size).order_by(ProvisionJob.id.desc())
    )
    jobs = list(result.scalars().all())
    items = []
    for j in jobs:
        items.append(ProvisionJobRead(
            id=j.id, device_id=j.device_id, user_id=j.user_id, os_profile=j.os_profile,
            status=j.status, kickstart_config=j.kickstart_config,
            custom_packages=j.custom_packages, post_install_script=j.post_install_script,
            error_message=j.error_message, celery_task_id=j.celery_task_id,
            started_at=j.started_at, finished_at=j.finished_at,
            device_name=j.device.name if j.device else None,
            username=j.user.username if j.user else None,
            created_at=j.created_at, updated_at=j.updated_at,
        ))
    return PageResult(items=items, total=total, page=page, size=size, pages=(total + size - 1) // size)


@router.post("/", response_model=ProvisionJobRead, status_code=status.HTTP_201_CREATED)
async def create_provision(
    body: ProvisionJobCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.TESTER)),
):
    device = (await db.execute(select(Device).where(Device.id == body.device_id))).scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if device.state not in (DeviceState.READY, DeviceState.RESERVED):
        raise HTTPException(status_code=400, detail=f"Device not available (state: {device.state.value})")

    callback_url = f"http://localhost:8000/api/v1/provision/callback"
    ks_content = pxe.generate_kickstart(
        body.os_profile, device.name, device.os_ip or device.bmc_ip,
        callback_url, body.custom_packages, body.post_install_script,
    )

    job = ProvisionJob(
        device_id=body.device_id, user_id=user.id, os_profile=body.os_profile,
        kickstart_config=ks_content, custom_packages={"packages": body.custom_packages or []},
        post_install_script=body.post_install_script,
    )
    db.add(job)
    device.state = DeviceState.DEPLOYING
    await db.flush()
    await db.refresh(job)
    return ProvisionJobRead(
        id=job.id, device_id=job.device_id, user_id=job.user_id, os_profile=job.os_profile,
        status=job.status, kickstart_config=job.kickstart_config,
        custom_packages=job.custom_packages, post_install_script=job.post_install_script,
        error_message=None, celery_task_id=None, started_at=None, finished_at=None,
        device_name=device.name, username=user.username,
        created_at=job.created_at, updated_at=job.updated_at,
    )


@router.post("/callback", response_model=MessageResponse)
async def provision_callback(body: ProvisionCallback, db: AsyncSession = Depends(get_db)):
    job = (await db.execute(select(ProvisionJob).where(ProvisionJob.id == body.provision_job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Provision job not found")
    if body.status == "completed":
        job.status = ProvisionStatus.COMPLETED
    else:
        job.status = ProvisionStatus.FAILED
        job.error_message = body.message
    device = (await db.execute(select(Device).where(Device.id == job.device_id))).scalar_one_or_none()
    if device:
        device.state = DeviceState.READY
    await db.flush()
    return MessageResponse(message=f"Provision job {job.id} updated to {job.status.value}")
