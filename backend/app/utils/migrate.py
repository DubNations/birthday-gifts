"""简单的数据库迁移工具，为已有表自动添加缺失的列和索引"""
from sqlalchemy import inspect, text
from ..database import engine, Base
from ..config import DATABASE_URL


def migrate():
    """检查并添加缺失的列和索引（仅适用于 SQLite）"""
    if 'sqlite' not in DATABASE_URL:
        return

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # 定义需要迁移的列: (表名, 列名, 列定义)
    migrations = [
        ('gifts', 'weight', 'INTEGER NOT NULL DEFAULT 10'),
        ('gifts', 'claimed_by', 'VARCHAR(200)'),
        ('gifts', 'claimed_at', 'DATETIME'),
        ('admin_sessions', None, None),  # 整表新建
    ]

    with engine.connect() as conn:
        for table_name, col_name, col_def in migrations:
            if table_name not in existing_tables:
                # 整表不存在，create_all 会处理
                continue
            if col_name is None:
                continue
            columns = [c['name'] for c in inspector.get_columns(table_name)]
            if col_name not in columns:
                conn.execute(text(
                    f'ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}'
                ))
                conn.commit()
                print(f"迁移: 为 {table_name} 表添加了 {col_name} 列")

    # 创建索引
    index_migrations = [
        'CREATE INDEX IF NOT EXISTS idx_gifts_status ON gifts(status)',
        'CREATE INDEX IF NOT EXISTS idx_gifts_tier_status ON gifts(tier, status)',
        'CREATE INDEX IF NOT EXISTS idx_gifts_claimed_by ON gifts(claimed_by)',
        'CREATE INDEX IF NOT EXISTS idx_gifts_locked_at ON gifts(locked_at)',
        'CREATE INDEX IF NOT EXISTS idx_user_action_fp_action ON user_action_log(fingerprint_id, action)',
    ]

    with engine.connect() as conn:
        for idx_sql in index_migrations:
            try:
                conn.execute(text(idx_sql))
                conn.commit()
            except Exception as e:
                print(f"索引创建警告: {e}")
