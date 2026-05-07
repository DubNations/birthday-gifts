from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from ..database import get_db
from ..models.gift import Gift
from ..models.draw_session import DrawSession
from ..schemas.draw import (
    PlanRequest, PlansResponse, DrawPlan,
    DrawStartRequest, DrawStartResponse, SpinRequest,
    ClaimRequest, ReleaseRequest, DrawStatusResponse,
)
from ..services.budget_allocator import generate_plans
from ..services.gift_state import (
    draw_random_gift, claim_gift, release_gift,
    get_regret_remaining, release_expired_locks,
)
from ..config import MAX_REGRET_CHANCES
from ..services.identity import validate_fingerprint, has_active_lock, get_regret_count

router = APIRouter(prefix="/api/draw", tags=["draw"])

TIERS = ["A", "B", "C"]


def gift_payload(gift: Gift) -> dict:
    return {
        "gift_id": gift.id,
        "name": gift.name,
        "tier": gift.tier,
        "price": gift.price,
        "url": gift.url,
    }


def build_plan_detail(selected_plan: dict) -> dict:
    draws = {tier: int(selected_plan.get("draws", {}).get(tier, 0) or 0) for tier in TIERS}
    return {
        "original_plan": selected_plan,
        "tiers": {
            tier: {
                "total": draws[tier],
                "drawn": 0,
                "claimed": 0,
                "released": 0,
                "status": "pending" if draws[tier] else "completed",
            }
            for tier in TIERS
        },
        "status": "active",
        "current_tier": next((tier for tier in TIERS if draws[tier] > 0), None),
        "next_action": "spin" if sum(draws.values()) > 0 else "completed",
    }


def normalize_plan_detail(session: DrawSession) -> dict:
    detail = session.plan_detail or {}
    if "tiers" not in detail:
        original_draws = detail if isinstance(detail, dict) else {}
        detail = build_plan_detail({
            "plan_type": session.plan_type,
            "description": session.plan_type or "",
            "draws": original_draws,
            "estimated_cost": session.budget,
        })
    for tier in TIERS:
        tier_state = detail.setdefault("tiers", {}).setdefault(tier, {})
        tier_state.setdefault("total", 0)
        tier_state.setdefault("drawn", 0)
        tier_state.setdefault("claimed", 0)
        tier_state.setdefault("released", 0)
        tier_state.setdefault("status", "pending" if tier_state["total"] else "completed")
    detail.setdefault("original_plan", {"draws": {tier: detail["tiers"][tier]["total"] for tier in TIERS}})
    detail.setdefault("status", session.status)
    return detail


def get_next_tier(detail: dict) -> str | None:
    for tier in TIERS:
        tier_state = detail["tiers"][tier]
        if tier_state["claimed"] < tier_state["total"]:
            return tier
    return None


def refresh_session_progress(session: DrawSession, detail: dict | None = None) -> dict:
    detail = detail or normalize_plan_detail(session)
    next_tier = get_next_tier(detail)
    for tier in TIERS:
        tier_state = detail["tiers"][tier]
        if tier_state["claimed"] >= tier_state["total"]:
            tier_state["status"] = "completed"
        elif tier == next_tier:
            tier_state["status"] = "active"
        else:
            tier_state["status"] = "pending"

    if next_tier is None:
        detail["status"] = "completed"
        detail["current_tier"] = None
        detail["next_action"] = "completed"
        session.status = "completed"
    else:
        detail["status"] = "active"
        detail["current_tier"] = next_tier
        detail["next_action"] = "spin"
        session.status = "active"
    session.plan_detail = detail
    flag_modified(session, "plan_detail")
    return detail


def get_active_session(db: Session, fingerprint_id: str) -> DrawSession | None:
    return db.query(DrawSession).filter(
        DrawSession.fingerprint_id == fingerprint_id,
        DrawSession.status == "active",
    ).order_by(DrawSession.created_at.desc()).first()


def get_request_session(db: Session, fingerprint_id: str, session_id: int | None = None) -> DrawSession | None:
    query = db.query(DrawSession).filter(DrawSession.fingerprint_id == fingerprint_id)
    if session_id:
        return query.filter(DrawSession.id == session_id).first()
    return query.filter(DrawSession.status == "active").order_by(DrawSession.created_at.desc()).first()


