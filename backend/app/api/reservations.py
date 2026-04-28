from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.device import Device, DeviceState
from app.models.reservation import Reservation, ReservationStatus
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse, PageResult
from app.schemas.reservation import ReservationCreate, ReservationRead

router = APIRouter()


@router.get("/", response_model=PageResult[ReservationRead])
async def list_reservations(
    page: int = 1,
    size: int = 20,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(Reservation)
    count_query = select(func.count(Reservation.id))
    if active_only:
        query = query.where(Reservation.status == ReservationStatus.ACTIVE)
        count_query = count_query.where(Reservation.status == ReservationStatus.ACTIVE)
    total = (await db.execute(count_query)).scalar_one()
    offset = (page - 1) * size
    result = await db.execute(query.offset(offset).limit(size).order_by(Reservation.id.desc()))
    reservations = list(result.scalars().all())
    items = []
    for r in reservations:
        items.append(ReservationRead(
            id=r.id,
            device_id=r.device_id,
            user_id=r.user_id,
            status=r.status,
            expires_at=r.expires_at,
            reason=r.reason,
            device_name=r.device.name if r.device else None,
            username=r.user.username if r.user else None,
            created_at=r.created_at,
            updated_at=r.updated_at,
        ))
    return PageResult(items=items, total=total, page=page, size=size, pages=(total + size - 1) // size)


@router.post("/", response_model=ReservationRead, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    body: ReservationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device_result = await db.execute(select(Device).where(Device.id == body.device_id))
    device = device_result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    if device.state not in (DeviceState.READY,):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Device is not available (state: {device.state.value})")

    active = await db.execute(
        select(Reservation).where(
            and_(Reservation.device_id == body.device_id, Reservation.status == ReservationStatus.ACTIVE)
        )
    )
    if active.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Device is already reserved")

    reservation = Reservation(
        device_id=body.device_id,
        user_id=user.id,
        expires_at=body.expires_at,
        reason=body.reason,
    )
    db.add(reservation)
    device.state = DeviceState.RESERVED
    await db.flush()
    await db.refresh(reservation)
    await db.refresh(device)
    return ReservationRead(
        id=reservation.id,
        device_id=reservation.device_id,
        user_id=reservation.user_id,
        status=reservation.status,
        expires_at=reservation.expires_at,
        reason=reservation.reason,
        device_name=device.name,
        username=user.username,
        created_at=reservation.created_at,
        updated_at=reservation.updated_at,
    )


@router.post("/{reservation_id}/release", response_model=MessageResponse)
async def release_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    if reservation.user_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your reservation")
    if reservation.status != ReservationStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation is not active")

    reservation.status = ReservationStatus.RELEASED
    device_result = await db.execute(select(Device).where(Device.id == reservation.device_id))
    device = device_result.scalar_one_or_none()
    if device and device.state == DeviceState.RESERVED:
        device.state = DeviceState.READY
    await db.flush()
    return MessageResponse(message="Reservation released")
