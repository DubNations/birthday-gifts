from sqlalchemy.orm import Session
from ..models.user_action import UserAction
from ..config import MAX_REGRET_CHANCES


def validate_fingerprint(fingerprint_id: str) -> bool:
    if not fingerprint_id or len(fingerprint_id) < 8:
        return False
    return True


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
    return get_regret_count(db, fingerprint_id) < MAX_REGRET_CHANCES
