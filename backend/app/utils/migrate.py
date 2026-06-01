"""简单的数据库迁移工具，为已有表自动添加缺失的列"""
from sqlalchemy import inspect, text
from ..database import engine, Base
from ..config import DATABASE_URL


def migrate():
    """检查并添加缺失的列（仅适用于 SQLite）"""
    if 'sqlite' not in DATABASE_URL:
        return

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # 定义需要迁移的列: (表名, 列名, 列定义)
    migrations = [
        ('gifts', 'weight', 'INTEGER NOT NULL DEFAULT 10'),
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
