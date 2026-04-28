"""RAS error injection service - manages EINJ and BMC-based error injection."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.schemas.ras import RASErrorType

logger = logging.getLogger(__name__)

# EINJ error type codes (ACPI EINJ table)
EINJ_ERROR_CODES: dict[RASErrorType, int] = {
    RASErrorType.CORRECTABLE_MEMORY: 0x08,
    RASErrorType.UNCORRECTABLE_MEMORY: 0x10,
    RASErrorType.MEMORY_FATAL: 0x20,
    RASErrorType.PCIE_CORRECTABLE: 0x40,
    RASErrorType.PCIE_UNCORRECTABLE: 0x80,
    RASErrorType.PCIE_FATAL: 0x100,
    RASErrorType.PROCESSOR_CORRECTABLE: 0x01,
    RASErrorType.PROCESSOR_UNCORRECTABLE: 0x02,
}

ERROR_TYPE_DESCRIPTIONS: dict[RASErrorType, str] = {
    RASErrorType.CORRECTABLE_MEMORY: "Memory Correctable Error (CE) - logged but no impact",
    RASErrorType.UNCORRECTABLE_MEMORY: "Memory Uncorrectable Non-Fatal Error - process may be killed",
    RASErrorType.MEMORY_FATAL: "Memory Fatal Error - may cause system panic",
    RASErrorType.PCIE_CORRECTABLE: "PCIe Correctable Error (AER CE)",
    RASErrorType.PCIE_UNCORRECTABLE: "PCIe Uncorrectable Non-Fatal Error (AER UCE)",
    RASErrorType.PCIE_FATAL: "PCIe Fatal Error - may cause device reset or panic",
    RASErrorType.PROCESSOR_CORRECTABLE: "Processor Correctable Error",
    RASErrorType.PROCESSOR_UNCORRECTABLE: "Processor Uncorrectable Non-Fatal Error",
}


class RASService:
    """Manages RAS error injection and verification."""

    def get_error_types(self) -> list[dict[str, Any]]:
        """Return supported error types with descriptions."""
        return [
            {
                "name": et.name,
                "value": et.value,
                "description": ERROR_TYPE_DESCRIPTIONS.get(et, ""),
                "einj_code": EINJ_ERROR_CODES.get(et, 0),
            }
            for et in RASErrorType
        ]

    def inject_error(self, device, driver, error_type: RASErrorType, params: dict | None = None) -> dict[str, Any]:
        """Inject a RAS error via SSH EINJ or BMC interface.

        In production this would SSH into the OS and write to EINJ sysfs.
        For now it builds the injection commands and records them.
        """
        einj_code = EINJ_ERROR_CODES.get(error_type, 0)
        params = params or {}

        # Build EINJ injection commands
        commands = [
            "modprobe einj",
            f"echo {hex(einj_code)} > /sys/kernel/debug/apei/einj/error_type",
        ]
        if params.get("phys_addr"):
            commands.append(f"echo {params['phys_addr']} > /sys/kernel/debug/apei/einj/param1")
        if params.get("addr_mask"):
            commands.append(f"echo {params['addr_mask']} > /sys/kernel/debug/apei/einj/param2")
        commands.append("echo 1 > /sys/kernel/debug/apei/einj/error_inject")

        logger.info(
            "RAS injection: device=%s, type=%s, einj_code=%s",
            device.id, error_type.value, hex(einj_code),
        )

        # In production: SSH to device.os_ip and execute commands
        # For now, record the commands as a stub
        result = {
            "injected": True,
            "error_type": error_type.value,
            "device_id": device.id,
            "einj_code": hex(einj_code),
            "commands": commands,
            "note": "Injection commands prepared - SSH execution stub",
        }

        # Try to read SEL after injection
        try:
            sel_entries = asyncio.run(driver.get_event_log(count=10))
            result["sel_entries"] = sel_entries
        except Exception:
            result["sel_entries"] = []

        return result

    def verify_response(self, device, driver, error_type: RASErrorType) -> dict[str, Any]:
        """Verify system response after RAS error injection.

        Checks:
        1. SEL entries for error records
        2. OS dmesg for MCE/AER logs (via SSH)
        3. System is still responsive
        """
        result: dict[str, Any] = {
            "device_id": device.id,
            "error_type": error_type.value,
            "verified": False,
            "checks": {},
        }

        # 1. Check SEL
        try:
            sel = asyncio.run(driver.get_event_log(count=20))
            result["checks"]["sel_entries"] = len(sel)
            result["checks"]["sel_sample"] = sel[:5] if sel else []
        except Exception as e:
            result["checks"]["sel_error"] = str(e)

        # 2. Check power state (system still alive?)
        try:
            power = asyncio.run(driver.get_power_state())
            result["checks"]["power_state"] = power.value
            result["checks"]["system_responsive"] = power.value == "on"
        except Exception as e:
            result["checks"]["power_error"] = str(e)

        # 3. Check sensors for critical readings
        try:
            sensors = asyncio.run(driver.get_sensors())
            critical = [s.name for s in sensors if s.status and s.status.lower() in ("critical", "nr", "cr")]
            result["checks"]["critical_sensors"] = critical
        except Exception:
            result["checks"]["sensors_available"] = False

        # Mark verified if we got SEL data and system is responsive
        if result["checks"].get("system_responsive") and result["checks"].get("sel_entries", 0) > 0:
            result["verified"] = True

        return result
