from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CampaignBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    status: str = Field(default="active", pattern="^(active|draft|ended|paused)$")
    lock_timeout_minutes: int = Field(gt=0, le=24 * 60)
    max_regret_chances: int = Field(ge=0, le=20)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    status: Optional[str] = Field(default=None, pattern="^(active|draft|ended|paused)$")
    lock_timeout_minutes: Optional[int] = Field(default=None, gt=0, le=24 * 60)
    max_regret_chances: Optional[int] = Field(default=None, ge=0, le=20)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class CampaignResponse(CampaignBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
