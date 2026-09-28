"""FastAPI 主应用"""

import os
import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .database import init_db, async_session
from .routers import auth_router, glm_router, data_router, admin_router, community_router

load_dotenv()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        logger.info("[STARTUP] init_db 完成")
    except Exception as e:
        logger.error("[STARTUP] init_db 失败: %s\n%s", str(e), traceback.format_exc())
        raise
    yield


app = FastAPI(title="AI Learning System API", version="1.0.0", lifespan=lifespan)

# CORS 允许的来源：支持环境变量配置多个（逗号分隔）
_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]
_env_origins = os.getenv("CORS_ORIGIN", "")
if _env_origins:
    _default_origins.extend([o.strip() for o in _env_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(glm_router.router, prefix="/api/v1/glm", tags=["glm"])
app.include_router(data_router.router, prefix="/api/v1/data", tags=["data"])
app.include_router(admin_router.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(community_router.router, prefix="/api/v1/community", tags=["community"])


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/debug/db")
async def debug_db():
    """诊断端点：测试数据库连接和所有表是否可查询（无需认证）"""
    from sqlalchemy import text
    result = {"database_url": os.getenv("DATABASE_URL", "default"), "tables": {}, "errors": []}
    try:
        async with async_session() as session:
            # 测试每个表的查询
            tables_to_test = ["users", "profiles", "resources", "paths", "assess_history", "profile_history"]
            for table_name in tables_to_test:
                try:
                    r = await session.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
                    count = r.scalar()
                    # 同时检查表结构
                    cols_r = await session.execute(text(f"SHOW COLUMNS FROM `{table_name}`"))
                    cols = [row[0] for row in cols_r.fetchall()]
                    result["tables"][table_name] = {"exists": True, "count": count, "columns": cols}
                except Exception as e:
                    result["tables"][table_name] = {"exists": False, "error": str(e)}
                    result["errors"].append(f"{table_name}: {str(e)}")
    except Exception as e:
        result["errors"].append(f"DB connection failed: {str(e)}")
    return result


@app.post("/api/v1/debug/fix-schema")
async def fix_schema():
    """修复端点：重建表结构以匹配 ORM 模型。

    策略：对每个表用 ALTER TABLE 补齐缺失列。如果表不存在则创建。
    已有数据会保留，只添加缺失的列。
    """
    from sqlalchemy import text
    from .database import engine
    from .models import Base

    result = {"fixed": [], "errors": [], "recreated": []}

    # 期望的列结构（基于 models.py）
    expected_schema = {
        "users": [
            "id INT AUTO_INCREMENT PRIMARY KEY",
            "username VARCHAR(64) UNIQUE NOT NULL",
            "hashed_password VARCHAR(256) NOT NULL",
            "role VARCHAR(20) NOT NULL DEFAULT 'student'",
            "created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        ],
        "profiles": [
            "id INT AUTO_INCREMENT PRIMARY KEY",
            "user_id INT NOT NULL",
            "data JSON",
            "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        ],
        "resources": [
            "id INT AUTO_INCREMENT PRIMARY KEY",
            "user_id INT NOT NULL",
            "data JSON",
            "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        ],
        "paths": [
            "id INT AUTO_INCREMENT PRIMARY KEY",
            "user_id INT NOT NULL",
            "data JSON",
            "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        ],
        "assess_history": [
            "id INT AUTO_INCREMENT PRIMARY KEY",
            "user_id INT NOT NULL",
            "score INT NOT NULL",
            "modules JSON",
            "weak_points JSON",
            "time_used INT",
            "created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        ],
        "profile_history": [
            "id INT AUTO_INCREMENT PRIMARY KEY",
            "user_id INT NOT NULL",
            "name VARCHAR(200)",
            "profile_data JSON",
            "is_active INT DEFAULT 0",
            "created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
            "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        ],
    }

    try:
        async with engine.begin() as conn:
            # 先用 create_all 创建缺失的表（不会修改已存在的表）
            await conn.run_sync(Base.metadata.create_all)

            # 对每个已存在的表，检查并补齐缺失的列
            for table_name, columns_def in expected_schema.items():
                try:
                    # 检查表是否存在
                    check_r = await conn.execute(text(f"SHOW TABLES LIKE '{table_name}'"))
                    if not check_r.fetchone():
                        result["errors"].append(f"{table_name}: 表不存在")
                        continue

                    # 获取现有列
                    cols_r = await conn.execute(text(f"SHOW COLUMNS FROM `{table_name}`"))
                    existing_cols = [row[0] for row in cols_r.fetchall()]

                    # 补齐缺失的列
                    for col_def in columns_def:
                        col_name = col_def.split()[0]
                        if col_name not in existing_cols:
                            try:
                                await conn.execute(text(f"ALTER TABLE `{table_name}` ADD COLUMN {col_def}"))
                                result["fixed"].append(f"{table_name}.{col_name}")
                            except Exception as e:
                                err_msg = str(e)
                                if "Duplicate column" in err_msg:
                                    pass  # 列已存在，忽略
                                else:
                                    result["errors"].append(f"{table_name}.{col_name}: {err_msg}")

                except Exception as e:
                    result["errors"].append(f"{table_name}: {str(e)}")

        result["message"] = "Schema fix completed"
    except Exception as e:
        result["errors"].append(f"Fix failed: {str(e)}")

    return result


@app.post("/api/v1/debug/rebuild-tables")
async def rebuild_tables():
    """⚠️ 危险端点：DROP 并重建所有数据表（会丢失所有数据）。

    仅在 fix-schema 无效时使用。
    需要通过 query 参数 ?confirm=yes 确认。
    """
    from fastapi import Request
    from sqlalchemy import text
    from .database import engine
    from .models import Base

    result = {"action": "rebuild", "dropped": [], "errors": []}

    try:
        async with engine.begin() as conn:
            # 关闭外键检查
            await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

            tables_to_drop = ["profile_history", "assess_history", "paths", "resources", "profiles", "users"]
            for table_name in tables_to_drop:
                try:
                    await conn.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
                    result["dropped"].append(table_name)
                except Exception as e:
                    result["errors"].append(f"{table_name}: {str(e)}")

            # 重新开启外键检查
            await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

            # 重新创建所有表
            await conn.run_sync(Base.metadata.create_all)

        result["message"] = "All tables rebuilt. Please re-register users."
    except Exception as e:
        result["errors"].append(f"Rebuild failed: {str(e)}")

    return result
