import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.gift import Gift
from ..models.user_action import UserAction
from ..config import LOCK_TIMEOUT_MINUTES, MAX_REGRET_CHANCES


def lock_gift(db: Session, gift_id: int, fingerprint_id: str) -> Gift:
    gift = db.query(Gift).filter(
        Gift.id == gift_id, Gift.status == 'available'
    ).first()
    if not gift:
        return None
    gift.status = 'locked'
    gift.locked_by = fingerprint_id
    gift.locked_at = datetime.now()
    log = UserAction(fingerprint_id=fingerprint_id, gift_id=gift_id, action='lock')
    db.add(log)
    db.commit()
    db.refresh(gift)
    return gift


def claim_gift(db: Session, gift_id: int, fingerprint_id: str) -> Gift:
    gift = db.query(Gift).filter(
        Gift.id == gift_id,
        Gift.status == 'locked',
        Gift.locked_by == fingerprint_id,
    ).first()
    if not gift:
        return None
    gift.status = 'claimed'
    gift.locked_by = None
    gift.locked_at = None
    log = UserAction(fingerprint_id=fingerprint_id, gift_id=gift_id, action='claim')
    db.add(log)
    db.commit()
    db.refresh(gift)
    return gift


def release_gift(db: Session, gift_id: int, fingerprint_id: str) -> Gift:
    regret_count = db.query(UserAction).filter(
        UserAction.fingerprint_id == fingerprint_id,
        UserAction.regret_used == True,
    ).count()
    if regret_count >= MAX_REGRET_CHANCES:
        return None
    gift = db.query(Gift).filter(
        Gift.id == gift_id,
        Gift.status == 'locked',
        Gift.locked_by == fingerprint_id,
    ).first()
    if not gift:
        return None
    gift.status = 'available'
    gift.locked_by = None
    gift.locked_at = None
    log = UserAction(fingerprint_id=fingerprint_id, gift_id=gift_id,
                     action='release', regret_used=True)
    db.add(log)
    db.commit()
    db.refresh(gift)
    return gift


def release_expired_locks(db: Session) -> int:
    timeout = datetime.now() - timedelta(minutes=LOCK_TIMEOUT_MINUTES)
    expired = db.query(Gift).filter(
        Gift.status == 'locked', Gift.locked_at < timeout
    ).all()
    count = 0
    for gift in expired:
        original_owner = gift.locked_by or 'system'
        gift.status = 'available'
        gift.locked_by = None
        gift.locked_at = None
        log = UserAction(fingerprint_id=original_owner,
                         gift_id=gift.id, action='release')
        db.add(log)
        count += 1
    db.commit()
    return count


def draw_from_tier_with_budget(db: Session, tier: str, fingerprint_id: str,
                                remaining_budget: float):
    available = db.query(Gift).filter(
        Gift.tier == tier,
        Gift.status == 'available',
        Gift.price <= remaining_budget,
    ).all()
    if not available:
        return None, '该等级没有预算范围内的可用礼物，剩余预算不足'
    # 按权重随机抽取
    weights = [g.weight for g in available]
    chosen = random.choices(available, weights=weights, k=1)[0]
    gift = lock_gift(db, chosen.id, fingerprint_id)
    if not gift:
        return None, '礼物已被他人锁定'
    return gift, None


def get_regret_remaining(db: Session, fingerprint_id: str) -> int:
    cnt = db.query(UserAction).filter(
        UserAction.fingerprint_id == fingerprint_id,
        UserAction.regret_used == True,
    ).count()
    return max(0, MAX_REGRET_CHANCES - cnt)


def get_available_in_budget(db: Session, tier: str, budget: float) -> int:
    return db.query(Gift).filter(
        Gift.tier == tier,
        Gift.status == 'available',
        Gift.price <= budget,
    ).count()
