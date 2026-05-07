from datetime import datetime


def format_datetime(dt: datetime) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def tier_display(tier: str) -> str:
    mapping = {"A": "高级", "B": "中级", "C": "普通"}
    return mapping.get(tier, tier)
