from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.gift import Gift
from ..models.draw_session import DrawSession
from ..schemas.draw import (
    PlanRequest, PlansResponse, DrawPlan,
    DrawStartRequest, DrawStartResponse,
    ClaimRequest, ReleaseRequest, DrawStatusResponse,
)
from ..services.budget_allocator import generate_plans
from ..services.gift_state import (
    draw_random_gift, claim_gift, release_gift,
    get_regret_remaining, release_expired_locks,
)
from ..services.identity import validate_fingerprint, has_active_lock

router = APIRouter(prefix="/api/draw", tags=["draw"])


@router.post("/plans", response_model=PlansResponse)
def get_plans(request: PlanRequest, db: Session = Depends(get_db)):
    if request.budget <= 0:
        raise HTTPException(status_code=400, detail="预算必须大于0")
    release_expired_locks(db)
    plans = generate_plans(request.budget, db)
    return PlansResponse(plans=[DrawPlan(**p) for p in plans])


@router.post("/start", response_model=DrawStartResponse)
def start_draw(request: DrawStartRequest, db: Session = Depends(get_db)):
    if not validate_fingerprint(request.fingerprint_id):
        raise HTTPException(status_code=400, detail="无效的用户标识")
    if has_active_lock(db, request.fingerprint_id):
        raise HTTPException(status_code=400, detail="您还有未处理的抽奖结果")

    release_expired_locks(db)
    plans = generate_plans(request.budget, db)
    selected_plan = None
    for p in plans:
        if p["plan_type"] == request.plan_type:
            selected_plan = p
            break
    if not selected_plan:
        raise HTTPException(status_code=400, detail="无效的方案类型")

    session = DrawSession(
        fingerprint_id=request.fingerprint_id,
        budget=request.budget,
        plan_type=request.plan_type,
        plan_detail=selected_plan["draws"],
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return DrawStartResponse(
        session_id=session.id,
        draws=selected_plan["draws"],
    )


@router.post("/spin")
def spin_gift(tier: str, fingerprint_id: str, db: Session = Depends(get_db)):
    if not validate_fingerprint(fingerprint_id):
        raise HTTPException(status_code=400, detail="无效的用户标识")
    release_expired_locks(db)
    gift = draw_random_gift(db, tier, fingerprint_id)
    if not gift:
        raise HTTPException(status_code=404, detail=f"没有可用的{tier}级礼物")
    return {
        "gift_id": gift.id,
        "name": gift.name,
        "tier": gift.tier,
        "price": gift.price,
        "url": gift.url,
    }


@router.post("/claim")
def claim(request: ClaimRequest, db: Session = Depends(get_db)):
    if not validate_fingerprint(request.fingerprint_id):
        raise HTTPException(status_code=400, detail="无效的用户标识")
    gift = claim_gift(db, request.gift_id, request.fingerprint_id)
    if not gift:
        raise HTTPException(status_code=400, detail="无法确认领取，礼物可能已释放或非您锁定")
    return {"detail": "已确认领取", "gift_id": gift.id, "name": gift.name}


@router.post("/release")
def release(request: ReleaseRequest, db: Session = Depends(get_db)):
    if not validate_fingerprint(request.fingerprint_id):
        raise HTTPException(status_code=400, detail="无效的用户标识")
    gift = release_gift(db, request.gift_id, request.fingerprint_id)
    if not gift:
        raise HTTPException(status_code=400, detail="无法反悔，可能已无反悔机会或礼物非您锁定")
    return {"detail": "已释放礼物", "gift_id": gift.id}


@router.get("/status", response_model=DrawStatusResponse)
def get_status(fingerprint_id: str, db: Session = Depends(get_db)):
    if not validate_fingerprint(fingerprint_id):
        raise HTTPException(status_code=400, detail="无效的用户标识")
    release_expired_locks(db)

    session = db.query(DrawSession).filter(
        DrawSession.fingerprint_id == fingerprint_id,
        DrawSession.status == "active",
    ).order_by(DrawSession.created_at.desc()).first()

    locked_gifts = db.query(Gift).filter(
        Gift.locked_by == fingerprint_id,
        Gift.status == "locked",
    ).all()

    locked_list = [
        {"gift_id": g.id, "name": g.name, "tier": g.tier, "price": g.price, "url": g.url}
        for g in locked_gifts
    ]

    return DrawStatusResponse(
        session_id=session.id if session else 0,
        status=session.status if session else "none",
        locked_gifts=locked_list,
        regret_remaining=get_regret_remaining(db, fingerprint_id),
    )
