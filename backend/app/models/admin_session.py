from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from ..database import Base


class AdminSession(Base):
    __tablename__ = 'admin_sessions'

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(200), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(Float, nullable=False)  # Unix timestamp
