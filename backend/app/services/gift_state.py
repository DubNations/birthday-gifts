import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models.gift import Gift
from ..models.user_action import UserAction
from ..config import LOCK_TIMEOUT_MINUTES, MAX_REGRET_CHANCES
from ..models.campaign import Campaign


MAX_LOCK_RETRIES = 5


def lock_gift(db: Session, gift_id: int, fingerprint_id: str, campaign_id: int | None = None) -> Gift:
    """Atomically transition an available gift into a locked gift."""
    now = datetime.now()
    updated = db.query(Gift).filter(
        Gift.id == gift_id,
        Gift.status == "available",
        Gift.campaign_id == campaign_id,
    ).update(
        {
            Gift.status: "locked",
            Gift.locked_by: fingerprint_id,
            Gift.locked_at: now,
        },
        synchronize_session=False,
    )
    if updated != 1:
        db.rollback()
        return None

    log = UserAction(
        campaign_id=campaign_id,
        fingerprint_id=fingerprint_id,
        gift_id=gift_id,
        action="lock",
    )
    db.add(log)
    db.commit()

    gift = db.query(Gift).filter(Gift.id == gift_id).first()
    return gift


def claim_gift(db: Session, gift_id: int, fingerprint_id: str, campaign_id: int | None = None) -> Gift:
    gift = db.query(Gift).filter(
        Gift.id == gift_id,
        Gift.status == "locked",
        Gift.locked_by == fingerprint_id,
        Gift.campaign_id == campaign_id,
    ).with_for_update().first()
    if not gift:
        return None
    gift.status = "claimed"
    gift.locked_by = None
    gift.locked_at = None
    log = UserAction(
        campaign_id=campaign_id,
        fingerprint_id=fingerprint_id,
        gift_id=gift_id,
        action="claim",
    )
    db.add(log)
    db.commit()
    db.refresh(gift)
    return gift


def release_gift(db: Session, gift_id: int, fingerprint_id: str, campaign_id: int | None = None, max_regret_chances: int = MAX_REGRET_CHANCES) -> Gift:
    regret_count = db.query(UserAction).filter(
        UserAction.fingerprint_id == fingerprint_id,
        UserAction.campaign_id == campaign_id,
        UserAction.regret_used == True,
    ).count()

    if regret_count >= max_regret_chances:
        return None

    gift = db.query(Gift).filter(
        Gift.id == gift_id,
        Gift.status == "locked",
        Gift.locked_by == fingerprint_id,
        Gift.campaign_id == campaign_id,
    ).with_for_update().first()
    if not gift:
        return None

    gift.status = "available"
    gift.locked_by = None
    gift.locked_at = None
    log = UserAction(
        campaign_id=campaign_id,
        fingerprint_id=fingerprint_id,
        gift_id=gift_id,
        action="release",
        regret_used=True,
    )
    db.add(log)
    db.commit()
    db.refresh(gift)
    return gift


def release_expired_locks(db: Session, campaign: Campaign | None = None) -> int:
    timeout_minutes = campaign.lock_timeout_minutes if campaign else LOCK_TIMEOUT_MINUTES
    timeout = datetime.now() - timedelta(minutes=timeout_minutes)
    query = db.query(Gift).filter(
        Gift.status == "locked",
        Gift.locked_at < timeout,
    )
    if campaign:
        query = query.filter(Gift.campaign_id == campaign.id)
    expired = query.all()
    count = 0
    for gift in expired:
        original_fp = gift.locked_by
        gift.status = "available"
        gift.locked_by = None
        gift.locked_at = None
        log = UserAction(
            campaign_id=gift.campaign_id,
            fingerprint_id=original_fp or "system",
            gift_id=gift.id,
            action="release",
        )
        db.add(log)
        count += 1
    db.commit()
    return count


def draw_random_gift(db: Session, tier: str, fingerprint_id: str, campaign_id: int | None = None) -> Gift:
    """Draw and lock a random gift with finite retries to avoid races."""
    for _ in range(MAX_LOCK_RETRIES):
        candidates = db.query(Gift.id).filter(
            Gift.tier == tier,
            Gift.status == "available",
            Gift.campaign_id == campaign_id,
        ).order_by(func.random()).limit(MAX_LOCK_RETRIES).all()
        if not candidates:
            return None

        candidate_ids = [candidate.id for candidate in candidates]
        random.shuffle(candidate_ids)
        for gift_id in candidate_ids:
            gift = lock_gift(db, gift_id, fingerprint_id, campaign_id)
            if gift:
                return gift
    return None


def get_regret_remaining(db: Session, fingerprint_id: str, campaign_id: int | None = None, max_regret_chances: int = MAX_REGRET_CHANCES) -> int:
    regret_count = db.query(UserAction).filter(
        UserAction.fingerprint_id == fingerprint_id,
        UserAction.campaign_id == campaign_id,
        UserAction.regret_used == True,
    ).count()
    return max(0, max_regret_chances - regret_count)
