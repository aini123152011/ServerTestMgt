import enum

from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin, TimestampMixin


class DeviceState(str, enum.Enum):
    NEW = "new"
    COMMISSIONING = "commissioning"
    READY = "ready"
    RESERVED = "reserved"
    DEPLOYING = "deploying"
    TESTING = "testing"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


class BmcProtocol(str, enum.Enum):
    IPMI = "ipmi"
    REDFISH = "redfish"


class Device(Base, IDMixin, TimestampMixin):
    __tablename__ = "devices"

    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=True)
    bmc_ip: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    bmc_username: Mapped[str] = mapped_column(String(64), nullable=False)
    bmc_password: Mapped[str] = mapped_column(String(255), nullable=False)
    bmc_protocol: Mapped[BmcProtocol] = mapped_column(Enum(BmcProtocol), default=BmcProtocol.IPMI, nullable=False)
    os_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True)
    state: Mapped[DeviceState] = mapped_column(Enum(DeviceState), default=DeviceState.NEW, nullable=False, index=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    hardware_info: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    VALID_TRANSITIONS: dict[DeviceState, set[DeviceState]] = {
        DeviceState.NEW: {DeviceState.COMMISSIONING, DeviceState.OFFLINE},
        DeviceState.COMMISSIONING: {DeviceState.READY, DeviceState.MAINTENANCE, DeviceState.OFFLINE},
        DeviceState.READY: {DeviceState.RESERVED, DeviceState.DEPLOYING, DeviceState.MAINTENANCE, DeviceState.OFFLINE},
        DeviceState.RESERVED: {DeviceState.DEPLOYING, DeviceState.READY, DeviceState.MAINTENANCE, DeviceState.OFFLINE},
        DeviceState.DEPLOYING: {DeviceState.TESTING, DeviceState.READY, DeviceState.MAINTENANCE, DeviceState.OFFLINE},
        DeviceState.TESTING: {DeviceState.READY, DeviceState.MAINTENANCE, DeviceState.OFFLINE},
        DeviceState.MAINTENANCE: {DeviceState.READY, DeviceState.OFFLINE},
        DeviceState.OFFLINE: {DeviceState.NEW, DeviceState.MAINTENANCE},
    }

    def can_transition_to(self, new_state: DeviceState) -> bool:
        return new_state in self.VALID_TRANSITIONS.get(self.state, set())
