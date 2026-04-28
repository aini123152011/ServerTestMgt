"""Init admin user on first startup."""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session, engine
from app.core.security import hash_password
from app.models.base import Base
from app.models.device import Device  # noqa: F401
from app.models.reservation import Reservation  # noqa: F401
from app.models.job import TestJob, TestJobLog  # noqa: F401
from app.models.provision import ProvisionJob  # noqa: F401
from app.models.firmware import FirmwareJob  # noqa: F401
from app.models.api_key import APIKey  # noqa: F401
from app.models.user import User, UserRole


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == settings.FIRST_ADMIN_USERNAME))
        if not result.scalar_one_or_none():
            admin = User(
                username=settings.FIRST_ADMIN_USERNAME,
                email=f"{settings.FIRST_ADMIN_USERNAME}@servertestlab.local",
                hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
                full_name="Administrator",
                role=UserRole.ADMIN,
            )
            session.add(admin)
            await session.commit()
            print(f"Created admin user: {settings.FIRST_ADMIN_USERNAME}")
        else:
            print("Admin user already exists")


if __name__ == "__main__":
    asyncio.run(init_db())
