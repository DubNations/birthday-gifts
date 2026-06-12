from sqlalchemy.orm import Session
from ..models.user_action import UserAction
from ..models.system_config import get_max_regret


def validate_fingerprint(fingerprint_id: str) -> bool:
    """校验手机号格式：11位纯数字"""
    if not fingerprint_id or len(fingerprint_id) != 11:
        return False
    return fingerprint_id.isdigit()


def get_user_actions(db: Session, fingerprint_id: str):
    return db.query(UserAction).filter(
        UserAction.fingerprint_id == fingerprint_id
    ).order_by(UserAction.created_at.desc()).all()


def has_active_lock(db: Session, fingerprint_id: str) -> bool:
    from ..models.gift import Gift
    locked = db.query(Gift).filter(
        Gift.locked_by == fingerprint_id,
        Gift.status == "locked",
    ).first()
    return locked is not None


def get_regret_count(db: Session, fingerprint_id: str) -> int:
    return db.query(UserAction).filter(
        UserAction.fingerprint_id == fingerprint_id,
        UserAction.regret_used == True,
    ).count()


def can_regret(db: Session, fingerprint_id: str) -> bool:
    max_regret = get_max_regret(db)
    return get_regret_count(db, fingerprint_id) < max_regret
