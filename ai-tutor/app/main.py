"""FastAPI应用入口"""

import os
from contextlib import asynccontextmanager

# 在所有import之前加载.env到os.environ
from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from app.core.config import get_settings
from app.core.database import init_db
from app.core.scheduler import scheduler_service
from app.api import chat, profile, path, question, code, multimodal, document, social, events, tutor, video, resources, reading, assessment, voice, generate, audit

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：初始化数据库 + 知识库 + 启动定时任务
    init_db()

    # 初始化ChromaDB知识库
    from app.services.knowledge_service import knowledge_service
    knowledge_service.initialize()

    # 经典题库同步到MySQL（幂等）
    from app.core.database import SessionLocal
    from app.services.question_service import question_service
    db = SessionLocal()
    try:
        question_service.ensure_classic_in_db(db)
    finally:
        db.close()

    # 预制代码模板同步到MySQL（幂等）
    from app.core.database import SessionLocal as _SL2
    from app.knowledge.code_templates import ensure_templates_in_db
    db2 = _SL2()
    try:
        ensure_templates_in_db(db2)
    finally:
        db2.close()

    # 知识数据种子迁移到MySQL（幂等）
    from app.core.migrations.seed_knowledge import seed_knowledge_data
    db3 = SessionLocal()
    try:
        seed_knowledge_data(db3)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"seed_knowledge_data skipped: {e}")
    finally:
        db3.close()

    # 知识缓存加载到Redis
    from app.core.knowledge_cache import knowledge_cache
    db4 = SessionLocal()
    try:
        knowledge_cache.load_all(db4)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"knowledge_cache.load_all skipped: {e}")
    finally:
        db4.close()

    # 注册所有TrueAgent到AGENT_REGISTRY
    import app.agents.all_agents  # noqa: F401 — 触发@register_agent装饰器

    scheduler_service.start()
    yield
    # 关闭时：停止定时任务
    scheduler_service.stop()


app = FastAPI(
    title="AI Tutor - 个性化资源生成与学习多智能体系统",
    description="基于大模型的个性化资源生成与学习多智能体系统 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS中间件（对照规范 E3：严禁 CORS 配置为 *）
_cors_origins = [
    "http://localhost:5173",    # Vite开发服务器
    "http://localhost:3000",    # 备选开发端口
    "http://localhost:80",      # Docker前端
    "http://localhost",         # Docker前端（无端口）
]
_cors_origin_env = os.getenv("CORS_ORIGIN", "")
if _cors_origin_env:
    _cors_origins.append(_cors_origin_env)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api/chat", tags=["对话"])
app.include_router(profile.router, prefix="/api/profile", tags=["画像"])
app.include_router(path.router, prefix="/api/path", tags=["学习路径"])
app.include_router(question.router, prefix="/api/questions", tags=["题库"])
app.include_router(code.router, prefix="/api/code", tags=["代码实操"])
app.include_router(multimodal.router, prefix="/api/multimodal", tags=["多模态"])
app.include_router(document.router, prefix="/api/document", tags=["文档"])
app.include_router(social.router, prefix="/api/social", tags=["社交"])
app.include_router(events.router, prefix="/api/events", tags=["事件回调"])
app.include_router(tutor.router, prefix="/api/tutor", tags=["智能辅导"])
app.include_router(video.router, prefix="/api/video", tags=["视频生成"])
app.include_router(resources.router, prefix="/api/resources", tags=["资源管理"])
app.include_router(reading.router, prefix="/api/reading", tags=["拓展阅读"])
app.include_router(assessment.router, prefix="/api/assessment", tags=["学习评估"])
app.include_router(voice.router, tags=["语音"])
app.include_router(generate.router, prefix="/api/generate", tags=["智能生成"])
app.include_router(audit.router, tags=["审计"])


@app.get("/api")
async def root():
    return {"message": "AI Tutor API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# React前端构建产物（生产模式）
import os
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.isdir(frontend_dist):
    from fastapi.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="frontend-assets")

    @app.get("/app/{full_path:path}")
    async def serve_frontend(full_path: str):
        """SPA fallback: 所有 /app/* 路由返回 index.html"""
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    @app.get("/app")
    async def serve_frontend_root():
        return FileResponse(os.path.join(frontend_dist, "index.html"))

# Manim视频输出目录（必须先于 /static 挂载，否则会被 /static 拦截）
from app.services.video_service import VIDEO_OUTPUT_DIR
os.makedirs(VIDEO_OUTPUT_DIR, exist_ok=True)
app.mount("/static/videos", StaticFiles(directory=VIDEO_OUTPUT_DIR), name="manim-videos")

# 旧版静态文件（兼容）
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ═══════════════════════════════════════════════════════════════════════════
# 前端界面（单文件 HTML）
# ═══════════════════════════════════════════════════════════════════════════
# 检查是否有单文件前端界面（$ROFESOD 或 index.html）
frontend_html_candidates = [
    "$ROFESOD",  # 单文件前端界面（乱码文件名）
    "index.html",  # 正常文件名
]
frontend_html_path = None
for candidate in frontend_html_candidates:
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), candidate)
    if os.path.exists(path):
        frontend_html_path = path
        break

if frontend_html_path:
    @app.get("/", response_class=HTMLResponse)
    async def serve_frontend():
        """返回前端界面（单文件 HTML）"""
        return FileResponse(frontend_html_path)
    import logging
    logging.getLogger(__name__).info(f"前端界面已挂载：{frontend_html_path}")
else:
    import logging
    logging.getLogger(__name__).warning("未找到前端界面文件，用户需要手动启动前端")
