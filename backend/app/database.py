"""数据库配置 — SQLAlchemy async + aiosqlite"""

import os
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


# 期望的列结构（基于 models.py）— 用于启动时自动修复 MySQL 表 schema
_EXPECTED_SCHEMA = {
    "users": {
        "id": "INT AUTO_INCREMENT PRIMARY KEY",
        "username": "VARCHAR(64) UNIQUE NOT NULL",
        "hashed_password": "VARCHAR(256) NOT NULL",
        "role": "VARCHAR(20) NOT NULL DEFAULT 'student'",
        "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
    },
    "profiles": {
        "id": "INT AUTO_INCREMENT PRIMARY KEY",
        "user_id": "INT NOT NULL",
        "data": "JSON",
        "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
    },
    "resources": {
        "id": "INT AUTO_INCREMENT PRIMARY KEY",
        "user_id": "INT NOT NULL",
        "data": "JSON",
        "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
    },
    "paths": {
        "id": "INT AUTO_INCREMENT PRIMARY KEY",
        "user_id": "INT NOT NULL",
        "data": "JSON",
        "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
    },
    "assess_history": {
        "id": "INT AUTO_INCREMENT PRIMARY KEY",
        "user_id": "INT NOT NULL",
        "score": "INT NOT NULL",
        "modules": "JSON",
        "weak_points": "JSON",
        "time_used": "INT",
        "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
    },
    "profile_history": {
        "id": "INT AUTO_INCREMENT PRIMARY KEY",
        "user_id": "INT NOT NULL",
        "name": "VARCHAR(200)",
        "profile_data": "JSON",
        "is_active": "INT DEFAULT 0",
        "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
    },
}


async def _fix_mysql_schema(conn):
    """★ 启动时自动修复 MySQL 表结构：补齐缺失的列。

    解决问题：从 SQLite 迁移到 MySQL 后，init_db 的 create_all 只创建不存在的表，
    不会修改已有表的列结构。导致旧表的 schema 与 ORM 模型不匹配，
    查询时报 "Unknown column" 错误。

    策略：对每个表用 SHOW COLUMNS 检查，ALTER TABLE 补齐缺失列。
    """
    if not DATABASE_URL.startswith("mysql"):
        return  # 只对 MySQL 生效

    for table_name, columns in _EXPECTED_SCHEMA.items():
        try:
            # 检查表是否存在
            check_r = await conn.execute(text(f"SHOW TABLES LIKE '{table_name}'"))
            if not check_r.fetchone():
                continue  # 表不存在，create_all 会创建

            # 获取现有列
            cols_r = await conn.execute(text(f"SHOW COLUMNS FROM `{table_name}`"))
            existing_cols = [row[0] for row in cols_r.fetchall()]

            # 补齐缺失的列
            for col_name, col_def in columns.items():
                if col_name not in existing_cols:
                    try:
                        await conn.execute(text(f"ALTER TABLE `{table_name}` ADD COLUMN {col_name} {col_def}"))
                        logger.warning("[SCHEMA FIX] %s.%s 列缺失，已自动添加", table_name, col_name)
                    except Exception as e:
                        if "Duplicate column" not in str(e):
                            logger.error("[SCHEMA FIX] %s.%s 添加失败: %s", table_name, col_name, e)
        except Exception as e:
            logger.error("[SCHEMA FIX] 检查表 %s 失败: %s", table_name, e)


async def init_db():
    """初始化数据库：创建表 + 修复 MySQL schema"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # ★ 自动修复 MySQL 表结构（补齐缺失列）
        await _fix_mysql_schema(conn)
