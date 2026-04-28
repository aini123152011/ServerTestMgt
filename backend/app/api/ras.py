from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.drivers.factory import get_driver
from app.models.device import Device
from app.models.user import User, UserRole
from app.schemas.ras import RASErrorType, RASInjectRequest, RASInjectResult, RASVerifyRequest
from app.services.ras_service import RASService

router = APIRouter()
ras_service = RASService()


@router.get("/error-types")
async def list_error_types():
    return ras_service.get_error_types()


@router.post("/inject", response_model=RASInjectResult)
async def inject_error(
    body: RASInjectRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.TESTER)),
):
    device = (await db.execute(select(Device).where(Device.id == body.device_id))).scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    driver = get_driver(device.bmc_protocol, device.bmc_ip, device.bmc_username, device.bmc_password)
    result = ras_service.inject_error(device, driver, body.error_type, body.params)
    return RASInjectResult(**result)


@router.post("/verify")
async def verify_response(
    body: RASVerifyRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.TESTER)),
):
    device = (await db.execute(select(Device).where(Device.id == body.device_id))).scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    driver = get_driver(device.bmc_protocol, device.bmc_ip, device.bmc_username, device.bmc_password)
    return ras_service.verify_response(device, driver, body.error_type)
