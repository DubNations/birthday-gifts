import os

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./gift.db')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
ADMIN_SESSION_HOURS = int(os.getenv('ADMIN_SESSION_HOURS', '2'))
LOCK_TIMEOUT_MINUTES = 15
MAX_REGRET_CHANCES = 1

# CORS 允许的前端域名，逗号分隔，开发环境默认允许 localhost
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv('CORS_ORIGINS', 'http://localhost:20000,http://localhost:5173').split(',')
    if origin.strip()
]
