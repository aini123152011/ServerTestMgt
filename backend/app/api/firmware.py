from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.drivers.factory import get_driver
from app.models.device import Device
from app.models.firmware import FirmwareJob, FirmwareJobStatus
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse, PageResult
from app.schemas.firmware import FirmwareJobRead, FirmwareUpgradeCreate, FirmwareVersionRead

router = APIRouter()


@router.post("/upgrade", response_model=MessageResponse)
async def upgrade_firmware(
    body: FirmwareUpgradeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.TESTER)),
):
    device_ids = body.device_ids or ([body.device_id] if body.device_id else [])
    if not device_ids:
        raise HTTPException(status_code=400, detail="Provide device_id or device_ids")
    created = []
    for did in device_ids:
        device = (await db.execute(select(Device).where(Device.id == did))).scalar_one_or_none()
        if not device:
            continue
        job = FirmwareJob(
            device_id=did, user_id=user.id, component=body.component,
            image_url=body.image_url, target_version=body.target_version,
        )
        db.add(job)
        created.append(did)
    await db.flush()
    return MessageResponse(message=f"Created firmware upgrade jobs for {len(created)} device(s)")


@router.get("/jobs", response_model=PageResult[FirmwareJobRead])
async def list_firmware_jobs(
    page: int = 1, size: int = 20,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    total = (await db.execute(select(func.count(FirmwareJob.id)))).scalar_one()
    offset = (page - 1) * size
    result = await db.execute(select(FirmwareJob).offset(offset).limit(size).order_by(FirmwareJob.id.desc()))
    jobs = list(result.scalars().all())
    items = []
    for j in jobs:
        items.append(FirmwareJobRead(
            id=j.id, device_id=j.device_id, user_id=j.user_id, component=j.component,
            image_url=j.image_url, current_version=j.current_version, target_version=j.target_version,
            status=j.status, error_message=j.error_message, celery_task_id=j.celery_task_id,
            started_at=j.started_at, finished_at=j.finished_at,
            device_name=j.device.name if j.device else None,
            username=j.user.username if j.user else None,
            created_at=j.created_at, updated_at=j.updated_at,
        ))
    return PageResult(items=items, total=total, page=page, size=size, pages=(total + size - 1) // size)


@router.get("/{device_id}/versions", response_model=list[FirmwareVersionRead])
async def get_firmware_versions(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    device = (await db.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    driver = get_driver(device.bmc_protocol, device.bmc_ip, device.bmc_username, device.bmc_password)
    versions = await driver.get_firmware_versions()
    return [FirmwareVersionRead(component=v.component, version=v.version, updateable=v.updateable) for v in versions]
