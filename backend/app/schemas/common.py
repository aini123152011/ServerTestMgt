from datetime import datetime

from pydantic import BaseModel


class PageParams(BaseModel):
    page: int = 1
    size: int = 20


class PageResult[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


class MessageResponse(BaseModel):
    message: str


class TimestampSchema(BaseModel):
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
