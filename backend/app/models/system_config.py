from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from ..database import Base


class SystemConfig(Base):
    __tablename__ = "system_config"

    key = Column(String(100), primary_key=True)
    value = Column(String(500), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


def get_config_value(db, key: str, default=None):
    """从数据库读取配置值，不存在则返回默认值"""
    from sqlalchemy.orm import Session
    if not isinstance(db, Session):
        return default
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    return row.value if row else default


def set_config_value(db, key: str, value: str):
    """写入或更新配置值"""
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if row:
        row.value = value
    else:
        row = SystemConfig(key=key, value=value)
        db.add(row)
    db.commit()


def get_max_regret(db) -> int:
    """获取最大反悔次数配置"""
    from ..config import MAX_REGRET_CHANCES
    val = get_config_value(db, 'max_regret_chances', None)
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
    return MAX_REGRET_CHANCES
