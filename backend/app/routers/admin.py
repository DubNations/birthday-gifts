import base64
import csv
import hashlib
import hmac
import io
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import ADMIN_PASSWORD, ADMIN_TOKEN_EXPIRE_MINUTES, ADMIN_TOKEN_SECRET, DATABASE_URL
from ..database import get_db
from ..models.gift import Gift
from ..models.user_action import UserAction
from ..schemas.gift import GiftCreate, GiftResponse, GiftUpdate
from ..services.gift_state import release_expired_locks

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminLoginRequest(BaseModel):
    password: str


class AdminLoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_at: datetime


class ResetRequest(BaseModel):
    confirmation: str


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


@router.post("/login", response_model=AdminLoginResponse)
def login(payload: AdminLoginRequest):
    if not hmac.compare_digest(payload.password, ADMIN_PASSWORD):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="管理员密码错误")
    token, expires_at = _create_admin_token()
    return AdminLoginResponse(token=token, expires_at=expires_at)


@router.get("/gifts", response_model=List[GiftResponse])
def list_gifts(db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    release_expired_locks(db)
    return db.query(Gift).order_by(Gift.tier, Gift.price).all()


@router.post("/gifts", response_model=GiftResponse)
def create_gift(gift: GiftCreate, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    if gift.tier not in ("A", "B", "C"):
        raise HTTPException(status_code=400, detail="等级必须是 A、B 或 C")
    db_gift = Gift(**gift.model_dump())
    db.add(db_gift)
    db.commit()
    db.refresh(db_gift)
    return db_gift


@router.put("/gifts/{gift_id}", response_model=GiftResponse)
def update_gift(gift_id: int, gift: GiftUpdate, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    db_gift = db.query(Gift).filter(Gift.id == gift_id).first()
    if not db_gift:
        raise HTTPException(status_code=404, detail="礼物不存在")
    update_data = gift.model_dump(exclude_unset=True)
    if "tier" in update_data and update_data["tier"] not in ("A", "B", "C"):
        raise HTTPException(status_code=400, detail="等级必须是 A、B 或 C")
    for key, value in update_data.items():
        setattr(db_gift, key, value)
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
    db.delete(db_gift)
    db.commit()
    return {"detail": "已删除"}


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    release_expired_locks(db)
    total = db.query(Gift).count()
    available = db.query(Gift).filter(Gift.status == "available").count()
    locked = db.query(Gift).filter(Gift.status == "locked").count()
    claimed = db.query(Gift).filter(Gift.status == "claimed").count()

    tier_stats = {}
    for tier in ["A", "B", "C"]:
        gifts = db.query(Gift).filter(Gift.tier == tier).all()
        tier_stats[tier] = {
            "total": len(gifts),
            "available": len([g for g in gifts if g.status == "available"]),
            "locked": len([g for g in gifts if g.status == "locked"]),
            "claimed": len([g for g in gifts if g.status == "claimed"]),
            "avg_price": round(sum(g.price for g in gifts) / len(gifts), 2) if gifts else 0,
        }

    return {
        "total": total,
        "available": available,
        "locked": locked,
        "claimed": claimed,
        "tiers": tier_stats,
    }


@router.post("/export")
def export_gifts(db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    gifts = db.query(Gift).filter(Gift.status == "claimed").all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "名称", "链接", "价格", "等级", "状态"])
    for g in gifts:
        writer.writerow([g.id, g.name, g.url or "", g.price, g.tier, g.status])
    return {"csv": output.getvalue(), "count": len(gifts)}


@router.post("/reset")
def reset_gifts(payload: ResetRequest, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    if payload.confirmation != "RESET":
        raise HTTPException(status_code=400, detail="请输入 RESET 确认重置")

    snapshot_path = create_data_snapshot("pre_reset")
    db.query(Gift).filter(Gift.status != "claimed").update(
        {"status": "available", "locked_by": None, "locked_at": None}
    )
    db.query(UserAction).delete()
    db.commit()
    return {"detail": "已重置所有礼物状态", "snapshot": snapshot_path}
