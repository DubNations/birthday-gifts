import csv
import io
import time
import secrets
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.gift import Gift
from ..models.user_action import UserAction
from ..schemas.gift import GiftCreate, GiftUpdate, GiftResponse, GiftStatusUpdate
from ..config import ADMIN_PASSWORD, ADMIN_SESSION_HOURS
from ..services.gift_state import release_expired_locks

router = APIRouter(prefix='/api/admin', tags=['admin'])

_admin_sessions = {}

def _clean_sessions():
    now = time.time()
    expired = [k for k, v in _admin_sessions.items() if v['expires'] < now]
    for k in expired:
        del _admin_sessions[k]

def verify_admin(
    password: str = Query(default=''),
    authorization: str = Header(default=''),
):
    _clean_sessions()
    if authorization.startswith('Bearer '):
        token = authorization[7:]
        session = _admin_sessions.get(token)
        if session and session['expires'] > time.time():
            return True
    if password and password == ADMIN_PASSWORD:
        return True
    raise HTTPException(status_code=403, detail='未授权访问')


@router.post('/login')
def admin_login(password: str):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail='密码错误')
    _clean_sessions()
    token = secrets.token_hex(32)
    _admin_sessions[token] = {
        'created': time.time(),
        'expires': time.time() + ADMIN_SESSION_HOURS * 3600,
    }
    return {
        'token': token,
        'expires_in': ADMIN_SESSION_HOURS * 3600,
        'message': f'登录成功，有效期{ADMIN_SESSION_HOURS}小时',
    }


@router.get('/gifts', response_model=List[GiftResponse])
def list_gifts(db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    release_expired_locks(db)
    return db.query(Gift).order_by(Gift.tier, Gift.price).all()


@router.post('/gifts', response_model=GiftResponse)
def create_gift(gift: GiftCreate, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    if gift.tier not in ('A', 'B', 'C'):
        raise HTTPException(status_code=400, detail='等级必须是 A、B 或 C')
    db_gift = Gift(**gift.model_dump())
    db.add(db_gift)
    db.commit()
    db.refresh(db_gift)
    return db_gift


@router.put('/gifts/{gift_id}', response_model=GiftResponse)
def update_gift(gift_id: int, gift: GiftUpdate, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    db_gift = db.query(Gift).filter(Gift.id == gift_id).first()
    if not db_gift:
        raise HTTPException(status_code=404, detail='礼物不存在')
    update_data = gift.model_dump(exclude_unset=True)
    if 'tier' in update_data and update_data['tier'] not in ('A', 'B', 'C'):
        raise HTTPException(status_code=400, detail='等级必须是 A、B 或 C')
    for key, value in update_data.items():
        setattr(db_gift, key, value)
    db.commit()
    db.refresh(db_gift)
    return db_gift


@router.delete('/gifts/{gift_id}')
def delete_gift(gift_id: int, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    db_gift = db.query(Gift).filter(Gift.id == gift_id).first()
    if not db_gift:
        raise HTTPException(status_code=404, detail='礼物不存在')
    if db_gift.status == 'locked':
        raise HTTPException(status_code=400, detail='礼物正在被锁定，无法删除')
    db.delete(db_gift)
    db.commit()
    return {'detail': '已删除'}


@router.put('/gifts/{gift_id}/status', response_model=GiftResponse)
def update_gift_status(gift_id: int, body: GiftStatusUpdate,
                       db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    if body.status not in ('available', 'locked', 'claimed'):
        raise HTTPException(status_code=400, detail='状态必须是 available、locked 或 claimed')
    db_gift = db.query(Gift).filter(Gift.id == gift_id).first()
    if not db_gift:
        raise HTTPException(status_code=404, detail='礼物不存在')
    db_gift.status = body.status
    if body.status == 'available':
        db_gift.locked_by = None
        db_gift.locked_at = None
    elif body.status == 'claimed':
        db_gift.locked_by = None
        db_gift.locked_at = None
    db.commit()
    db.refresh(db_gift)
    return db_gift


@router.get('/stats')
def get_stats(db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    release_expired_locks(db)
    total = db.query(Gift).count()
    available = db.query(Gift).filter(Gift.status == 'available').count()
    locked = db.query(Gift).filter(Gift.status == 'locked').count()
    claimed = db.query(Gift).filter(Gift.status == 'claimed').count()

    tier_stats = {}
    for tier in ['A', 'B', 'C']:
        avail = [g for g in db.query(Gift).filter(Gift.tier == tier, Gift.status == 'available').all()]
        all_tier = [g for g in db.query(Gift).filter(Gift.tier == tier).all()]
        tier_stats[tier] = {
            'total': len(all_tier),
            'available': len(avail),
            'locked': len([g for g in all_tier if g.status == 'locked']),
            'claimed': len([g for g in all_tier if g.status == 'claimed']),
            'avg_price': round(sum(g.price for g in avail) / len(avail), 2) if avail else 0,
            'min_price': min(g.price for g in avail) if avail else 0,
            'max_price': max(g.price for g in avail) if avail else 0,
        }

    return {
        'total': total,
        'available': available,
        'locked': locked,
        'claimed': claimed,
        'tiers': tier_stats,
    }


@router.post('/export')
def export_gifts(db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    gifts = db.query(Gift).filter(Gift.status == 'claimed').all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', '名称', '链接', '价格', '等级', '状态'])
    for g in gifts:
        writer.writerow([g.id, g.name, g.url or '', g.price, g.tier, g.status])
    return {'csv': output.getvalue(), 'count': len(gifts)}


@router.post('/reset')
def reset_gifts(db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    db.query(Gift).filter(Gift.status != 'claimed').update(
        {'status': 'available', 'locked_by': None, 'locked_at': None}
    )
    db.query(UserAction).delete()
    db.commit()
    return {'detail': '已重置所有礼物状态'}
