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
    draws = {'A': 0, 'B': 0, 'C': 0}
    remaining = budget
    for tier in ['A', 'B', 'C']:
        s = stats.get(tier, {})
        min_p = s.get('min_price', float('inf'))
        avail = s.get('count', 0)
        if min_p > 0 and avail > 0 and remaining >= min_p:
            max_n = int(remaining // min_p)
            n = min(max_n, avail)
            draws[tier] = n
            remaining -= n * min_p
    return draws


def allocate_diverse(budget: float, stats: Dict[str, Dict]) -> Dict[str, int]:
    draws = {'A': 0, 'B': 0, 'C': 0}
    avail = {t: stats.get(t, {}).get('count', 0) for t in ['A', 'B', 'C']}
    min_p = {t: stats.get(t, {}).get('min_price', 0) for t in ['A', 'B', 'C']}

    remaining = budget

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
    run_rounds(['B', 'C'])
    run_rounds(['C'])

    return draws


def estimate_cost(draws: Dict[str, int], stats: Dict[str, Dict]) -> float:
    total = 0.0
    for tier, count in draws.items():
        if count > 0:
            total += count * stats.get(tier, {}).get('min_price', 0)
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

    if sum(premium_draws.values()) > 0:
        plans.append({
            'plan_type': 'premium',
            'description': build_desc(premium_draws, '高级优先'),
            'draws': premium_draws,
            'tier_prices': {t: stats[t]['min_price'] for t in ['A', 'B', 'C']},
            'estimated_cost': estimate_cost(premium_draws, stats),
        })

    if sum(diverse_draws.values()) > 0:
        plans.append({
            'plan_type': 'diverse',
            'description': build_desc(diverse_draws, '均衡多样'),
            'draws': diverse_draws,
            'tier_prices': {t: stats[t]['min_price'] for t in ['A', 'B', 'C']},
            'estimated_cost': estimate_cost(diverse_draws, stats),
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
