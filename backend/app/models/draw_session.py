from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Numeric
from sqlalchemy.sql import func
from ..database import Base


class DrawSession(Base):
    __tablename__ = "draw_sessions"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)
    fingerprint_id = Column(String(200), nullable=False, index=True)
    budget = Column(Numeric(10, 2), nullable=False)
    plan_type = Column(String(50), nullable=True)
    plan_detail = Column(
        JSON,
        nullable=True,
        comment="Recoverable draw progress: original_plan, tier totals/counters, state, and next action.",
    )
    status = Column(String(20), default="active", index=True)
    created_at = Column(DateTime, server_default=func.now())
