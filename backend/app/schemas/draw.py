from pydantic import BaseModel
from typing import Optional, Dict, List


class PlanRequest(BaseModel):
    budget: float


class DrawPlan(BaseModel):
    plan_type: str
    description: str
    draws: Dict[str, int]
    tier_prices: Dict[str, float]
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
    tier_prices: Dict[str, float]
    remaining_budget: float


class SpinRequest(BaseModel):
    tier: str
    fingerprint_id: str
    session_id: int


class ClaimRequest(BaseModel):
    fingerprint_id: str
    gift_id: int


class ReleaseRequest(BaseModel):
    fingerprint_id: str
    gift_id: int


class DrawStatusResponse(BaseModel):
    session_id: int
    status: str
    remaining_budget: float
    locked_gifts: List[dict]
    regret_remaining: int
