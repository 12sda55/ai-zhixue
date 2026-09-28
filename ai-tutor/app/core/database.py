"""数据库基础配置 - SQLAlchemy + MySQL/SQLite"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# 根据数据库类型选择引擎
engine_params = {
    "echo": settings.app_debug,
}

# SQLite和MySQL的特殊配置
if settings.database_type == "mysql":
    engine_params["pool_pre_ping"] = True
    engine_params["pool_recycle"] = 3600
elif settings.database_type == "sqlite":
    engine_params["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **engine_params)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI依赖注入：获取数据库session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建所有表）"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(f"✓ 数据库初始化成功（类型: {settings.database_type})")
    except Exception as e:
        logger.error(f"× 数据库初始化失败: {e}")
        logger.error(f"当前数据库URL: {settings.database_url}")
        
        if settings.database_type == "mysql":
            logger.error("\nMySQL连接失败，建议：")
            logger.error("  1. 检查MySQL服务是否运行")
            logger.error("  2. 在.env文件中设置DATABASE_TYPE=sqlite切换到SQLite")
            logger.error("  3. 或在.env文件中设置正确的MYSQL_PASSWORD")
        
        raise e
