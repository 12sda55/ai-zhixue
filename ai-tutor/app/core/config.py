"""全局配置 - 从环境变量加载"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # DeepSeek API
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # 讯飞星火API（对照规范 E1：讯飞星火可切换为主模型）
    xunfei_app_id: str = ""
    xunfei_api_key: str = ""
    xunfei_api_secret: str = ""
    xunfei_api_password: str = ""  # OpenAI兼容HTTP API认证密码（XUNFEI_API_PASSWORD）
    xunfei_spark_url: str = "wss://spark-api.xf-yun.com/v4/chat"
    xunfei_spark_model: str = "4.0Ultra"

    # LLM主模型配置（对照规范 9.1：双模型可切换）
    llm_primary: str = "deepseek"       # 主模型: "spark" | "deepseek"
    llm_secondary: str = "deepseek"     # 备选模型
    llm_fallback_enabled: bool = True   # 主模型不可用时自动切换备选

    # MySQL (替代PostgreSQL)
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_db: str = "ai_tutor"

    # 数据库类型选择（用于开发测试）
    database_type: str = "mysql"  # "mysql" | "sqlite"

    # .env兼容映射
    mysql_database: str = ""
    debug: str = ""

    @property
    def database_url(self) -> str:
        # 如果选择SQLite，使用内存数据库（适合快速测试）
        if self.database_type == "sqlite":
            return "sqlite:///./data/ai_tutor_dev.db"
        
        # 否则使用MySQL
        db = self.mysql_db or self.mysql_database or "ai_tutor"
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{db}"

    @property
    def database_url_async(self) -> str:
        # 如果选择SQLite，使用内存数据库
        if self.database_type == "sqlite":
            return "sqlite+aiosqlite:///./data/ai_tutor_dev.db"
        
        # 否则使用MySQL
        db = self.mysql_db or self.mysql_database or "ai_tutor"
        return f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{db}"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma_db"

    # Judge0
    judge0_url: str = "http://localhost:2358"
    judge0_api_key: str = ""

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = True
    app_secret_key: str = "change_me_in_production"

    # Object Storage
    oss_endpoint: str = ""
    oss_access_key: str = ""
    oss_secret_key: str = ""
    oss_bucket: str = "ai-tutor"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
