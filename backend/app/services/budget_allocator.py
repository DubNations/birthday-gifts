import math
from typing import Dict, List
from sqlalchemy.orm import Session
from ..models.gift import Gift


TIERS = ["A", "B", "C"]


def get_tier_stats(db: Session) -> Dict[str, Dict]:
    gifts = db.query(Gift).filter(Gift.status == "available").all()
    tiers = {tier: [] for tier in TIERS}
    for g in gifts:
        if g.tier in tiers:
            tiers[g.tier].append(g.price)

    stats = {}
    for tier, prices in tiers.items():
        if prices:
            stats[tier] = {
                "avg_price": sum(prices) / len(prices),
                "count": len(prices),
                "min_price": min(prices),
                "max_price": max(prices),
            }
        else:
            stats[tier] = {"avg_price": 0, "count": 0, "min_price": 0, "max_price": 0}
    return stats


def allocate_premium_first(budget: float, stats: Dict[str, Dict]) -> Dict[str, int]:
    draws = {tier: 0 for tier in TIERS}
    remaining = budget

    for tier in TIERS:
        s = stats.get(tier, {"avg_price": 0, "count": 0})
        if s["avg_price"] <= 0 or s["count"] <= 0:
            continue
        n = min(math.floor(remaining / s["avg_price"]), s["count"])
        draws[tier] = n
        remaining -= n * s["avg_price"]

    if sum(draws.values()) == 0:
        for tier in TIERS:
            s = stats.get(tier, {"avg_price": 0, "count": 0})
            if s["min_price"] > 0 and budget >= s["min_price"] and s["count"] > 0:
                draws[tier] = 1
                break

    return draws


def allocate_diverse(budget: float, stats: Dict[str, Dict]) -> Dict[str, int]:
    draws = {tier: 0 for tier in TIERS}
    remaining = budget

    available_tiers = []
    for tier in TIERS:
        s = stats.get(tier, {"avg_price": 0, "count": 0})
        if s["avg_price"] > 0 and s["count"] > 0:
            available_tiers.append(tier)

    for tier in available_tiers:
        s = stats[tier]
        if remaining >= s["avg_price"] and draws[tier] < s["count"]:
            draws[tier] = 1
            remaining -= s["avg_price"]

    for tier in available_tiers:
        s = stats[tier]
        if s["avg_price"] <= 0:
            continue
        n = min(math.floor(remaining / s["avg_price"]), s["count"] - draws[tier])
        if n > 0:
            draws[tier] += n
            remaining -= n * s["avg_price"]

    return draws


def apply_fallback(draws: Dict[str, int], stats: Dict[str, Dict]) -> Dict[str, int]:
    result = dict(draws)
    for tier in TIERS:
        s = stats.get(tier, {"count": 0})
        if result[tier] > s["count"]:
            overflow = result[tier] - s["count"]
            result[tier] = s["count"]
            lower_tiers = [t for t in TIERS if t > tier]
            for lt in lower_tiers:
                ls = stats.get(lt, {"count": 0, "avg_price": 0})
                if ls["count"] > result[lt] and ls["avg_price"] > 0:
                    bonus = min(overflow, ls["count"] - result[lt])
                    result[lt] += bonus
                    overflow -= bonus
                    if overflow <= 0:
                        break
    return result


def calculate_estimated_cost(draws: Dict[str, int], stats: Dict[str, Dict]) -> float:
    total = 0.0
    for tier, count in draws.items():
        s = stats.get(tier, {"avg_price": 0})
        total += count * s["avg_price"]
    return round(total, 2)


def generate_plans(budget: float, db: Session) -> List[dict]:
    stats = get_tier_stats(db)
    plans = []

    premium_draws = allocate_premium_first(budget, stats)
    premium_draws = apply_fallback(premium_draws, stats)
    if sum(premium_draws.values()) > 0:
        cost = calculate_estimated_cost(premium_draws, stats)
        desc_parts = [f"{v}次{t}级" for t, v in premium_draws.items() if v > 0]
        plans.append({
            "plan_type": "premium",
            "description": "高级优先型: " + "+".join(desc_parts),
            "draws": premium_draws,
            "estimated_cost": cost,
        })

    diverse_draws = allocate_diverse(budget, stats)
    diverse_draws = apply_fallback(diverse_draws, stats)
    if sum(diverse_draws.values()) > 0:
        cost = calculate_estimated_cost(diverse_draws, stats)
        desc_parts = [f"{v}次{t}级" for t, v in diverse_draws.items() if v > 0]
        plans.append({
            "plan_type": "diverse",
            "description": "多样化型: " + "+".join(desc_parts),
            "draws": diverse_draws,
            "estimated_cost": cost,
        })

    if not plans:
        min_prices = []
        for tier in TIERS:
            s = stats.get(tier, {"min_price": 0, "count": 0})
            if s["count"] > 0:
                min_prices.append((tier, s["min_price"]))
        if min_prices:
            min_prices.sort(key=lambda x: x[1])
            suggestion = f"预算不足，最低需要 {min_prices[0][1]} 元起（{min_prices[0][0]}级礼物）"
        else:
            suggestion = "暂无可用礼物"
        plans.append({
            "plan_type": "none",
            "description": suggestion,
            "draws": {tier: 0 for tier in TIERS},
            "estimated_cost": 0,
        })

    return plans
