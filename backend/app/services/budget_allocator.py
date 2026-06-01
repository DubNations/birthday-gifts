from typing import Dict, List
from sqlalchemy.orm import Session
from ..models.gift import Gift


def get_tier_stats(db: Session) -> Dict[str, Dict]:
    gifts = db.query(Gift).filter(Gift.status == 'available').all()
    tiers = {'A': [], 'B': [], 'C': []}
    for g in gifts:
        if g.tier in tiers:
            tiers[g.tier].append(g.price)

    stats = {}
    for tier, prices in tiers.items():
        if prices:
            stats[tier] = {
                'avg_price': round(sum(prices) / len(prices), 2),
                'count': len(prices),
                'min_price': min(prices),
                'max_price': max(prices),
            }
        else:
            stats[tier] = {'avg_price': 0, 'count': 0, 'min_price': 0, 'max_price': 0}
    return stats


def get_qualifications(budget: float, stats: Dict[str, Dict]) -> Dict[str, bool]:
    result = {}
    for tier in ['A', 'B', 'C']:
        s = stats.get(tier, {})
        result[tier] = s.get('count', 0) > 0 and budget >= s.get('min_price', float('inf'))
    return result


def allocate_premium(budget: float, stats: Dict[str, Dict]) -> Dict[str, int]:
    """高级优先：使用均价估算，优先分配高等级礼物，追求质量"""
    draws = {'A': 0, 'B': 0, 'C': 0}
    remaining = budget
    # 使用均价而非最低价，确保预算更真实地反映实际花费
    for tier in ['A', 'B', 'C']:
        s = stats.get(tier, {})
        avg_p = s.get('avg_price', 0)
        avail = s.get('count', 0)
        if avg_p > 0 and avail > 0 and remaining >= avg_p:
            # 高级优先：最多分配可用数量，但不超过预算/均价
            max_n = int(remaining // avg_p)
            n = min(max_n, avail)
            draws[tier] = n
            remaining -= n * avg_p
    return draws


def allocate_diverse(budget: float, stats: Dict[str, Dict]) -> Dict[str, int]:
    """均衡多样：使用最低价估算，最大化抽奖次数，雨露均沾"""
    draws = {'A': 0, 'B': 0, 'C': 0}
    avail = {t: stats.get(t, {}).get('count', 0) for t in ['A', 'B', 'C']}
    min_p = {t: stats.get(t, {}).get('min_price', 0) for t in ['A', 'B', 'C']}

    remaining = budget

    # 第一轮：每个等级各抽一次（如果预算和库存允许）
    def run_rounds(tiers):
        nonlocal remaining
        while True:
            cost = sum(min_p[t] for t in tiers if avail[t] > draws[t])
            if cost == 0 or remaining < cost:
                break
            for t in tiers:
                if avail[t] > draws[t]:
                    draws[t] += 1
                    remaining -= min_p[t]

    run_rounds(['A', 'B', 'C'])
    # 第二轮：只在中低等级中继续分配
    run_rounds(['B', 'C'])
    # 第三轮：只在最低等级中分配剩余预算
    run_rounds(['C'])

    return draws


def estimate_cost(draws: Dict[str, int], stats: Dict[str, Dict], use_avg: bool = False) -> float:
    """估算花费，premium 方案用均价，diverse 方案用最低价"""
    total = 0.0
    for tier, count in draws.items():
        if count > 0:
            price_key = 'avg_price' if use_avg else 'min_price'
            total += count * stats.get(tier, {}).get(price_key, 0)
    return round(total, 2)


def generate_plans(budget: float, db: Session) -> List[dict]:
    stats = get_tier_stats(db)
    qual = get_qualifications(budget, stats)

    plans = []

    tier_names = {'A': '高级', 'B': '中级', 'C': '普通'}

    premium_draws = allocate_premium(budget, stats)
    diverse_draws = allocate_diverse(budget, stats)

    def build_desc(draws, label):
        parts = []
        for t in ['A', 'B', 'C']:
            if draws[t] > 0:
                parts.append(f'{draws[t]}张{t}级')
        total_draws = sum(draws.values())
        return f'{label}: {" + ".join(parts)} (共{total_draws}次抽奖)'

    # premium 方案用均价估算（更贴近实际）
    if sum(premium_draws.values()) > 0:
        plans.append({
            'plan_type': 'premium',
            'description': build_desc(premium_draws, '高级优先'),
            'draws': premium_draws,
            'tier_prices': {t: stats[t]['avg_price'] for t in ['A', 'B', 'C']},
            'estimated_cost': estimate_cost(premium_draws, stats, use_avg=True),
        })

    # diverse 方案用最低价估算（最大化次数）
    if sum(diverse_draws.values()) > 0:
        plans.append({
            'plan_type': 'diverse',
            'description': build_desc(diverse_draws, '均衡多样'),
            'draws': diverse_draws,
            'tier_prices': {t: stats[t]['min_price'] for t in ['A', 'B', 'C']},
            'estimated_cost': estimate_cost(diverse_draws, stats, use_avg=False),
        })

    if not plans:
        available = [(t, s['min_price']) for t, s in stats.items() if s['count'] > 0]
        if available:
            available.sort(key=lambda x: x[1])
            msg = '预算不足，最低需' + str(available[0][1]) + '起(' + available[0][0] + '级)'
        else:
            msg = '暂无可用礼物'
        plans.append({
            'plan_type': 'none',
            'description': msg,
            'draws': {'A': 0, 'B': 0, 'C': 0},
            'tier_prices': {t: stats[t]['min_price'] for t in ['A','B','C']},
            'estimated_cost': 0,
        })

    return plans

