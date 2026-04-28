from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.drivers.factory import get_driver
from app.models.device import Device, DeviceState
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse, PageResult
from app.schemas.device import DeviceCreate, DeviceRead, DeviceStateTransition, DeviceUpdate, PowerAction

router = APIRouter()


@router.get("/", response_model=PageResult[DeviceRead])
async def list_devices(
    page: int = 1,
    size: int = 20,
    state: DeviceState | None = None,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(Device)
    count_query = select(func.count(Device.id))
    if state:
        query = query.where(Device.state == state)
        count_query = count_query.where(Device.state == state)
    if q:
        like = f"%{q}%"
        query = query.where(Device.name.ilike(like) | Device.bmc_ip.ilike(like) | Device.model.ilike(like))
        count_query = count_query.where(Device.name.ilike(like) | Device.bmc_ip.ilike(like) | Device.model.ilike(like))
    total = (await db.execute(count_query)).scalar_one()
    offset = (page - 1) * size
    result = await db.execute(query.offset(offset).limit(size).order_by(Device.id))
    items = list(result.scalars().all())
    return PageResult(items=items, total=total, page=page, size=size, pages=(total + size - 1) // size)


@router.post("/", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
async def create_device(
    body: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.TESTER)),
):
    existing = await db.execute(select(Device).where(Device.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Device name already exists")
    device = Device(**body.model_dump())
    db.add(device)
    await db.flush()
    await db.refresh(device)
    return device


@router.get("/{device_id}", response_model=DeviceRead)
async def get_device(device_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


@router.patch("/{device_id}", response_model=DeviceRead)
async def update_device(
    device_id: int,
    body: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.TESTER)),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(device, field, value)
    await db.flush()
    await db.refresh(device)
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    await db.delete(device)


@router.post("/{device_id}/state", response_model=DeviceRead)
async def transition_state(
    device_id: int,
    body: DeviceStateTransition,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.TESTER)),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    if not device.can_transition_to(body.state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {device.state.value} to {body.state.value}",
        )
    device.state = body.state
    await db.flush()
    await db.refresh(device)
    return device


@router.post("/{device_id}/power", response_model=MessageResponse)
async def power_control(
    device_id: int,
    body: PowerAction,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.TESTER)),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    driver = get_driver(device.bmc_protocol, device.bmc_ip, device.bmc_username, device.bmc_password)
    action_map = {
        "on": driver.power_on,
        "off": driver.power_off,
        "cycle": driver.power_cycle,
        "reset": driver.power_reset,
    }
    if body.action == "status":
        state = await driver.get_power_state()
        return MessageResponse(message=f"Power state: {state.value}")
    fn = action_map.get(body.action)
    if not fn:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown action: {body.action}")
    success = await fn()
    return MessageResponse(message=f"Power {body.action}: {'success' if success else 'failed'}")
