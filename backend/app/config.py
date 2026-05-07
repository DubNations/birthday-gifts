import os


def _parse_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def _parse_cors_origins(value: str | None) -> list[str]:
    if not value:
        return []
    return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gift.db")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_TOKEN_SECRET = os.getenv("ADMIN_TOKEN_SECRET")
CORS_ORIGINS = _parse_cors_origins(os.getenv("CORS_ORIGINS"))
LOCK_TIMEOUT_MINUTES = _parse_int("LOCK_TIMEOUT_MINUTES", 15)
MAX_REGRET_CHANCES = _parse_int("MAX_REGRET_CHANCES", 1)
ADMIN_TOKEN_EXPIRE_MINUTES = _parse_int("ADMIN_TOKEN_EXPIRE_MINUTES", 12 * 60)

if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD must be set; the default admin password has been removed")

if ADMIN_PASSWORD == "admin123":
    raise RuntimeError("ADMIN_PASSWORD must not use the removed insecure default value 'admin123'")

if not ADMIN_TOKEN_SECRET:
    ADMIN_TOKEN_SECRET = ADMIN_PASSWORD
