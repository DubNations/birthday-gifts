import csv
import io
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.gift import Gift
from ..models.user_action import UserAction
from ..schemas.gift import GiftCreate, GiftUpdate, GiftResponse
from ..config import ADMIN_PASSWORD
from ..services.gift_state import release_expired_locks

router = APIRouter(prefix="/api/admin", tags=["admin"])


def verify_admin(password: str = Query(...)):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="管理员密码错误")
    return True


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
def reset_gifts(db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    db.query(Gift).filter(Gift.status != "claimed").update(
        {"status": "available", "locked_by": None, "locked_at": None}
    )
    db.query(UserAction).delete()
    db.commit()
    return {"detail": "已重置所有礼物状态"}
