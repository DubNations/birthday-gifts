import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gift.db")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
LOCK_TIMEOUT_MINUTES = 15
MAX_REGRET_CHANCES = 1
