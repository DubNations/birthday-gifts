from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class GiftCreate(BaseModel):
    name: str
    url: str
    price: float
    tier: str
    weight: int = 10

    @field_validator('url')
    @classmethod
    def url_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('购买链接不能为空')
        return v.strip()

    @field_validator('price')
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('价格必须大于0')
        return round(v, 2)


class GiftUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    price: Optional[float] = None
    tier: Optional[str] = None
    weight: Optional[int] = None

    @field_validator('url')
    @classmethod
    def url_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError('购买链接不能为空')
        return v.strip() if v else v

    @field_validator('price')
    @classmethod
    def price_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError('价格必须大于0')
        return round(v, 2) if v else v


class GiftStatusUpdate(BaseModel):
    status: str


class GiftResponse(BaseModel):
    id: int
    name: str
    url: Optional[str] = None
    price: float
    tier: str
    weight: int
    status: str
    locked_by: Optional[str] = None
    locked_at: Optional[datetime] = None
    claimed_by: Optional[str] = None
    claimed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
