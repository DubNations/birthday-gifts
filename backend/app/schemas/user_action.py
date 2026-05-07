from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserActionResponse(BaseModel):
    id: int
    campaign_id: Optional[int] = None
    fingerprint_id: str
    gift_id: Optional[int] = None
    action: str
    regret_used: bool
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
