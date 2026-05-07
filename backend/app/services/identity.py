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


def has_active_lock(db: Session, fingerprint_id: str, campaign_id: int | None = None) -> bool:
    from ..models.gift import Gift
    query = db.query(Gift).filter(
        Gift.locked_by == fingerprint_id,
        Gift.status == "locked",
    )
    if campaign_id is not None:
        query = query.filter(Gift.campaign_id == campaign_id)
    locked = query.first()
    return locked is not None


def get_regret_count(db: Session, fingerprint_id: str, campaign_id: int | None = None) -> int:
    query = db.query(UserAction).filter(
        UserAction.fingerprint_id == fingerprint_id,
        UserAction.regret_used == True,
    )
    if campaign_id is not None:
        query = query.filter(UserAction.campaign_id == campaign_id)
    return query.count()


def can_regret(db: Session, fingerprint_id: str, campaign_id: int | None = None, max_regret_chances: int = MAX_REGRET_CHANCES) -> bool:
    return get_regret_count(db, fingerprint_id, campaign_id) < max_regret_chances
