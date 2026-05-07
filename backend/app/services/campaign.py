from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..config import LOCK_TIMEOUT_MINUTES, MAX_REGRET_CHANCES
from ..models.campaign import Campaign

DEFAULT_CAMPAIGN_NAME = "默认生日礼物活动"


def get_active_campaign(db: Session) -> Campaign:
    now = datetime.now()
    campaign = db.query(Campaign).filter(
        Campaign.status == "active",
        or_(Campaign.starts_at.is_(None), Campaign.starts_at <= now),
        or_(Campaign.ends_at.is_(None), Campaign.ends_at >= now),
    ).order_by(Campaign.created_at.desc(), Campaign.id.desc()).first()
    if campaign:
        return campaign
    return ensure_default_campaign(db)


def ensure_default_campaign(db: Session) -> Campaign:
    campaign = db.query(Campaign).filter(Campaign.status == "active").order_by(Campaign.id.asc()).first()
    if campaign:
        return campaign
    campaign = Campaign(
        name=DEFAULT_CAMPAIGN_NAME,
        status="active",
        lock_timeout_minutes=LOCK_TIMEOUT_MINUTES,
        max_regret_chances=MAX_REGRET_CHANCES,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign
