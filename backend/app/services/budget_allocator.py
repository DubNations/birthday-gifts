from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List

from sqlalchemy.orm import Session

from ..models.gift import Gift

TIERS = ["A", "B", "C"]
MONEY = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)


def get_tier_stats(db: Session, campaign_id: int | None = None) -> Dict[str, Dict]:
    query = db.query(Gift).filter(Gift.status == "available")
    if campaign_id is not None:
        query = query.filter(Gift.campaign_id == campaign_id)
    gifts = query.all()
    tiers = {tier: [] for tier in TIERS}
    for gift in gifts:
        if gift.tier in tiers:
            tiers[gift.tier].append(money(gift.price))

    stats = {}
    for tier, prices in tiers.items():
        if prices:
            total = sum(prices, Decimal("0"))
            stats[tier] = {
                "avg_price": money(total / Decimal(len(prices))),
                "count": len(prices),
                "min_price": min(prices),
                "max_price": max(prices),
            }
        else:
            stats[tier] = {"avg_price": Decimal("0"), "count": 0, "min_price": Decimal("0"), "max_price": Decimal("0")}
    return stats


def _cap(draws: Dict[str, int], stats: Dict[str, Dict]) -> Dict[str, int]:
    return {tier: max(0, min(int(draws.get(tier, 0)), stats.get(tier, {}).get("count", 0))) for tier in TIERS}


def allocate_premium_first(budget: Decimal, stats: Dict[str, Dict]) -> Dict[str, int]:
    draws = {tier: 0 for tier in TIERS}
    remaining = budget
    for tier in TIERS:
        avg = stats[tier]["avg_price"]
        if avg <= 0 or stats[tier]["count"] <= 0:
            continue
        count = min(int(remaining // avg), stats[tier]["count"])
        draws[tier] = count
        remaining -= avg * count
    return draws


def allocate_balanced(budget: Decimal, stats: Dict[str, Dict]) -> Dict[str, int]:
    draws = {tier: 0 for tier in TIERS}
    remaining = budget
    weights = {"A": 1, "B": 2, "C": 2}
    while True:
        added = False
        for tier in TIERS:
            avg = stats[tier]["avg_price"]
            for _ in range(weights[tier]):
                if avg > 0 and stats[tier]["count"] > draws[tier] and remaining >= avg:
                    draws[tier] += 1
                    remaining -= avg
                    added = True
        if not added:
            break
    return draws


def allocate_quantity_first(budget: Decimal, stats: Dict[str, Dict]) -> Dict[str, int]:
    draws = {tier: 0 for tier in TIERS}
    remaining = budget
    for tier in reversed(TIERS):
        avg = stats[tier]["avg_price"]
        if avg <= 0:
            continue
        count = min(int(remaining // avg), stats[tier]["count"])
        draws[tier] = count
        remaining -= avg * count
    return draws


def allocate_surprise(budget: Decimal, stats: Dict[str, Dict]) -> Dict[str, int]:
    # 先保留一次 A/B 惊喜机会，再用 C 级填充，兼顾未知感与数量。
    draws = {tier: 0 for tier in TIERS}
    remaining = budget
    for tier in ("A", "B"):
        avg = stats[tier]["avg_price"]
        if avg > 0 and stats[tier]["count"] > 0 and remaining >= avg:
            draws[tier] += 1
            remaining -= avg
    c_avg = stats["C"]["avg_price"]
    if c_avg > 0:
        count = min(int(remaining // c_avg), stats["C"]["count"])
        draws["C"] += count
    return draws


def allocate_safe(budget: Decimal, stats: Dict[str, Dict]) -> Dict[str, int]:
    # 使用各 tier 最高价估算，尽量让实际成本落在预算内。
    draws = {tier: 0 for tier in TIERS}
    remaining = budget
    for tier in ("B", "C", "A"):
        max_price = stats[tier]["max_price"]
        if max_price <= 0:
            continue
        count = min(int(remaining // max_price), stats[tier]["count"])
        draws[tier] = count
        remaining -= max_price * count
    return draws


def calculate_costs(draws: Dict[str, int], stats: Dict[str, Dict]) -> tuple[Decimal, Decimal, Decimal]:
    estimated = Decimal("0")
    minimum = Decimal("0")
    maximum = Decimal("0")
    for tier, count in draws.items():
        tier_stats = stats.get(tier, {})
        estimated += money(tier_stats.get("avg_price")) * count
        minimum += money(tier_stats.get("min_price")) * count
        maximum += money(tier_stats.get("max_price")) * count
    return money(estimated), money(minimum), money(maximum)


def _draw_summary(draws: Dict[str, int]) -> str:
    parts = [f"{count}次{tier}级" for tier, count in draws.items() if count > 0]
    return "+".join(parts) if parts else "无可用抽奖次数"


def build_plan(plan_type: str, label: str, draws: Dict[str, int], budget: Decimal, stats: Dict[str, Dict], explanation: str) -> dict | None:
    draws = _cap(draws, stats)
    if sum(draws.values()) <= 0:
        return None
    estimated, minimum, maximum = calculate_costs(draws, stats)
    return {
        "plan_type": plan_type,
        "description": f"{label}: {_draw_summary(draws)}",
        "draws": draws,
        "estimated_cost": estimated,
        "min_possible_cost": minimum,
        "max_possible_cost": maximum,
        "remaining_budget_estimate": money(budget - estimated),
        "explanation": explanation,
    }


def generate_plans(budget: Decimal, db: Session, campaign_id: int | None = None) -> List[dict]:
    budget = money(budget)
    stats = get_tier_stats(db, campaign_id)
    candidates = [
        ("premium", "高级优先型", allocate_premium_first, "优先分配 A/B 等高等级礼物；预计花费按当前库存均价测算，最终实际花费取决于抽中的具体礼物。"),
        ("balanced", "均衡型", allocate_balanced, "在高等级与抽取次数之间保持平衡；预计花费不是最终账单，请参考最低/最高可能成本区间。"),
        ("quantity", "数量优先型", allocate_quantity_first, "优先增加可抽次数，通常会更多使用 C/B 级礼物；实际花费会随抽中礼物价格波动。"),
        ("surprise", "惊喜型", allocate_surprise, "保留高等级惊喜机会后补充轻量礼物；预算解释展示的是估算范围而非承诺消费。"),
        ("safe", "稳妥型", allocate_safe, "按各等级最高价进行保守规划，更适合希望实际花费尽量不超预算的场景。"),
    ]

    plans = []
    seen = set()
    for plan_type, label, allocator, explanation in candidates:
        plan = build_plan(plan_type, label, allocator(budget, stats), budget, stats, explanation)
        if not plan:
            continue
        key = tuple(plan["draws"][tier] for tier in TIERS)
        if key in seen:
            plan["description"] = f"{label}: {_draw_summary(plan['draws'])}"
        seen.add(key)
        plans.append(plan)

    if not plans:
        min_prices = [(tier, stats[tier]["min_price"]) for tier in TIERS if stats[tier]["count"] > 0]
        suggestion = f"预算不足，最低需要 {min(min_prices, key=lambda item: item[1])[1]} 元起" if min_prices else "暂无可用礼物"
        plans.append({
            "plan_type": "none",
            "description": suggestion,
            "draws": {tier: 0 for tier in TIERS},
            "estimated_cost": Decimal("0"),
            "min_possible_cost": Decimal("0"),
            "max_possible_cost": Decimal("0"),
            "remaining_budget_estimate": budget,
            "explanation": "当前活动没有可用礼物或预算不足，无法生成有效方案。",
        })

    return plans
