import csv
import io
import time
import secrets
from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, or_
from ..database import get_db
from ..models.gift import Gift
from ..models.user_action import UserAction
from ..models.draw_session import DrawSession
from ..models.admin_session import AdminSession
from ..models.system_config import SystemConfig, get_config_value, set_config_value, get_max_regret
from ..schemas.gift import GiftCreate, GiftUpdate, GiftResponse, GiftStatusUpdate
from ..config import ADMIN_PASSWORD, ADMIN_SESSION_HOURS
from ..services.gift_state import release_expired_locks

router = APIRouter(prefix='/api/admin', tags=['admin'])


def _clean_expired_sessions(db: Session):
    now = time.time()
    db.query(AdminSession).filter(AdminSession.expires_at < now).delete()
    db.commit()


def verify_admin(
    authorization: str = Header(default=''),
    db: Session = Depends(get_db),
):
    if authorization.startswith('Bearer '):
        token = authorization[7:]
        session = db.query(AdminSession).filter(
            AdminSession.token == token,
            AdminSession.expires_at > time.time(),
        ).first()
        if session:
            return True
    raise HTTPException(status_code=403, detail='未授权访问')


class LoginRequest(BaseModel):
    password: str


class ConfigUpdateRequest(BaseModel):
    max_regret_chances: Optional[int] = None


@router.post('/login')
def admin_login(body: LoginRequest, db: Session = Depends(get_db)):
    if body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail='密码错误')
    _clean_expired_sessions(db)
    token = secrets.token_hex(32)
    session = AdminSession(
        token=token,
        expires_at=time.time() + ADMIN_SESSION_HOURS * 3600,
    )
    db.add(session)
    db.commit()
    return {
        'token': token,
        'expires_in': ADMIN_SESSION_HOURS * 3600,
        'message': f'登录成功，有效期{ADMIN_SESSION_HOURS}小时',
    }


# ============ 礼物管理 (增强搜索/筛选) ============

@router.get('/gifts')
def list_gifts(
    db: Session = Depends(get_db),
    auth: bool = Depends(verify_admin),
    search: Optional[str] = Query(None, description="搜索名称或手机号"),
    status: Optional[str] = Query(None, description="筛选状态"),
    tier: Optional[str] = Query(None, description="筛选等级"),
):
    release_expired_locks(db)
    q = db.query(Gift)
    if search:
        q = q.filter(or_(
            Gift.name.contains(search),
            Gift.claimed_by.contains(search),
            Gift.locked_by.contains(search),
        ))
    if status:
        q = q.filter(Gift.status == status)
    if tier:
        q = q.filter(Gift.tier == tier)
    return q.order_by(Gift.tier, Gift.price).all()


