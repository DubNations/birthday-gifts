import os

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./gift.db')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
ADMIN_SESSION_HOURS = int(os.getenv('ADMIN_SESSION_HOURS', '2'))
LOCK_TIMEOUT_MINUTES = 15
MAX_REGRET_CHANCES = 1
