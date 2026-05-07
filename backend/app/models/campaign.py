from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from ..database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    status = Column(String(20), default="active", nullable=False, index=True)
    lock_timeout_minutes = Column(Integer, nullable=False)
    max_regret_chances = Column(Integer, nullable=False)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
