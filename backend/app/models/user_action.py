from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from ..database import Base


class UserAction(Base):
    __tablename__ = "user_action_log"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)
    fingerprint_id = Column(String(200), nullable=False, index=True)
    gift_id = Column(Integer, ForeignKey("gifts.id"), nullable=True)
    action = Column(String(40), nullable=False)
    regret_used = Column(Boolean, default=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
