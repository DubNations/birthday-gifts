from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class GiftCreate(BaseModel):
    name: str
    url: Optional[str] = None
    price: float
    tier: str


class GiftUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    price: Optional[float] = None
    tier: Optional[str] = None
    status: Optional[str] = None


class GiftResponse(BaseModel):
    id: int
    name: str
    url: Optional[str] = None
    price: float
    tier: str
    status: str
    locked_by: Optional[str] = None
    locked_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class GiftListResponse(BaseModel):
    items: list[GiftResponse]
    total: int
    page: int
    page_size: int
