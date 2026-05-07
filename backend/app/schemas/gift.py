from decimal import Decimal

from pydantic import BaseModel, field_serializer
from typing import Optional
from datetime import datetime


class GiftCreate(BaseModel):
    name: str
    url: Optional[str] = None
    price: Decimal
    tier: str
    campaign_id: Optional[int] = None


class GiftUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    price: Optional[Decimal] = None
    tier: Optional[str] = None
    status: Optional[str] = None


class GiftResponse(BaseModel):
    id: int
    campaign_id: Optional[int] = None
    name: str
    url: Optional[str] = None
    price: Decimal
    tier: str
    status: str
    locked_by: Optional[str] = None
    locked_at: Optional[datetime] = None
    created_at: datetime

    @field_serializer("price")
    def serialize_price(self, value: Decimal) -> float:
        return float(value)

    class Config:
        from_attributes = True


class GiftListResponse(BaseModel):
    items: list[GiftResponse]
    total: int
    page: int
    page_size: int
