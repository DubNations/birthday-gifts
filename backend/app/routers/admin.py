import base64
import csv
import hashlib
import hmac
import io
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from decimal import Decimal
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..config import ADMIN_PASSWORD, ADMIN_TOKEN_EXPIRE_MINUTES, ADMIN_TOKEN_SECRET, DATABASE_URL
from ..database import get_db
from ..models.draw_session import DrawSession
from ..models.gift import Gift
from ..models.user_action import UserAction
from ..schemas.campaign import CampaignResponse, CampaignUpdate
from ..schemas.gift import GiftCreate, GiftListResponse, GiftResponse, GiftUpdate
from ..services.campaign import get_active_campaign
from ..services.gift_state import release_expired_locks

router = APIRouter(prefix="/api/admin", tags=["admin"])

VALID_TIERS = ("A", "B", "C")
VALID_STATUSES = ("available", "locked", "claimed", "disabled")
ADMIN_FINGERPRINT = "admin"


class AdminLoginRequest(BaseModel):
    password: str


class AdminLoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_at: datetime


class ResetRequest(BaseModel):
    confirmation: str


class BulkGiftRequest(BaseModel):
    gift_ids: list[int] = Field(default_factory=list, min_length=1)


class BulkTierRequest(BulkGiftRequest):
    tier: str


class BulkStatusRequest(BulkGiftRequest):
    status: Literal["available", "disabled"]


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(payload: str) -> str:
    return _b64encode(hmac.new(ADMIN_TOKEN_SECRET.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest())


def _create_admin_token() -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ADMIN_TOKEN_EXPIRE_MINUTES)
    payload = _b64encode(json.dumps({"sub": "admin", "exp": int(expires_at.timestamp())}).encode("utf-8"))
    signature = _sign(payload)
    return f"{payload}.{signature}", expires_at


def verify_admin(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少管理员登录凭证")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload, signature = token.split(".", 1)
        expected_signature = _sign(payload)
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("invalid signature")
        claims = json.loads(_b64decode(payload))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="管理员登录凭证无效") from exc

    if claims.get("sub") != "admin" or int(claims.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="管理员登录凭证已过期")
    return True


def _sqlite_database_path() -> Path | None:
    parsed = urlparse(DATABASE_URL)
    if parsed.scheme != "sqlite":
        return None
    if parsed.path in ("", "/:memory:"):
        return None
    if parsed.netloc:
        return None
    return Path(parsed.path.lstrip("/")) if not parsed.path.startswith("//") else Path(parsed.path)


def create_data_snapshot(reason: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = Path("backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    safe_reason = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in reason)
    sqlite_path = _sqlite_database_path()
    if sqlite_path and sqlite_path.exists():
        backup_path = backup_dir / f"gift_{safe_reason}_{timestamp}.db"
        shutil.copy2(sqlite_path, backup_path)
        return str(backup_path)

    backup_path = backup_dir / f"gift_{safe_reason}_{timestamp}.json"
    backup_path.write_text(json.dumps({"created_at": timestamp, "reason": reason}), encoding="utf-8")
    return str(backup_path)


def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def log_admin_action(db: Session, action: str, gift_id: int | None = None, details: dict | None = None, campaign_id: int | None = None):
    log = UserAction(
        campaign_id=campaign_id,
        fingerprint_id=ADMIN_FINGERPRINT,
        gift_id=gift_id,
        action=action[:40],
        details=json.dumps(_json_safe(details or {}), ensure_ascii=False),
    )
    db.add(log)


def _validate_tier(tier: str):
    if tier not in VALID_TIERS:
        raise HTTPException(status_code=400, detail="等级必须是 A、B 或 C")


def _gift_query(db: Session, status_filter: str | None, tier: str | None, q: str | None, min_price: Decimal | None, max_price: Decimal | None, campaign_id: int | None):
    query = db.query(Gift)
    if campaign_id is not None:
        query = query.filter(Gift.campaign_id == campaign_id)
    if status_filter:
        if status_filter not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail="状态必须是 available、locked、claimed 或 disabled")
        query = query.filter(Gift.status == status_filter)
    if tier:
        _validate_tier(tier)
        query = query.filter(Gift.tier == tier)
    if q:
        keyword = f"%{q.strip()}%"
        query = query.filter(or_(Gift.name.ilike(keyword), Gift.url.ilike(keyword)))
    if min_price is not None:
        query = query.filter(Gift.price >= min_price)
    if max_price is not None:
        query = query.filter(Gift.price <= max_price)
    return query


def _csv_response(rows: list[list], headers: list[str]) -> dict:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return {"csv": output.getvalue(), "count": len(rows)}


@router.post("/login", response_model=AdminLoginResponse)
def login(payload: AdminLoginRequest):
    if not hmac.compare_digest(payload.password, ADMIN_PASSWORD):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="管理员密码错误")
    token, expires_at = _create_admin_token()
    return AdminLoginResponse(token=token, expires_at=expires_at)