@router.post('/gifts', response_model=GiftResponse)
def create_gift(gift: GiftCreate, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    if gift.tier not in ('A', 'B', 'C'):
        raise HTTPException(status_code=400, detail='等级必须是 A、B 或 C')
    if gift.weight < 1 or gift.weight > 100:
        raise HTTPException(status_code=400, detail='权重必须在 1-100 之间')
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
    if 'weight' in update_data and (update_data['weight'] < 1 or update_data['weight'] > 100):
        raise HTTPException(status_code=400, detail='权重必须在 1-100 之间')
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
    if db_gift.status in ('locked', 'claimed'):
        raise HTTPException(status_code=400, detail=f'礼物状态为{db_gift.status}，无法删除')
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
        db_gift.claimed_by = None
        db_gift.claimed_at = None
    elif body.status == 'claimed':
        db_gift.locked_by = None
        db_gift.locked_at = None
    db.commit()
    db.refresh(db_gift)
    return db_gift


@router.post('/gifts/{gift_id}/unlock')
def unlock_gift(gift_id: int, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    """强制解锁单个礼物"""
    db_gift = db.query(Gift).filter(Gift.id == gift_id).first()
    if not db_gift:
        raise HTTPException(status_code=404, detail='礼物不存在')
    if db_gift.status != 'locked':
        raise HTTPException(status_code=400, detail='该礼物当前未被锁定')
    db_gift.status = 'available'
    db_gift.locked_by = None
    db_gift.locked_at = None
    db.commit()
    return {'detail': '已解锁', 'gift_id': gift_id}


# ============ 统计 (增强用户统计) ============

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

    # 用户统计
    total_users = db.query(distinct(DrawSession.fingerprint_id)).count()
    today = date.today()
    today_users = db.query(distinct(DrawSession.fingerprint_id)).filter(
        func.date(DrawSession.created_at) == today.isoformat()
    ).count()

    return {
        'total': total,
        'available': available,
        'locked': locked,
        'claimed': claimed,
        'tiers': tier_stats,
        'total_users': total_users,
        'today_users': today_users,
    }


# ============ 导出 (增强) ============

@router.post('/export')
def export_gifts(db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    gifts = db.query(Gift).filter(Gift.status == 'claimed').all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', '名称', '链接', '价格', '等级', '状态', '领取者', '领取时间'])
    for g in gifts:
        writer.writerow([
            g.id, g.name, g.url or '', g.price, g.tier, g.status,
            g.claimed_by or '', g.claimed_at.isoformat() if g.claimed_at else '',
        ])
    return {'csv': output.getvalue(), 'count': len(gifts)}


# ============ 全局重置 ============

@router.post('/reset')
def reset_gifts(db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    db.query(Gift).filter(Gift.status != 'claimed').update(
        {'status': 'available', 'locked_by': None, 'locked_at': None}
    )
    db.query(UserAction).delete()
    db.commit()
    return {'detail': '已重置所有礼物状态'}


# ============ 用户管理 ============

@router.get('/users')
def list_users(
    db: Session = Depends(get_db),
    auth: bool = Depends(verify_admin),
    search: Optional[str] = Query(None, description="手机号模糊搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取所有用户列表及统计"""
    # 获取所有有活动记录的唯一手机号
    user_query = db.query(
        DrawSession.fingerprint_id,
        func.count(distinct(DrawSession.id)).label('session_count'),
        func.max(DrawSession.created_at).label('last_active'),
    ).group_by(DrawSession.fingerprint_id)

    if search:
        user_query = user_query.filter(DrawSession.fingerprint_id.contains(search))

    total = user_query.count()
    users_raw = user_query.offset((page - 1) * page_size).limit(page_size).all()

    users = []
    for row in users_raw:
        phone = row.fingerprint_id
        claimed_count = db.query(UserAction).filter(
            UserAction.fingerprint_id == phone,
            UserAction.action == 'claim',
        ).count()
        regret_count = db.query(UserAction).filter(
            UserAction.fingerprint_id == phone,
            UserAction.regret_used == True,
        ).count()
        claimed_value = db.query(func.coalesce(func.sum(Gift.price), 0)).filter(
            Gift.claimed_by == phone, Gift.status == 'claimed'
        ).scalar()
        users.append({
            'phone': phone,
            'session_count': row.session_count,
            'claimed_count': claimed_count,
            'regret_count': regret_count,
            'claimed_value': round(float(claimed_value), 2),
            'last_active': row.last_active.isoformat() if row.last_active else None,
        })

    return {'users': users, 'total': total, 'page': page, 'page_size': page_size}


@router.get('/users/{phone}')
def get_user_detail(phone: str, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    """获取单用户详情"""
    sessions = db.query(DrawSession).filter(
        DrawSession.fingerprint_id == phone
    ).order_by(DrawSession.created_at.desc()).all()

    actions = db.query(UserAction).filter(
        UserAction.fingerprint_id == phone
    ).order_by(UserAction.created_at.desc()).all()

    claimed_gifts = db.query(Gift).filter(
        Gift.claimed_by == phone, Gift.status == 'claimed'
    ).all()

    return {
        'phone': phone,
        'sessions': [
            {
                'id': s.id, 'budget': s.budget, 'plan_type': s.plan_type,
                'status': s.status, 'remaining_budget': s.remaining_budget,
                'created_at': s.created_at.isoformat() if s.created_at else None,
            }
            for s in sessions
        ],
        'actions': [
            {
                'id': a.id, 'gift_id': a.gift_id, 'action': a.action,
                'regret_used': a.regret_used,
                'created_at': a.created_at.isoformat() if a.created_at else None,
            }
            for a in actions
        ],
        'claimed_gifts': [
            {
                'id': g.id, 'name': g.name, 'tier': g.tier,
                'price': g.price, 'url': g.url,
                'claimed_at': g.claimed_at.isoformat() if g.claimed_at else None,
            }
            for g in claimed_gifts
        ],
    }


@router.post('/users/{phone}/reset')
def reset_user(phone: str, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    """重置单个用户的所有状态"""
    # 释放该用户锁定的礼物
    locked_gifts = db.query(Gift).filter(
        Gift.locked_by == phone, Gift.status == 'locked'
    ).all()
    for g in locked_gifts:
        g.status = 'available'
        g.locked_by = None
        g.locked_at = None

    # 删除该用户的操作记录
    db.query(UserAction).filter(UserAction.fingerprint_id == phone).delete()

    # 将该用户的会话标记为 reset
    db.query(DrawSession).filter(
        DrawSession.fingerprint_id == phone,
        DrawSession.status == 'active',
    ).update({'status': 'reset'})

    db.commit()
    return {
        'detail': '已重置用户状态',
        'phone': phone,
        'released_gifts': len(locked_gifts),
    }


# ============ 系统配置 ============

@router.get('/config')
def get_config(db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    """获取系统配置"""
    max_regret = get_max_regret(db)
    return {
        'max_regret_chances': max_regret,
    }


@router.put('/config')
def update_config(body: ConfigUpdateRequest, db: Session = Depends(get_db), auth: bool = Depends(verify_admin)):
    """更新系统配置"""
    if body.max_regret_chances is not None:
        if body.max_regret_chances < 0:
            raise HTTPException(status_code=400, detail='反悔次数不能为负数')
        set_config_value(db, 'max_regret_chances', str(body.max_regret_chances))
    return {'detail': '配置已更新'}


# ============ 活动日志 ============

@router.get('/activity-log')
def get_activity_log(
    db: Session = Depends(get_db),
    auth: bool = Depends(verify_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    phone: Optional[str] = Query(None, description="按手机号筛选"),
    action: Optional[str] = Query(None, description="按操作类型筛选"),
):
    """获取活动日志"""
    q = db.query(UserAction)
    if phone:
        q = q.filter(UserAction.fingerprint_id.contains(phone))
    if action:
        q = q.filter(UserAction.action == action)

    total = q.count()
    logs = q.order_by(UserAction.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = []
    gift_ids = [log.gift_id for log in logs if log.gift_id]
    gifts_map = {}
    if gift_ids:
        gifts_map = {g.id: g.name for g in db.query(Gift).filter(Gift.id.in_(gift_ids)).all()}
    for log in logs:
        gift_name = None
        if log.gift_id:
            gift_name = gifts_map.get(log.gift_id, f'礼物#{log.gift_id}')
        items.append({
            'id': log.id,
            'phone': log.fingerprint_id,
            'gift_id': log.gift_id,
            'gift_name': gift_name,
            'action': log.action,
            'regret_used': log.regret_used,
            'created_at': log.created_at.isoformat() if log.created_at else None,
        })

    return {'items': items, 'total': total, 'page': page, 'page_size': page_size}
