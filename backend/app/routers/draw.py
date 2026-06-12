from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import OperationalError
from ..database import get_db
from ..models.gift import Gift
from ..models.draw_session import DrawSession
from ..schemas.draw import (
    PlanRequest, PlansResponse, DrawPlan,
    DrawStartRequest, DrawStartResponse, SpinRequest,
    ClaimRequest, ReleaseRequest, DrawStatusResponse,
)
from ..services.budget_allocator import generate_plans, get_tier_stats
from ..services.gift_state import (
    draw_from_tier_with_budget, claim_gift, release_gift,
    get_regret_remaining, release_expired_locks, get_available_in_budget,
)
from ..services.identity import validate_fingerprint, has_active_lock

router = APIRouter(prefix='/api/draw', tags=['draw'])


@router.post('/plans', response_model=PlansResponse)
def get_plans(request: PlanRequest, db: Session = Depends(get_db)):
    if request.budget <= 0:
        raise HTTPException(status_code=400, detail='预算必须大于0')
    release_expired_locks(db)
    plans = generate_plans(request.budget, db)
    return PlansResponse(plans=[DrawPlan(**p) for p in plans])


@router.post('/start', response_model=DrawStartResponse)
def start_draw(request: DrawStartRequest, db: Session = Depends(get_db)):
    if not validate_fingerprint(request.fingerprint_id):
        raise HTTPException(status_code=400, detail='无效的用户标识')
    if request.budget <= 0:
        raise HTTPException(status_code=400, detail='预算必须大于0')
    if has_active_lock(db, request.fingerprint_id):
        raise HTTPException(status_code=400, detail='您还有未处理的抽奖结果')

    release_expired_locks(db)
    plans = generate_plans(request.budget, db)
    selected_plan = None
    for p in plans:
        if p['plan_type'] == request.plan_type:
            selected_plan = p
            break
    if not selected_plan:
        raise HTTPException(status_code=400, detail='无效的方案类型')

    stats = get_tier_stats(db)
    min_prices = {t: stats[t]['min_price'] for t in ['A', 'B', 'C']}

    session = DrawSession(
        fingerprint_id=request.fingerprint_id,
        budget=request.budget,
        remaining_budget=request.budget,
        plan_type=request.plan_type,
        plan_detail=selected_plan['draws'],
        status='active',
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return DrawStartResponse(
        session_id=session.id,
        draws=selected_plan['draws'],
        tier_prices=selected_plan['tier_prices'],
        remaining_budget=session.remaining_budget,
        min_prices=min_prices,
    )


@router.post('/spin')
def spin_gift(request: SpinRequest, db: Session = Depends(get_db)):
    if not validate_fingerprint(request.fingerprint_id):
        raise HTTPException(status_code=400, detail='无效的用户标识')

    release_expired_locks(db)
    session = db.query(DrawSession).filter(
        DrawSession.id == request.session_id,
        DrawSession.fingerprint_id == request.fingerprint_id,
        DrawSession.status == 'active',
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail='抽奖会话不存在或已结束')

    remaining = session.remaining_budget or 0

    # 校验该等级抽奖次数是否超过方案配额
    plan_detail = session.plan_detail or {}
    tier_limit = plan_detail.get(request.tier, 0)
    used_count = db.query(Gift).filter(
        Gift.tier == request.tier,
        Gift.status.in_(['locked', 'claimed']),
        or_(Gift.locked_by == request.fingerprint_id,
            Gift.claimed_by == request.fingerprint_id),
    ).count()
    if used_count >= tier_limit:
        raise HTTPException(status_code=400, detail=f'{request.tier}级抽奖次数已用完')

    # 并发重试：锁定冲突时自动重试
    max_attempts = 3
    gift = None
    err = None
    for attempt in range(max_attempts):
        gift, err = draw_from_tier_with_budget(db, request.tier, request.fingerprint_id, remaining)
        if gift:
            break
        if err == '礼物已被他人锁定':
            db.rollback()
            continue
        raise HTTPException(status_code=404, detail=err or f'没有可用的{request.tier}级礼物')
    else:
        raise HTTPException(status_code=409, detail='当前参与人数较多，请稍后再试')

    # spin 成功后立即扣减预算
    session.remaining_budget = round((session.remaining_budget or 0) - gift.price, 2)
    db.commit()

    avail_count = get_available_in_budget(db, request.tier, session.remaining_budget)

    return {
        'gift_id': gift.id,
        'name': gift.name,
        'tier': gift.tier,
        'price': gift.price,
        'url': gift.url,
        'remaining_budget': session.remaining_budget,
        'available_in_tier': avail_count,
    }


@router.post('/claim')
def claim(request: ClaimRequest, db: Session = Depends(get_db)):
    if not validate_fingerprint(request.fingerprint_id):
        raise HTTPException(status_code=400, detail='无效的用户标识')

    try:
        gift = claim_gift(db, request.gift_id, request.fingerprint_id)
        if not gift:
            raise HTTPException(status_code=400,
                                detail='无法确认领取，礼物可能已释放或非您锁定')

        session = db.query(DrawSession).filter(
            DrawSession.fingerprint_id == request.fingerprint_id,
            DrawSession.status == 'active',
        ).order_by(DrawSession.created_at.desc()).first()

        # 预算已在 spin 时扣减，claim 不再重复扣减
        new_remaining = session.remaining_budget if session else 0
        db.commit()
    except OperationalError:
        db.rollback()
        raise HTTPException(status_code=503, detail='系统繁忙，请稍后重试')

    return {
        'detail': '已确认领取',
        'gift_id': gift.id,
        'name': gift.name,
        'price': gift.price,
        'remaining_budget': new_remaining,
    }


@router.post('/release')
def release(request: ReleaseRequest, db: Session = Depends(get_db)):
    if not validate_fingerprint(request.fingerprint_id):
        raise HTTPException(status_code=400, detail='无效的用户标识')

    gift = release_gift(db, request.gift_id, request.fingerprint_id)
    if not gift:
        raise HTTPException(status_code=400,
                            detail='无法反悔，可能已无反悔机会或礼物非您锁定')

    # 回滚预算
    session = db.query(DrawSession).filter(
        DrawSession.fingerprint_id == request.fingerprint_id,
        DrawSession.status == 'active',
    ).order_by(DrawSession.created_at.desc()).first()
    if session:
        session.remaining_budget = round((session.remaining_budget or 0) + gift.price, 2)
        db.commit()

    return {
        'detail': '已释放礼物',
        'gift_id': gift.id,
        'remaining_budget': session.remaining_budget if session else 0,
    }


@router.get('/status', response_model=DrawStatusResponse)
def get_status(fingerprint_id: str, db: Session = Depends(get_db)):
    if not validate_fingerprint(fingerprint_id):
        raise HTTPException(status_code=400, detail='无效的用户标识')

    release_expired_locks(db)
    session = db.query(DrawSession).filter(
        DrawSession.fingerprint_id == fingerprint_id,
        DrawSession.status == 'active',
    ).order_by(DrawSession.created_at.desc()).first()

    locked_gifts = db.query(Gift).filter(
        Gift.locked_by == fingerprint_id,
        Gift.status == 'locked',
    ).all()

    locked_list = [
        {'gift_id': g.id, 'name': g.name, 'tier': g.tier,
         'price': g.price, 'url': g.url}
        for g in locked_gifts
    ]

    claimed_gifts = db.query(Gift).filter(
        Gift.claimed_by == fingerprint_id,
        Gift.status == 'claimed',
    ).all()
    claimed_list = [
        {'gift_id': g.id, 'name': g.name, 'tier': g.tier,
         'price': g.price, 'url': g.url,
         'claimed_at': g.claimed_at.isoformat() if g.claimed_at else None}
        for g in claimed_gifts
    ]

    return DrawStatusResponse(
        session_id=session.id if session else 0,
        status=session.status if session else 'none',
        remaining_budget=session.remaining_budget if session else 0,
        locked_gifts=locked_list,
        claimed_gifts=claimed_list,
        regret_remaining=get_regret_remaining(db, fingerprint_id),
    )


@router.get('/history')
def get_history(fingerprint_id: str, db: Session = Depends(get_db)):
    """获取用户已领取的礼物历史"""
    if not validate_fingerprint(fingerprint_id):
        raise HTTPException(status_code=400, detail='无效的用户标识')

    claimed_gifts = db.query(Gift).filter(
        Gift.claimed_by == fingerprint_id,
        Gift.status == 'claimed',
    ).order_by(Gift.claimed_at.desc()).all()

    return [
        {
            'gift_id': g.id,
            'name': g.name,
            'tier': g.tier,
            'price': g.price,
            'url': g.url,
            'claimed_at': g.claimed_at.isoformat() if g.claimed_at else None,
        }
        for g in claimed_gifts
    ]
