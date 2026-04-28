from __future__ import annotations

import logging
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

RESET_TYPE_MAP = {
    "on": "On",
    "off": "ForceOff",
    "graceful_off": "GracefulShutdown",
    "cycle": "ForceRestart",
    "reset": "ForceRestart",
}


class RedfishDriver(HardwareDriver):
    def __init__(self, host: str, username: str, password: str):
        super().__init__(host, username, password)
        self._client = None

    def _get_client(self):
        if self._client is None:
            import redfish
            self._client = redfish.redfish_client(
                base_url=f"https://{self.host}",
                username=self.username,
                password=self.password,
                default_prefix="/redfish/v1",
            )
            self._client.login(auth="session")
        return self._client

    def _close(self):
        if self._client:
            try:
                self._client.logout()
            except Exception:
                pass
            self._client = None

    async def _reset(self, reset_type: str) -> bool:
        try:
            client = self._get_client()
            body = {"ResetType": reset_type}
            resp = client.post("/redfish/v1/Systems/1/Actions/ComputerSystem.Reset", body=body)
            return resp.status in (200, 202, 204)
        except Exception as e:
            logger.error("Redfish reset %s failed: %s", reset_type, e)
            return False

    async def power_on(self) -> bool:
        return await self._reset("On")

    async def power_off(self, force: bool = False) -> bool:
        return await self._reset("ForceOff" if force else "GracefulShutdown")

    async def power_cycle(self) -> bool:
        return await self._reset("ForceRestart")

    async def power_reset(self) -> bool:
        return await self._reset("ForceRestart")

    async def get_power_state(self) -> PowerState:
        try:
            client = self._get_client()
            resp = client.get("/redfish/v1/Systems/1")
            state = resp.dict.get("PowerState", "").lower()
            if state == "on":
                return PowerState.ON
            elif state == "off":
                return PowerState.OFF
            return PowerState.UNKNOWN
        except Exception:
            return PowerState.UNKNOWN

    async def get_boot_device(self) -> str:
        try:
            client = self._get_client()
            resp = client.get("/redfish/v1/Systems/1")
            boot = resp.dict.get("Boot", {})
            return boot.get("BootSourceOverrideTarget", "unknown")
        except Exception:
            return "unknown"

    async def set_boot_device(self, device: str, persistent: bool = False) -> bool:
        try:
            client = self._get_client()
            body = {
                "Boot": {
                    "BootSourceOverrideTarget": device,
                    "BootSourceOverrideEnabled": "Continuous" if persistent else "Once",
                }
            }
            resp = client.patch("/redfish/v1/Systems/1", body=body)
            return resp.status in (200, 202, 204)
        except Exception as e:
            logger.error("Redfish set boot device failed: %s", e)
            return False

    async def get_sensors(self) -> list[SensorReading]:
        sensors = []
        try:
            client = self._get_client()
            thermal = client.get("/redfish/v1/Chassis/1/Thermal").dict
            for t in thermal.get("Temperatures", []):
                sensors.append(SensorReading(
                    name=t.get("Name", ""),
                    value=t.get("ReadingCelsius"),
                    unit="Celsius",
                    status=t.get("Status", {}).get("Health", "OK"),
                ))
            for f in thermal.get("Fans", []):
                sensors.append(SensorReading(
                    name=f.get("Name", ""),
                    value=f.get("Reading"),
                    unit=f.get("ReadingUnits", "RPM"),
                    status=f.get("Status", {}).get("Health", "OK"),
                ))
        except Exception as e:
            logger.warning("Redfish sensor read failed: %s", e)
        return sensors

    async def get_event_log(self, count: int = 50) -> list[dict[str, Any]]:
        try:
            client = self._get_client()
            resp = client.get("/redfish/v1/Systems/1/LogServices/Log1/Entries")
            entries = []
            for entry in resp.dict.get("Members", [])[:count]:
                entries.append({
                    "id": entry.get("Id"),
                    "date": entry.get("Created"),
                    "severity": entry.get("Severity"),
                    "message": entry.get("Message"),
                })
            return entries
        except Exception:
            return []

    async def clear_event_log(self) -> bool:
        try:
            client = self._get_client()
            resp = client.post("/redfish/v1/Systems/1/LogServices/Log1/Actions/LogService.ClearLog", body={})
            return resp.status in (200, 202, 204)
        except Exception:
            return False

    async def start_sol(self) -> Any:
        raise NotImplementedError("Redfish SOL requires vendor-specific virtual media/KVM")

    async def stop_sol(self) -> bool:
        raise NotImplementedError("Redfish SOL requires vendor-specific implementation")

    async def get_firmware_versions(self) -> list[FirmwareInfo]:
        firmwares = []
        try:
            client = self._get_client()
            resp = client.get("/redfish/v1/UpdateService/FirmwareInventory")
            for member in resp.dict.get("Members", []):
                detail = client.get(member["@odata.id"]).dict
                firmwares.append(FirmwareInfo(
                    component=detail.get("Name", "Unknown"),
                    version=detail.get("Version", "Unknown"),
                    updateable=detail.get("Updateable", True),
                ))
        except Exception as e:
            logger.warning("Redfish firmware inventory failed: %s", e)
        return firmwares

    async def update_firmware(self, component: str, image_path: str) -> dict[str, Any]:
        try:
            client = self._get_client()
            body = {
                "ImageURI": image_path,
                "TransferProtocol": "HTTP",
            }
            resp = client.post("/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate", body=body)
            return {"status": resp.status, "task": resp.dict.get("@odata.id")}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def read_fru(self, fru_id: int = 0) -> FRUData:
        try:
            client = self._get_client()
            chassis = client.get("/redfish/v1/Chassis/1").dict
            system = client.get("/redfish/v1/Systems/1").dict
            return FRUData(
                board_manufacturer=chassis.get("Manufacturer"),
                board_product=chassis.get("Model"),
                board_serial=chassis.get("SerialNumber"),
                board_part_number=chassis.get("PartNumber"),
                product_manufacturer=system.get("Manufacturer"),
                product_name=system.get("Model"),
                product_serial=system.get("SerialNumber"),
            )
        except Exception:
            return FRUData()

    async def write_fru(self, fru_id: int, data: dict[str, str]) -> bool:
        raise NotImplementedError("Redfish FRU write requires vendor OEM extensions")

    async def discover_hardware(self) -> HardwareInventory:
        try:
            client = self._get_client()
            system = client.get("/redfish/v1/Systems/1").dict
            proc_col = client.get(f"/redfish/v1/Systems/1/Processors").dict
            mem = system.get("MemorySummary", {})
            mgr = client.get("/redfish/v1/Managers/1").dict
            return HardwareInventory(
                cpu_model=system.get("ProcessorSummary", {}).get("Model"),
                cpu_count=system.get("ProcessorSummary", {}).get("Count"),
                memory_total_gb=mem.get("TotalSystemMemoryGiB"),
                bmc_version=mgr.get("FirmwareVersion"),
                bios_version=system.get("BiosVersion"),
            )
        except Exception as e:
            logger.warning("Redfish hardware discovery failed: %s", e)
            return HardwareInventory()
