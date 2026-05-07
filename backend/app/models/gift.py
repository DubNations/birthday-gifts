from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index
from sqlalchemy.sql import func
from ..database import Base


class Gift(Base):
    __tablename__ = "gifts"
    __table_args__ = (
        Index("ix_gifts_status_tier", "status", "tier"),
        Index("ix_gifts_locked_by_status", "locked_by", "status"),
        Index("ix_gifts_status_locked_at", "status", "locked_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    url = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    tier = Column(String(1), nullable=False)
    status = Column(String(20), default="available")
    locked_by = Column(String(200), nullable=True)
    locked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
