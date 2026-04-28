from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.drivers.factory import get_driver
from app.models.device import Device
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse
from app.schemas.fru import FRUBatchWriteRequest, FRUDataRead, FRUWriteRequest

router = APIRouter()


@router.post("/{device_id}/read", response_model=FRUDataRead)
async def read_fru(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    device = (await db.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    driver = get_driver(device.bmc_protocol, device.bmc_ip, device.bmc_username, device.bmc_password)
    fru = await driver.read_fru()
    return FRUDataRead(**fru.__dict__)


@router.post("/{device_id}/write", response_model=MessageResponse)
async def write_fru(
    device_id: int, body: FRUWriteRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.TESTER)),
):
    device = (await db.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    driver = get_driver(device.bmc_protocol, device.bmc_ip, device.bmc_username, device.bmc_password)
    ok = await driver.write_fru(0, body.data)
    if not ok:
        raise HTTPException(status_code=500, detail="FRU write failed")
    return MessageResponse(message="FRU data written successfully")


@router.post("/batch-write", response_model=MessageResponse)
async def batch_write_fru(
    body: FRUBatchWriteRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.TESTER)),
):
    success, failed = 0, 0
    for did in body.device_ids:
        device = (await db.execute(select(Device).where(Device.id == did))).scalar_one_or_none()
        if not device:
            failed += 1
            continue
        driver = get_driver(device.bmc_protocol, device.bmc_ip, device.bmc_username, device.bmc_password)
        try:
            ok = await driver.write_fru(0, body.data)
            if ok:
                success += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    return MessageResponse(message=f"FRU batch write: {success} success, {failed} failed")
