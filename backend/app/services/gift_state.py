import random
import time
import functools
from datetime import datetime, timedelta
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from ..models.gift import Gift
from ..models.user_action import UserAction
from ..config import LOCK_TIMEOUT_MINUTES, MAX_REGRET_CHANCES
from ..models.system_config import get_max_regret, SystemConfig


def retry_on_locked(max_retries=3, delay=0.3):
    """SQLite 并发写冲突重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    if 'locked' in str(e).lower() and attempt < max_retries - 1:
                        if args and hasattr(args[0], 'rollback'):
                            args[0].rollback()
                        time.sleep(delay * (attempt + 1))
                    else:
                        raise
        return wrapper
    return decorator


@retry_on_locked()
def lock_gift(db: Session, gift_id: int, fingerprint_id: str) -> Gift:
    """原子化锁定：使用 UPDATE ... WHERE 避免 TOCTOU 竞态"""
    now = datetime.now()
    rows = db.query(Gift).filter(
        Gift.id == gift_id, Gift.status == 'available'
    ).update({
        'status': 'locked',
        'locked_by': fingerprint_id,
        'locked_at': now,
    })
    if rows == 0:
        return None
    log = UserAction(fingerprint_id=fingerprint_id, gift_id=gift_id, action='lock')
    db.add(log)
    db.commit()
    return db.query(Gift).filter(Gift.id == gift_id).first()


@retry_on_locked()
def claim_gift(db: Session, gift_id: int, fingerprint_id: str) -> Gift:
    gift = db.query(Gift).filter(
        Gift.id == gift_id,
        Gift.status == 'locked',
        Gift.locked_by == fingerprint_id,
    ).first()
    if not gift:
        return None
    gift.claimed_by = fingerprint_id
    gift.claimed_at = datetime.now()
    gift.status = 'claimed'
    gift.locked_by = None
    gift.locked_at = None
    log = UserAction(fingerprint_id=fingerprint_id, gift_id=gift_id, action='claim')
    db.add(log)
    db.commit()
    db.refresh(gift)
    return gift


@retry_on_locked()
def release_gift(db: Session, gift_id: int, fingerprint_id: str) -> Gift:
    # 早期写入强制获取 SQLite RESERVED 锁，序列化并发 release 操作
    # 避免两个线程同时读到 regret_count=0 都通过检查的竞态条件
    sentinel = db.query(SystemConfig).filter(SystemConfig.key == '_tx_lock').first()
    if sentinel:
        sentinel.value = str(time.time())
    else:
        db.add(SystemConfig(key='_tx_lock', value=str(time.time())))
    db.flush()  # 立即发送 UPDATE，SQLite 进入 RESERVED 锁模式

    max_regret = get_max_regret(db)
    regret_count = db.query(UserAction).filter(
        UserAction.fingerprint_id == fingerprint_id,
        UserAction.regret_used == True,
    ).count()
    if regret_count >= max_regret:
        db.rollback()
        return None
    gift = db.query(Gift).filter(
        Gift.id == gift_id,
        Gift.status == 'locked',
        Gift.locked_by == fingerprint_id,
    ).first()
    if not gift:
        db.rollback()
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


@retry_on_locked()
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
    max_regret = get_max_regret(db)
    cnt = db.query(UserAction).filter(
        UserAction.fingerprint_id == fingerprint_id,
        UserAction.regret_used == True,
    ).count()
    return max(0, max_regret - cnt)


def get_available_in_budget(db: Session, tier: str, budget: float) -> int:
    return db.query(Gift).filter(
        Gift.tier == tier,
        Gift.status == 'available',
        Gift.price <= budget,
    ).count()
