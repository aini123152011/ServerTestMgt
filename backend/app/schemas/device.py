from pydantic import BaseModel

from app.models.device import BmcProtocol, DeviceState
from app.schemas.common import TimestampSchema


class DeviceCreate(BaseModel):
    name: str
    hostname: str | None = None
    bmc_ip: str
    bmc_username: str
    bmc_password: str
    bmc_protocol: BmcProtocol = BmcProtocol.IPMI
    os_ip: str | None = None
    mac_address: str | None = None
    model: str | None = None
    serial_number: str | None = None
    location: str | None = None
    tags: dict | None = None
    notes: str | None = None


class DeviceUpdate(BaseModel):
    name: str | None = None
    hostname: str | None = None
    bmc_ip: str | None = None
    bmc_username: str | None = None
    bmc_password: str | None = None
    bmc_protocol: BmcProtocol | None = None
    os_ip: str | None = None
    mac_address: str | None = None
    model: str | None = None
    serial_number: str | None = None
    location: str | None = None
    tags: dict | None = None
    notes: str | None = None


class DeviceRead(TimestampSchema):
    id: int
    name: str
    hostname: str | None
    bmc_ip: str
    bmc_protocol: BmcProtocol
    os_ip: str | None
    mac_address: str | None
    state: DeviceState
    model: str | None
    serial_number: str | None
    location: str | None
    tags: dict | None
    hardware_info: dict | None
    notes: str | None


class DeviceStateTransition(BaseModel):
    state: DeviceState


class PowerAction(BaseModel):
    action: str  # on, off, cycle, reset, status