@router.get("/gifts", response_model=GiftListResponse)
def list_gifts(
    status_filter: str | None = Query(default=None, alias="status"),
    tier: str | None = None,
    q: str | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    auth: bool = Depends(verify_admin),
):
    campaign = get_active_campaign(db)
    release_expired_locks(db, campaign)
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="最低价格不能高于最高价格")
    query = _gift_query(db, status_filter, tier, q, min_price, max_price, campaign.id)
    total = query.count()
    gifts = query.order_by(Gift.tier, Gift.price, Gift.id).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": gifts, "total": total, "page": page, "page_size": page_size}


@router.post("/gifts", response_model=GiftResponse)
def create_gift(gift: GiftCreate, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    _validate_tier(gift.tier)
    campaign = get_active_campaign(db)
    data = gift.model_dump()
    data["campaign_id"] = data.get("campaign_id") or campaign.id
    db_gift = Gift(**data)
    db.add(db_gift)
    db.flush()
    log_admin_action(db, "admin_create", db_gift.id, data, data["campaign_id"])
    db.commit()
    db.refresh(db_gift)
    return db_gift


@router.put("/gifts/{gift_id}", response_model=GiftResponse)
def update_gift(gift_id: int, gift: GiftUpdate, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    db_gift = db.query(Gift).filter(Gift.id == gift_id).first()
    if not db_gift:
        raise HTTPException(status_code=404, detail="礼物不存在")
    update_data = gift.model_dump(exclude_unset=True)
    if "tier" in update_data:
        _validate_tier(update_data["tier"])
    if "status" in update_data and update_data["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="状态必须是 available、locked、claimed 或 disabled")
    before = {key: getattr(db_gift, key) for key in update_data.keys()}
    for key, value in update_data.items():
        setattr(db_gift, key, value)
    log_admin_action(db, "admin_edit", gift_id, {"before": before, "after": update_data}, db_gift.campaign_id)
    db.commit()
    db.refresh(db_gift)
    return db_gift


@router.delete("/gifts/{gift_id}")
def delete_gift(gift_id: int, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    db_gift = db.query(Gift).filter(Gift.id == gift_id).first()
    if not db_gift:
        raise HTTPException(status_code=404, detail="礼物不存在")
    if db_gift.status == "locked":
        raise HTTPException(status_code=400, detail="礼物正在被锁定，无法删除")
    if db_gift.status == "claimed":
        raise HTTPException(status_code=400, detail="礼物已领取，无法删除")
    details = {"name": db_gift.name, "status": db_gift.status, "tier": db_gift.tier, "price": db_gift.price, "campaign_id": db_gift.campaign_id}
    db.query(UserAction).filter(UserAction.gift_id == gift_id).update({UserAction.gift_id: None}, synchronize_session=False)
    db.delete(db_gift)
    log_admin_action(db, "admin_delete", None, {**details, "gift_id": gift_id}, db_gift.campaign_id)
    db.commit()
    return {"detail": "已删除"}


@router.post("/gifts/import")
async def import_gifts(file: UploadFile = File(...), db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    content = await file.read()
    try:
        text_content = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV 文件必须使用 UTF-8 编码") from exc

    reader = csv.DictReader(io.StringIO(text_content))
    aliases = {
        "name": ("name", "名称", "礼物名称"),
        "url": ("url", "链接", "link"),
        "price": ("price", "价格"),
        "tier": ("tier", "等级"),
        "status": ("status", "状态"),
    }
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV 文件缺少表头")

    def pick(row, field):
        for key in aliases[field]:
            if key in row and row[key] not in (None, ""):
                return row[key]
        return None

    campaign = get_active_campaign(db)
    created = 0
    errors = []
    for line_no, row in enumerate(reader, start=2):
        try:
            name = (pick(row, "name") or "").strip()
            tier = (pick(row, "tier") or "").strip().upper()
            price_raw = pick(row, "price")
            if not name:
                raise ValueError("名称不能为空")
            if tier not in VALID_TIERS:
                raise ValueError("等级必须是 A、B 或 C")
            price = Decimal(str(price_raw))
            if price < 0:
                raise ValueError("价格不能为负数")
            gift = Gift(
                campaign_id=campaign.id,
                name=name,
                url=(pick(row, "url") or "").strip() or None,
                price=price,
                tier=tier,
                status=((pick(row, "status") or "available").strip() or "available"),
            )
            if gift.status not in VALID_STATUSES:
                raise ValueError("状态必须是 available、locked、claimed 或 disabled")
            db.add(gift)
            db.flush()
            log_admin_action(db, "admin_import", gift.id, {"filename": file.filename, "line": line_no}, gift.campaign_id)
            created += 1
        except Exception as exc:
            errors.append({"line": line_no, "error": str(exc)})
    if errors:
        db.rollback()
        raise HTTPException(status_code=400, detail={"message": "CSV 导入失败，未写入任何礼物", "errors": errors[:20]})
    db.commit()
    return {"detail": "导入完成", "created": created}


@router.post("/gifts/bulk-delete")
def bulk_delete_gifts(payload: BulkGiftRequest, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    gifts = db.query(Gift).filter(Gift.id.in_(payload.gift_ids)).all()
    missing = set(payload.gift_ids) - {gift.id for gift in gifts}
    blocked = [gift.id for gift in gifts if gift.status in ("locked", "claimed")]
    if missing:
        raise HTTPException(status_code=404, detail=f"礼物不存在：{sorted(missing)}")
    if blocked:
        raise HTTPException(status_code=400, detail=f"仅可删除未领取且未锁定礼物，以下礼物不可删除：{blocked}")
    for gift in gifts:
        deleted_id = gift.id
        log_admin_action(db, "admin_bulk_delete", None, {"gift_id": deleted_id, "name": gift.name, "status": gift.status}, gift.campaign_id)
        db.query(UserAction).filter(UserAction.gift_id == deleted_id).update({UserAction.gift_id: None}, synchronize_session=False)
        db.delete(gift)
    db.commit()
    return {"detail": "批量删除完成", "deleted": len(gifts)}


@router.post("/gifts/bulk-tier")
def bulk_update_tier(payload: BulkTierRequest, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    _validate_tier(payload.tier)
    gifts = db.query(Gift).filter(Gift.id.in_(payload.gift_ids)).all()
    for gift in gifts:
        before = gift.tier
        gift.tier = payload.tier
        log_admin_action(db, "admin_bulk_tier", gift.id, {"before": before, "after": payload.tier}, gift.campaign_id)
    db.commit()
    return {"detail": "批量调整等级完成", "updated": len(gifts)}


@router.post("/gifts/bulk-status")
def bulk_update_status(payload: BulkStatusRequest, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    gifts = db.query(Gift).filter(Gift.id.in_(payload.gift_ids)).all()
    blocked = [gift.id for gift in gifts if gift.status in ("locked", "claimed")]
    if blocked:
        raise HTTPException(status_code=400, detail=f"锁定或已领取礼物不可批量切换可用性：{blocked}")
    for gift in gifts:
        before = gift.status
        gift.status = payload.status
        gift.locked_by = None
        gift.locked_at = None
        log_admin_action(db, "admin_bulk_status", gift.id, {"before": before, "after": payload.status}, gift.campaign_id)
    db.commit()
    return {"detail": "批量状态更新完成", "updated": len(gifts)}


@router.get("/campaign/current", response_model=CampaignResponse)
def get_current_campaign(db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    return get_active_campaign(db)


@router.put("/campaign/current", response_model=CampaignResponse)
def update_current_campaign(payload: CampaignUpdate, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    campaign = get_active_campaign(db)
    update_data = payload.model_dump(exclude_unset=True)
    starts_at = update_data.get("starts_at", campaign.starts_at)
    ends_at = update_data.get("ends_at", campaign.ends_at)
    if starts_at and ends_at and ends_at <= starts_at:
        raise HTTPException(status_code=400, detail="活动结束时间必须晚于开始时间")
    before = {key: getattr(campaign, key) for key in update_data.keys()}
    for key, value in update_data.items():
        setattr(campaign, key, value)
    log_admin_action(db, "admin_campaign", None, {"before": before, "after": update_data}, campaign.id)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    campaign = get_active_campaign(db)
    release_expired_locks(db, campaign)
    total = db.query(Gift).filter(Gift.campaign_id == campaign.id).count()
    available = db.query(Gift).filter(Gift.campaign_id == campaign.id, Gift.status == "available").count()
    locked = db.query(Gift).filter(Gift.campaign_id == campaign.id, Gift.status == "locked").count()
    claimed = db.query(Gift).filter(Gift.campaign_id == campaign.id, Gift.status == "claimed").count()
    disabled = db.query(Gift).filter(Gift.campaign_id == campaign.id, Gift.status == "disabled").count()
    claimed_value = db.query(func.coalesce(func.sum(Gift.price), 0)).filter(Gift.campaign_id == campaign.id, Gift.status == "claimed").scalar() or 0

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_participants = db.query(func.count(func.distinct(UserAction.fingerprint_id))).filter(
        UserAction.created_at >= today_start,
        UserAction.campaign_id == campaign.id,
        UserAction.fingerprint_id != ADMIN_FINGERPRINT,
    ).scalar() or 0
    active_sessions = db.query(DrawSession).filter(DrawSession.campaign_id == campaign.id, DrawSession.status == "active").count()

    tier_stats = {}
    for tier in VALID_TIERS:
        gifts = db.query(Gift).filter(Gift.campaign_id == campaign.id, Gift.tier == tier).all()
        tier_stats[tier] = {
            "total": len(gifts),
            "available": len([g for g in gifts if g.status == "available"]),
            "locked": len([g for g in gifts if g.status == "locked"]),
            "claimed": len([g for g in gifts if g.status == "claimed"]),
            "disabled": len([g for g in gifts if g.status == "disabled"]),
            "remaining": len([g for g in gifts if g.status == "available"]),
            "avg_price": round(float(sum(g.price for g in gifts) / len(gifts)), 2) if gifts else 0,
        }

    now = datetime.now()
    locked_gifts = db.query(Gift).filter(Gift.campaign_id == campaign.id, Gift.status == "locked").order_by(Gift.locked_at.asc()).all()
    locked_details = []
    for gift in locked_gifts:
        expires_at = gift.locked_at + timedelta(minutes=campaign.lock_timeout_minutes) if gift.locked_at else None
        remaining_seconds = max(0, int((expires_at - now).total_seconds())) if expires_at else 0
        locked_details.append({
            "id": gift.id,
            "name": gift.name,
            "tier": gift.tier,
            "locked_by": gift.locked_by,
            "locked_at": gift.locked_at,
            "expires_at": expires_at,
            "remaining_seconds": remaining_seconds,
        })

    recent_actions = db.query(UserAction).filter(UserAction.campaign_id == campaign.id).order_by(UserAction.created_at.desc()).limit(20).all()
    recent_action_payload = [
        {
            "id": action.id,
            "fingerprint_id": action.fingerprint_id,
            "gift_id": action.gift_id,
            "action": action.action,
            "regret_used": action.regret_used,
            "details": action.details,
            "created_at": action.created_at,
        }
        for action in recent_actions
    ]

    return {
        "total": total,
        "available": available,
        "locked": locked,
        "claimed": claimed,
        "disabled": disabled,
        "claimed_value": round(float(claimed_value), 2),
        "today_participants": today_participants,
        "active_sessions": active_sessions,
        "tiers": tier_stats,
        "locked_details": locked_details,
        "recent_actions": recent_action_payload,
        "campaign": CampaignResponse.model_validate(campaign).model_dump(),
    }


@router.post("/export")
def export_gifts(
    export_type: str = Query(default="claimed", pattern="^(claimed|inventory|locked|actions|grouped)$"),
    group_by: str = Query(default="session", pattern="^(session|user)$"),
    db: Session = Depends(get_db),
    auth: bool = Depends(verify_admin),
):
    campaign = get_active_campaign(db)
    release_expired_locks(db, campaign)
    if export_type == "claimed":
        gifts = db.query(Gift).filter(Gift.campaign_id == campaign.id, Gift.status == "claimed").order_by(Gift.tier, Gift.price).all()
        return _csv_response(
            [[g.id, g.name, g.url or "", float(g.price), g.tier, g.status, g.created_at] for g in gifts],
            ["ID", "名称", "链接", "价格", "等级", "状态", "创建时间"],
        )
    if export_type == "inventory":
        gifts = db.query(Gift).filter(Gift.campaign_id == campaign.id).order_by(Gift.tier, Gift.price).all()
        return _csv_response(
            [[g.id, g.name, g.url or "", float(g.price), g.tier, g.status, g.locked_by or "", g.locked_at or "", g.created_at] for g in gifts],
            ["ID", "名称", "链接", "价格", "等级", "状态", "锁定用户", "锁定时间", "创建时间"],
        )
    if export_type == "locked":
        gifts = db.query(Gift).filter(Gift.campaign_id == campaign.id, Gift.status == "locked").order_by(Gift.locked_at.asc()).all()
        return _csv_response(
            [[g.id, g.name, float(g.price), g.tier, g.locked_by or "", g.locked_at or ""] for g in gifts],
            ["ID", "名称", "价格", "等级", "锁定用户", "锁定时间"],
        )
    if export_type == "actions":
        actions = db.query(UserAction).filter(UserAction.campaign_id == campaign.id).order_by(UserAction.created_at.desc()).all()
        return _csv_response(
            [[a.id, a.fingerprint_id, a.gift_id or "", a.action, a.regret_used, a.details or "", a.created_at] for a in actions],
            ["ID", "操作者/用户", "礼物ID", "操作", "是否使用反悔", "详情", "创建时间"],
        )

    claimed_actions = db.query(UserAction).filter(UserAction.campaign_id == campaign.id, UserAction.action == "claim", UserAction.gift_id.isnot(None)).all()
    gift_ids = [action.gift_id for action in claimed_actions]
    gifts_by_id = {gift.id: gift for gift in db.query(Gift).filter(Gift.id.in_(gift_ids)).all()} if gift_ids else {}
    sessions = db.query(DrawSession).filter(DrawSession.campaign_id == campaign.id).order_by(DrawSession.created_at.desc()).all()
    session_by_user = {}
    for session in sessions:
        session_by_user.setdefault(session.fingerprint_id, []).append(session)
    rows = []
    for action in claimed_actions:
        gift = gifts_by_id.get(action.gift_id)
        if not gift:
            continue
        group_value = action.fingerprint_id
        if group_by == "session":
            candidates = session_by_user.get(action.fingerprint_id, [])
            matched = next((s for s in candidates if s.created_at <= action.created_at), None)
            group_value = matched.id if matched else ""
        rows.append([group_value, action.fingerprint_id, gift.id, gift.name, float(gift.price), gift.tier, action.created_at])
    return _csv_response(rows, ["分组", "用户", "礼物ID", "名称", "价格", "等级", "领取时间"])


@router.post("/reset")
def reset_gifts(payload: ResetRequest, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    if payload.confirmation != "RESET":
        raise HTTPException(status_code=400, detail="请输入 RESET 确认重置")

    campaign = get_active_campaign(db)
    snapshot_path = create_data_snapshot("pre_reset")
    db.query(Gift).filter(Gift.campaign_id == campaign.id, Gift.status != "claimed").update(
        {"status": "available", "locked_by": None, "locked_at": None}
    )
    log_admin_action(db, "admin_reset", None, {"snapshot": snapshot_path}, campaign.id)
    db.commit()
    return {"detail": "已重置所有礼物状态", "snapshot": snapshot_path}
