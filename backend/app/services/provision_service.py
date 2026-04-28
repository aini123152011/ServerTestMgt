"""Provision orchestration service - coordinates PXE provisioning flow."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.provision import ProvisionJob, ProvisionStatus
from app.services.pxe_service import PXEService

logger = logging.getLogger(__name__)

pxe_service = PXEService()


def update_provision_status(
    session: Session, job: ProvisionJob, new_status: ProvisionStatus, error_message: str | None = None
):
    """Update provision job status and timestamps."""
    job.status = new_status
    now = datetime.now(timezone.utc)
    if new_status == ProvisionStatus.PROVISIONING and job.started_at is None:
        job.started_at = now
    if new_status in (ProvisionStatus.COMPLETED, ProvisionStatus.FAILED):
        job.finished_at = now
    if error_message:
        job.error_message = error_message
    session.flush()


def run_provision(session: Session, job: ProvisionJob, device, driver) -> None:
    """Execute the full PXE provisioning flow.

    Steps:
    1. Generate kickstart/preseed config from template
    2. Add host to dnsmasq DHCP config
    3. Set boot device to PXE via BMC driver
    4. Power cycle the server
    5. Status transitions to INSTALLING (callback will mark COMPLETED)
    """
    import asyncio

    update_provision_status(session, job, ProvisionStatus.PROVISIONING)
    session.commit()

    try:
        # 1. Generate kickstart config
        hostname = device.hostname or device.name
        ip = device.os_ip or device.bmc_ip
        callback_url = f"http://localhost:8000/api/v1/provision/callback"

        kickstart_content = pxe_service.generate_kickstart(
            profile=job.os_profile,
            hostname=hostname,
            ip=ip,
            callback_url=callback_url,
            custom_packages=job.custom_packages if isinstance(job.custom_packages, list) else [],
            post_install_script=job.post_install_script,
        )
        job.kickstart_config = kickstart_content
        session.flush()
        session.commit()

        # 2. Save kickstart to HTTP-served directory
        pxe_service.save_kickstart(hostname, kickstart_content)

        # 3. Add host to dnsmasq
        if device.mac_address:
            pxe_service.add_host(device.mac_address, ip, hostname, job.os_profile)
            pxe_service.reload_dnsmasq()

        # 4. Set boot device to PXE
        asyncio.run(driver.set_boot_device("pxe", persistent=False))
        logger.info("Set boot device to PXE for device %s", device.id)

        # 5. Power cycle
        asyncio.run(driver.power_cycle())
        logger.info("Power cycled device %s for PXE boot", device.id)

        # 6. Mark as installing - callback will mark completed
        update_provision_status(session, job, ProvisionStatus.INSTALLING)
        session.commit()

    except Exception as exc:
        update_provision_status(session, job, ProvisionStatus.FAILED, str(exc))
        session.commit()
        raise
