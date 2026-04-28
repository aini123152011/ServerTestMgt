from __future__ import annotations

import abc
from dataclasses import dataclass
from enum import Enum
from typing import Any


class PowerState(str, Enum):
    ON = "on"
    OFF = "off"
    UNKNOWN = "unknown"


@dataclass
class SensorReading:
    name: str
    value: float | None
    unit: str
    status: str


@dataclass
class FirmwareInfo:
    component: str
    version: str
    updateable: bool = True


@dataclass
class FRUData:
    board_manufacturer: str | None = None
    board_product: str | None = None
    board_serial: str | None = None
    board_part_number: str | None = None
    product_manufacturer: str | None = None
    product_name: str | None = None
    product_serial: str | None = None
    product_part_number: str | None = None
    chassis_type: str | None = None
    chassis_serial: str | None = None
    extra: dict[str, str] | None = None


@dataclass
class HardwareInventory:
    cpu_model: str | None = None
    cpu_count: int | None = None
    cpu_cores: int | None = None
    memory_total_gb: float | None = None
    dimm_count: int | None = None
    storage: list[dict[str, Any]] | None = None
    nics: list[dict[str, Any]] | None = None
    bmc_version: str | None = None
    bios_version: str | None = None


class PowerInterface(abc.ABC):
    @abc.abstractmethod
    async def power_on(self) -> bool: ...

    @abc.abstractmethod
    async def power_off(self, force: bool = False) -> bool: ...

    @abc.abstractmethod
    async def power_cycle(self) -> bool: ...

    @abc.abstractmethod
    async def power_reset(self) -> bool: ...

    @abc.abstractmethod
    async def get_power_state(self) -> PowerState: ...


class ManagementInterface(abc.ABC):
    @abc.abstractmethod
    async def get_boot_device(self) -> str: ...

    @abc.abstractmethod
    async def set_boot_device(self, device: str, persistent: bool = False) -> bool: ...

    @abc.abstractmethod
    async def get_sensors(self) -> list[SensorReading]: ...

    @abc.abstractmethod
    async def get_event_log(self, count: int = 50) -> list[dict[str, Any]]: ...

    @abc.abstractmethod
    async def clear_event_log(self) -> bool: ...


class ConsoleInterface(abc.ABC):
    @abc.abstractmethod
    async def start_sol(self) -> Any: ...

    @abc.abstractmethod
    async def stop_sol(self) -> bool: ...


class FirmwareInterface(abc.ABC):
    @abc.abstractmethod
    async def get_firmware_versions(self) -> list[FirmwareInfo]: ...

    @abc.abstractmethod
    async def update_firmware(self, component: str, image_path: str) -> dict[str, Any]: ...


class FRUInterface(abc.ABC):
    @abc.abstractmethod
    async def read_fru(self, fru_id: int = 0) -> FRUData: ...

    @abc.abstractmethod
    async def write_fru(self, fru_id: int, data: dict[str, str]) -> bool: ...


class InspectInterface(abc.ABC):
    @abc.abstractmethod
    async def discover_hardware(self) -> HardwareInventory: ...


class HardwareDriver(
    PowerInterface,
    ManagementInterface,
    ConsoleInterface,
    FirmwareInterface,
    FRUInterface,
    InspectInterface,
):
    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.username = username
        self.password = password
