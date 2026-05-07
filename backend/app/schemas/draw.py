from decimal import Decimal

from pydantic import BaseModel, field_serializer
from typing import Optional, Dict, List
from datetime import datetime


class PlanRequest(BaseModel):
    budget: Decimal


class DrawPlan(BaseModel):
    plan_type: str
    description: str
    draws: Dict[str, int]
    estimated_cost: Decimal
    min_possible_cost: Decimal
    max_possible_cost: Decimal
    remaining_budget_estimate: Decimal
    explanation: str

    @field_serializer("estimated_cost", "min_possible_cost", "max_possible_cost", "remaining_budget_estimate")
    def serialize_money(self, value: Decimal) -> float:
        return float(value)


class PlansResponse(BaseModel):
    plans: List[DrawPlan]


class DrawStartRequest(BaseModel):
    fingerprint_id: str
    budget: Decimal
    plan_type: str


class DrawStartResponse(BaseModel):
    session_id: int
    draws: Dict[str, int]
    plan_detail: dict


class SpinRequest(BaseModel):
    fingerprint_id: str
    session_id: int


class ClaimRequest(BaseModel):
    fingerprint_id: str
    gift_id: int
    session_id: Optional[int] = None


class ReleaseRequest(BaseModel):
    fingerprint_id: str
    gift_id: int
    session_id: Optional[int] = None


class DrawStatusResponse(BaseModel):
    session_id: int
    status: str
    active_session: Optional[dict] = None
    locked_gift: Optional[dict] = None
    locked_gifts: List[dict]
    claimed_gifts: List[dict]
    remaining_draws: Dict[str, int]
    regret_remaining: int
    next_action: str
