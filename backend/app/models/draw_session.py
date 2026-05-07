from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.sql import func
from ..database import Base


class DrawSession(Base):
    __tablename__ = "draw_sessions"

    id = Column(Integer, primary_key=True, index=True)
    fingerprint_id = Column(String(200), nullable=False, index=True)
    budget = Column(Float, nullable=False)
    plan_type = Column(String(50), nullable=True)
    plan_detail = Column(JSON, nullable=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, server_default=func.now())
