from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserActionResponse(BaseModel):
    id: int
    fingerprint_id: str
    gift_id: Optional[int] = None
    action: str
    regret_used: bool
    created_at: datetime

    class Config:
        from_attributes = True
