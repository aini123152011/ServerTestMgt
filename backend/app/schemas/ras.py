import enum

from pydantic import BaseModel


class RASErrorType(str, enum.Enum):
    CORRECTABLE_MEMORY = "correctable_memory"
    UNCORRECTABLE_MEMORY = "uncorrectable_memory"
    MEMORY_FATAL = "memory_fatal"
    PCIE_CORRECTABLE = "pcie_correctable"
    PCIE_UNCORRECTABLE = "pcie_uncorrectable"
    PCIE_FATAL = "pcie_fatal"
    PROCESSOR_CORRECTABLE = "processor_correctable"
    PROCESSOR_UNCORRECTABLE = "processor_uncorrectable"


class RASInjectRequest(BaseModel):
    device_id: int
    error_type: RASErrorType
    params: dict | None = None  # e.g. {"phys_addr": "0x100000000", "addr_mask": "0xFFF"}


class RASInjectResult(BaseModel):
    injected: bool
    error_type: str
    device_id: int
    sel_entries: list[dict] | None = None
    os_response: str | None = None
    verified: bool = False
    warning: str = "RAS error injection is a destructive operation. Ensure the target device is in a controlled test environment."


class RASVerifyRequest(BaseModel):
    device_id: int
    error_type: RASErrorType


class RASErrorTypeInfo(BaseModel):
    name: str
    value: str
    description: str
    einj_code: int
