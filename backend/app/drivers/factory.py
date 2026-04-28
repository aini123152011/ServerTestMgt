from app.drivers.base import HardwareDriver
from app.drivers.ipmi import IPMIDriver
from app.drivers.redfish import RedfishDriver
from app.models.device import BmcProtocol

_DRIVER_MAP: dict[BmcProtocol, type[HardwareDriver]] = {
    BmcProtocol.IPMI: IPMIDriver,
    BmcProtocol.REDFISH: RedfishDriver,
}


def get_driver(protocol: BmcProtocol, host: str, username: str, password: str) -> HardwareDriver:
    cls = _DRIVER_MAP.get(protocol)
    if cls is None:
        raise ValueError(f"Unsupported BMC protocol: {protocol}")
    return cls(host=host, username=username, password=password)
