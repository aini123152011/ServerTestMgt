from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = 1
    size: int = 20


class PageResult(BaseModel, Generic[T]):
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
