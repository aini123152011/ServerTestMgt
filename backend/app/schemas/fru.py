from pydantic import BaseModel


class FRUDataRead(BaseModel):
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


class FRUWriteRequest(BaseModel):
    data: dict[str, str]


class FRUBatchWriteRequest(BaseModel):
    device_ids: list[int]
    data: dict[str, str]
