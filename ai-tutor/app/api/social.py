"""社交与创新功能接口 - 对照 ai_architecture_plan.md 创新功能

完整实现：
- GET /partner/{user_id}/recommend - 学习伙伴匹配
- GET /dashboard/{user_id} - 学习效果仪表盘
- GET /dashboard/{user_id}/achievements - 成就系统
- GET /dashboard/{user_id}/radar - 雷达图数据
- GET /review-schedule/{user_id} - 遗忘曲线复习调度
- GET /code/shared - 共享代码列表
- POST /code/shared - 分享代码
- POST /code/shared/{code_id}/rate - 评分代码
- GET /code/evolution/{user_id} - 代码进化轨迹
- POST /code/evolution - 记录代码迭代
- POST /code/performance - 性能擂台
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.profile_service import profile_service
from app.services.path_service import path_service
from app.services.innovation_service import innovation_service

router = APIRouter()


class ShareCodeRequest(BaseModel):
    """分享代码请求"""
    user_id: str
    knowledge_point: str
    title: str
    code: str
    tags: list[str] = Field(default_factory=list)


class RateCodeRequest(BaseModel):
    """评分代码请求"""
    rating: int = Field(ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    user_id: str = ""


class CodeIterationRequest(BaseModel):
    """代码迭代记录请求"""
    user_id: str
    knowledge_point: str
    code: str
    status: str  # syntax_error / runtime_error / logic_error / passed / optimized
    template_id: str = ""
    error_message: str = ""


class PerformanceArenaRequest(BaseModel):
    """性能擂台请求"""
    code: str
    knowledge_point: str
    complexity_class: str = ""  # O(n), O(n²), O(n log n)


@router.get("/partner/{user_id}/recommend")
async def recommend_partners(
    user_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """推荐学习伙伴 - 基于画像余弦相似度"""
    profile = profile_service.get_profile(db, user_id)
    if not profile:
        return {"status": "error", "message": "画像不存在"}

    # 获取其他用户画像（从数据库）
    all_profiles = profile_service.list_profiles(db, exclude_user_id=user_id, limit=50)

    matches = path_service.match_partners(profile, all_profiles, limit=limit)
    return {
        "status": "ok",
        "matches": [m.model_dump() for m in matches],
    }


@router.get("/dashboard/{user_id}")
async def get_dashboard(
    user_id: str,
    db: Session = Depends(get_db),
):
    """学习效果仪表盘 - 创新功能14"""
    profile = profile_service.get_profile(db, user_id)
    if not profile:
        return {"status": "error", "message": "画像不存在"}

    dashboard = innovation_service.get_dashboard(profile)
    return {
        "status": "ok",
        "dashboard": dashboard.model_dump(),
    }


@router.get("/dashboard/{user_id}/achievements")
async def get_achievements(
    user_id: str,
    db: Session = Depends(get_db),
):
    """成就系统"""
    profile = profile_service.get_profile(db, user_id)
    if not profile:
        return {"status": "error", "message": "画像不存在"}

    dashboard = innovation_service.get_dashboard(profile)
    return {
        "status": "ok",
        "achievements": [a.model_dump() for a in dashboard.achievements],
    }


@router.get("/dashboard/{user_id}/radar")
async def get_radar(
    user_id: str,
    db: Session = Depends(get_db),
):
    """雷达图数据"""
    profile = profile_service.get_profile(db, user_id)
    if not profile:
        return {"status": "error", "message": "画像不存在"}

    dashboard = innovation_service.get_dashboard(profile)
    return {
        "status": "ok",
        "radar": dashboard.radar.model_dump() if dashboard.radar else None,
    }


@router.get("/review-schedule/{user_id}")
async def get_review_schedule(
    user_id: str,
    db: Session = Depends(get_db),
):
    """遗忘曲线复习调度 - 创新功能3"""
    profile = profile_service.get_profile(db, user_id)
    if not profile:
        return {"status": "error", "message": "画像不存在"}

    schedule = innovation_service.get_review_schedule(profile)
    return {
        "status": "ok",
        "schedule": [s.model_dump() for s in schedule],
    }


@router.get("/code/shared")
async def get_shared_codes(
    knowledge_point: Optional[str] = Query(None),
    sort_by: str = Query("rating"),
):
    """获取共享代码列表"""
    codes = innovation_service.get_shared_codes(knowledge_point, sort_by)
    return {
        "status": "ok",
        "codes": [c.model_dump() for c in codes],
    }


@router.post("/code/shared")
async def share_code(req: ShareCodeRequest):
    """分享代码 - 创新功能13"""
    result = innovation_service.share_code(
        user_id=req.user_id,
        knowledge_point=req.knowledge_point,
        title=req.title,
        code=req.code,
        tags=req.tags,
    )
    return {"status": "ok", "code": result.model_dump()}


@router.post("/code/shared/{code_id}/rate")
async def rate_shared_code(code_id: str, req: RateCodeRequest):
    """评分共享代码"""
    result = innovation_service.rate_shared_code(
        code_id=code_id,
        rating=req.rating,
        tags=req.tags,
        user_id=req.user_id,
    )
    if not result:
        return {"status": "error", "message": "代码不存在"}
    return {"status": "ok", "code": result.model_dump()}


@router.get("/code/evolution/{user_id}")
async def get_code_evolution(
    user_id: str,
    knowledge_point: str = Query(...),
    template_id: str = Query(""),
):
    """获取代码进化轨迹 - 创新功能9"""
    evolution = innovation_service.get_code_evolution(user_id, knowledge_point, template_id)
    if not evolution:
        return {"status": "ok", "evolution": None}
    return {"status": "ok", "evolution": evolution.model_dump()}


@router.post("/code/evolution")
async def record_code_iteration(req: CodeIterationRequest):
    """记录代码迭代"""
    evolution = innovation_service.record_code_iteration(
        user_id=req.user_id,
        knowledge_point=req.knowledge_point,
        code=req.code,
        status=req.status,
        template_id=req.template_id,
        error_message=req.error_message,
    )
    return {"status": "ok", "evolution": evolution.model_dump()}


@router.post("/code/performance")
async def run_performance_arena(req: PerformanceArenaRequest):
    """性能擂台 - 创新功能8"""
    result = innovation_service.run_performance_arena(
        code=req.code,
        knowledge_point=req.knowledge_point,
        complexity_class=req.complexity_class,
    )
    return {"status": "ok", "arena": result.model_dump()}
