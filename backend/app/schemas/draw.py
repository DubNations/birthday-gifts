from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime


class PlanRequest(BaseModel):
    budget: float


class DrawPlan(BaseModel):
    plan_type: str
    description: str
    draws: Dict[str, int]
    estimated_cost: float


class PlansResponse(BaseModel):
    plans: List[DrawPlan]


class DrawStartRequest(BaseModel):
    fingerprint_id: str
    budget: float
    plan_type: str


class DrawStartResponse(BaseModel):
    session_id: int
    draws: Dict[str, int]


class ClaimRequest(BaseModel):
    fingerprint_id: str
    gift_id: int


class ReleaseRequest(BaseModel):
    fingerprint_id: str
    gift_id: int


class DrawStatusResponse(BaseModel):
    session_id: int
    status: str
    locked_gifts: List[dict]
    regret_remaining: int