def status_payload(db: Session, fingerprint_id: str) -> dict:
    session = get_active_session(db, fingerprint_id)
    if not session:
        session = db.query(DrawSession).filter(
            DrawSession.fingerprint_id == fingerprint_id,
            DrawSession.status == "completed",
        ).order_by(DrawSession.created_at.desc()).first()
    locked_gifts = db.query(Gift).filter(
        Gift.locked_by == fingerprint_id,
        Gift.status == "locked",
    ).all()
    from ..models.user_action import UserAction
    claimed_ids = [row.gift_id for row in db.query(UserAction.gift_id).filter(
        UserAction.fingerprint_id == fingerprint_id,
        UserAction.action == "claim",
        UserAction.gift_id.isnot(None),
    ).all()]
    claimed = db.query(Gift).filter(Gift.id.in_(claimed_ids)).all() if claimed_ids else []

    locked_list = [gift_payload(g) for g in locked_gifts]
    claimed_list = [gift_payload(g) for g in claimed]
    locked_gift = locked_list[0] if locked_list else None
    regret_remaining = get_regret_remaining(db, fingerprint_id)
    remaining_draws = {tier: 0 for tier in TIERS}
    active_session = None
    next_action = "start"
    status = "none"
    session_id = 0

    if session:
        detail = refresh_session_progress(session)
        db.commit()
        session_id = session.id
        status = session.status
        remaining_draws = {
            tier: max(0, detail["tiers"][tier]["total"] - detail["tiers"][tier]["claimed"])
            for tier in TIERS
        }
        active_session = {
            "session_id": session.id,
            "budget": session.budget,
            "plan_type": session.plan_type,
            "plan_detail": detail,
            "created_at": session.created_at,
        }
        if session.status == "completed":
            next_action = "completed"
        elif locked_gift:
            next_action = "claim_or_release"
            detail["next_action"] = next_action
        else:
            next_action = "spin"
        session.plan_detail = detail
        flag_modified(session, "plan_detail")
        db.commit()
    elif locked_gift:
        next_action = "claim_or_release"

    return {
        "session_id": session_id,
        "status": status,
        "active_session": active_session,
        "locked_gift": locked_gift,
        "locked_gifts": locked_list,
        "claimed_gifts": claimed_list,
        "remaining_draws": remaining_draws,
        "regret_remaining": regret_remaining,
        "next_action": next_action,
    }


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
    selected_plan = next((p for p in plans if p["plan_type"] == request.plan_type), None)
    if not selected_plan or selected_plan["plan_type"] == "none":
        raise HTTPException(status_code=400, detail="无效的方案类型")

    existing = get_active_session(db, request.fingerprint_id)
    if existing:
        existing.status = "cancelled"
        existing_detail = normalize_plan_detail(existing)
        existing_detail["status"] = "cancelled"
        existing.plan_detail = existing_detail
        flag_modified(existing, "plan_detail")

    plan_detail = build_plan_detail(selected_plan)
    session = DrawSession(
        fingerprint_id=request.fingerprint_id,
        budget=request.budget,
        plan_type=request.plan_type,
        plan_detail=plan_detail,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return DrawStartResponse(
        session_id=session.id,
        draws=selected_plan["draws"],
        plan_detail=session.plan_detail,
    )


@router.post("/spin")
def spin_gift(request: SpinRequest, db: Session = Depends(get_db)):
    if not validate_fingerprint(request.fingerprint_id):
        raise HTTPException(status_code=400, detail="无效的用户标识")
    release_expired_locks(db)

    session = db.query(DrawSession).filter(DrawSession.id == request.session_id).with_for_update().first()
    if not session or session.fingerprint_id != request.fingerprint_id:
        raise HTTPException(status_code=403, detail="抽奖会话不属于当前用户")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="抽奖会话不是进行中状态")
    if has_active_lock(db, request.fingerprint_id):
        raise HTTPException(status_code=400, detail="您还有未处理的抽奖结果")
    if get_regret_count(db, request.fingerprint_id) > MAX_REGRET_CHANCES:
        raise HTTPException(status_code=400, detail="反悔次数异常，已超过允许次数")
    detail = refresh_session_progress(session)
    tier = get_next_tier(detail)
    if not tier:
        db.commit()
        raise HTTPException(status_code=400, detail="抽奖次数已全部完成")

    tier_state = detail["tiers"][tier]
    if tier_state["claimed"] >= tier_state["total"]:
        raise HTTPException(status_code=400, detail=f"{tier}级抽奖次数已用完")

    gift = draw_random_gift(db, tier, request.fingerprint_id)
    if not gift:
        raise HTTPException(status_code=404, detail=f"没有可用的{tier}级礼物")

    tier_state["drawn"] += 1
    detail["current_tier"] = tier
    detail["next_action"] = "claim_or_release"
    session.plan_detail = detail
    flag_modified(session, "plan_detail")
    db.add(session)
    db.commit()
    db.refresh(gift)
    return gift_payload(gift)


@router.post("/claim")
def claim(request: ClaimRequest, db: Session = Depends(get_db)):
    if not validate_fingerprint(request.fingerprint_id):
        raise HTTPException(status_code=400, detail="无效的用户标识")
    session = get_request_session(db, request.fingerprint_id, request.session_id)
    gift = claim_gift(db, request.gift_id, request.fingerprint_id)
    if not gift:
        raise HTTPException(status_code=400, detail="无法确认领取，礼物可能已释放或非您锁定")

    if session:
        detail = normalize_plan_detail(session)
        tier_state = detail["tiers"].get(gift.tier)
        if tier_state:
            tier_state["claimed"] = min(tier_state["total"], tier_state["claimed"] + 1)
        refresh_session_progress(session, detail)
        db.commit()
    return {"detail": "已确认领取", "gift_id": gift.id, "name": gift.name}


@router.post("/release")
def release(request: ReleaseRequest, db: Session = Depends(get_db)):
    if not validate_fingerprint(request.fingerprint_id):
        raise HTTPException(status_code=400, detail="无效的用户标识")
    if get_regret_remaining(db, request.fingerprint_id) <= 0:
        raise HTTPException(status_code=400, detail="反悔次数已用完")
    session = get_request_session(db, request.fingerprint_id, request.session_id)
    gift = release_gift(db, request.gift_id, request.fingerprint_id)
    if not gift:
        raise HTTPException(status_code=400, detail="无法反悔，可能已无反悔机会或礼物非您锁定")

    if session:
        detail = normalize_plan_detail(session)
        tier_state = detail["tiers"].get(gift.tier)
        if tier_state:
            tier_state["released"] += 1
        refresh_session_progress(session, detail)
        db.commit()
    return {"detail": "已释放礼物", "gift_id": gift.id}


@router.get("/status", response_model=DrawStatusResponse)
def get_status(fingerprint_id: str, db: Session = Depends(get_db)):
    if not validate_fingerprint(fingerprint_id):
        raise HTTPException(status_code=400, detail="无效的用户标识")
    release_expired_locks(db)
    return DrawStatusResponse(**status_payload(db, fingerprint_id))
