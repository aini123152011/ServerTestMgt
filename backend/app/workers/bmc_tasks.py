"""Background BMC operation tasks."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.drivers.factory import get_driver
from app.models.device import Device
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_sync_engine = None
_sync_session_factory = None


def _get_sync_session() -> Session:
    global _sync_engine, _sync_session_factory
    if _sync_engine is None:
        sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
        _sync_engine = create_engine(sync_url, pool_size=5, max_overflow=5)
        _sync_session_factory = sessionmaker(bind=_sync_engine, expire_on_commit=False)
    return _sync_session_factory()


@celery_app.task(name="bmc_tasks.collect_sensors")
def collect_sensors(device_id: int) -> dict | None:
    """Collect sensor readings from a device's BMC."""
    session = _get_sync_session()
    try:
        device = session.execute(select(Device).where(Device.id == device_id)).scalar_one_or_none()
        if not device:
            logger.warning(f"Device {device_id} not found for sensor collection")
            return None

        driver = get_driver(device.bmc_protocol, device.bmc_ip, device.bmc_username, device.bmc_password)
        sensors = asyncio.run(driver.get_sensors())
        readings = [{"name": s.name, "value": s.value, "unit": s.unit, "status": s.status} for s in sensors]
        logger.info(f"Collected {len(readings)} sensor readings from device {device_id}")
        return {"device_id": device_id, "sensors": readings}
    except Exception:
        logger.exception(f"Failed to collect sensors from device {device_id}")
        return None
    finally:
        session.close()


@celery_app.task(name="bmc_tasks.health_check")
def health_check(device_id: int) -> dict | None:
    """Run a basic health check on a device via BMC."""
    session = _get_sync_session()
    try:
        device = session.execute(select(Device).where(Device.id == device_id)).scalar_one_or_none()
        if not device:
            logger.warning(f"Device {device_id} not found for health check")
            return None

        driver = get_driver(device.bmc_protocol, device.bmc_ip, device.bmc_username, device.bmc_password)

        power_state = asyncio.run(driver.get_power_state())
        result = {"device_id": device_id, "power_state": power_state.value, "healthy": True}

        try:
            sensors = asyncio.run(driver.get_sensors())
            critical = [s for s in sensors if s.status and s.status.lower() in ("critical", "nr", "cr")]
            if critical:
                result["healthy"] = False
                result["critical_sensors"] = [s.name for s in critical]
        except Exception:
            result["sensors_available"] = False

        logger.info(f"Health check device {device_id}: healthy={result['healthy']}")
        return result
    except Exception:
        logger.exception(f"Health check failed for device {device_id}")
        return {"device_id": device_id, "healthy": False, "error": "unreachable"}
    finally:
        session.close()
