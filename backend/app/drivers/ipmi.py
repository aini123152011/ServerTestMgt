from __future__ import annotations

import asyncio
import logging
import subprocess
from typing import Any

from app.drivers.base import (
    FRUData,
    FirmwareInfo,
    HardwareDriver,
    HardwareInventory,
    PowerState,
    SensorReading,
)

logger = logging.getLogger(__name__)


def _run_ipmitool(host: str, user: str, password: str, cmd: str, timeout: int = 30) -> tuple[str, str, int]:
    full_cmd = f"ipmitool -I lanplus -H {host} -U {user} -P {password} {cmd}"
    result = subprocess.run(full_cmd.split(), capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


class IPMIDriver(HardwareDriver):
    def __init__(self, host: str, username: str, password: str):
        super().__init__(host, username, password)
        self._pyghmi_conn = None

    def _get_conn(self):
        if self._pyghmi_conn is None:
            try:
                import pyghmi.ipmi.command as ipmi_cmd
                self._pyghmi_conn = ipmi_cmd.Command(bmc=self.host, userid=self.username, password=self.password)
            except Exception as e:
                logger.warning("pyghmi connection failed, will use ipmitool fallback: %s", e)
        return self._pyghmi_conn

    def _ipmitool(self, cmd: str, timeout: int = 30) -> tuple[str, str, int]:
        return _run_ipmitool(self.host, self.username, self.password, cmd, timeout)

    async def power_on(self) -> bool:
        conn = self._get_conn()
        if conn:
            try:
                conn.set_power("on")
                return True
            except Exception:
                pass
        out, err, rc = await asyncio.to_thread(self._ipmitool, "power on")
        return rc == 0

    async def power_off(self, force: bool = False) -> bool:
        conn = self._get_conn()
        if conn:
            try:
                conn.set_power("off", wait=not force)
                return True
            except Exception:
                pass
        out, err, rc = await asyncio.to_thread(self._ipmitool, "power off")
        return rc == 0

    async def power_cycle(self) -> bool:
        out, err, rc = await asyncio.to_thread(self._ipmitool, "power cycle")
        return rc == 0

    async def power_reset(self) -> bool:
        out, err, rc = await asyncio.to_thread(self._ipmitool, "power reset")
        return rc == 0

    async def get_power_state(self) -> PowerState:
        conn = self._get_conn()
        if conn:
            try:
                state = conn.get_power()
                return PowerState.ON if state.get("powerstate") == "on" else PowerState.OFF
            except Exception:
                pass
        out, err, rc = await asyncio.to_thread(self._ipmitool, "power status")
        if "on" in out.lower():
            return PowerState.ON
        elif "off" in out.lower():
            return PowerState.OFF
        return PowerState.UNKNOWN

    async def get_boot_device(self) -> str:
        out, _, _ = await asyncio.to_thread(self._ipmitool, "chassis bootparam get 5")
        for line in out.splitlines():
            if "Boot Device" in line:
                return line.split(":")[-1].strip()
        return "unknown"

    async def set_boot_device(self, device: str, persistent: bool = False) -> bool:
        cmd = f"chassis bootdev {device}"
        if persistent:
            cmd += " options=persistent"
        _, _, rc = await asyncio.to_thread(self._ipmitool, cmd)
        return rc == 0

    async def get_sensors(self) -> list[SensorReading]:
        out, _, _ = await asyncio.to_thread(self._ipmitool, "sensor list")
        sensors = []
        for line in out.splitlines():
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                name = parts[0]
                try:
                    value = float(parts[1])
                except (ValueError, IndexError):
                    value = None
                unit = parts[2] if len(parts) > 2 else ""
                status = parts[3] if len(parts) > 3 else "ok"
                sensors.append(SensorReading(name=name, value=value, unit=unit, status=status))
        return sensors

    async def get_event_log(self, count: int = 50) -> list[dict[str, Any]]:
        out, _, _ = await asyncio.to_thread(self._ipmitool, "sel list")
        entries = []
        for line in out.splitlines()[:count]:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                entries.append({"id": parts[0], "date": parts[1], "time": parts[2], "message": parts[3]})
        return entries

    async def clear_event_log(self) -> bool:
        _, _, rc = await asyncio.to_thread(self._ipmitool, "sel clear")
        return rc == 0

    async def start_sol(self) -> Any:
        raise NotImplementedError("SOL requires interactive session, use dedicated console service")

    async def stop_sol(self) -> bool:
        _, _, rc = await asyncio.to_thread(self._ipmitool, "sol deactivate")
        return rc == 0

    async def get_firmware_versions(self) -> list[FirmwareInfo]:
        out, _, _ = await asyncio.to_thread(self._ipmitool, "mc info")
        bmc_version = ""
        for line in out.splitlines():
            if "Firmware Revision" in line:
                bmc_version = line.split(":")[-1].strip()
                break
        return [FirmwareInfo(component="BMC", version=bmc_version)]

    async def update_firmware(self, component: str, image_path: str) -> dict[str, Any]:
        raise NotImplementedError("IPMI firmware update requires vendor-specific tools")

    async def read_fru(self, fru_id: int = 0) -> FRUData:
        out, _, _ = await asyncio.to_thread(self._ipmitool, f"fru print {fru_id}")
        data = {}
        for line in out.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                data[key.strip().lower().replace(" ", "_")] = val.strip()
        return FRUData(
            board_manufacturer=data.get("board_mfg"),
            board_product=data.get("board_product"),
            board_serial=data.get("board_serial"),
            board_part_number=data.get("board_part_number"),
            product_manufacturer=data.get("product_manufacturer"),
            product_name=data.get("product_name"),
            product_serial=data.get("product_serial"),
            product_part_number=data.get("product_part_number"),
            extra=data,
        )

    async def write_fru(self, fru_id: int, data: dict[str, str]) -> bool:
        for field_type, fields in [("b", ["board_mfg", "board_product", "board_serial", "board_part_number"])]:
            for idx, key in enumerate(fields):
                if key in data:
                    cmd = f"fru edit {fru_id} field {field_type} {idx} \"{data[key]}\""
                    _, _, rc = await asyncio.to_thread(self._ipmitool, cmd)
                    if rc != 0:
                        return False
        return True

    async def discover_hardware(self) -> HardwareInventory:
        fru = await self.read_fru()
        fw = await self.get_firmware_versions()
        bmc_ver = fw[0].version if fw else None
        return HardwareInventory(
            bmc_version=bmc_ver,
            cpu_model=fru.product_name,
        )
