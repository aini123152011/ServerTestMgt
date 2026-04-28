"""API Key management endpoints."""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.models.api_key import APIKey
from app.models.user import User, UserRole
from app.schemas.cicd import APIKeyCreate, APIKeyCreateResponse, APIKeyRead

router = APIRouter()


@router.post("/", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a new API key. The raw key is returned only once."""
    raw_key = f"stl_{secrets.token_urlsafe(32)}"
    key_prefix = raw_key[:8]
    key_hash = hash_password(raw_key)

    expires_at = None
    if body.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

    api_key = APIKey(
        name=body.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        user_id=current_user.id,
        is_active=True,
        expires_at=expires_at,
        description=body.description,
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)

    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,
        key_prefix=key_prefix,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
    )


@router.get("/", response_model=list[APIKeyRead])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    """List all API keys."""
    result = await db.execute(select(APIKey).order_by(APIKey.id.desc()))
    keys = result.scalars().all()
    return [
        APIKeyRead(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            user_id=k.user_id,
            username=k.user.username if k.user else None,
            is_active=k.is_active,
            description=k.description,
            created_at=k.created_at,
            expires_at=k.expires_at,
        )
        for k in keys
    ]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    """Revoke (deactivate) an API key."""
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    api_key.is_active = False
    await db.flush()
