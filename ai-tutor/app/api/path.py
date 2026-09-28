"""学习路径接口 - 对照 ai_architecture_plan.md Agent 7

完整实现：
- GET /{user_id} - 获取个性化学习路径
- GET /{user_id}/options - 多路径对比
- GET /{user_id}/simulation - 路径模拟未来
- GET /{user_id}/next - 推荐下一步
- GET /{user_id}/progress - 学习进度
- GET /{user_id}/methods - 学习方式推荐
- POST /{user_id}/choose - 选择路径策略
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.profile_service import profile_service
from app.services.path_service import path_service, PathStrategy
from app.schemas.knowledge_graph import KNOWLEDGE_GRAPH, get_categories

router = APIRouter()


@router.get("/knowledge-points")
async def get_knowledge_points():
    """获取所有知识点列表（供前端下拉选择等使用）"""
    categories = get_categories()
    points = []
    for node in KNOWLEDGE_GRAPH:
        points.append({
            "id": node.id,
            "name": node.name,
            "category": node.category,
        })
    return {
        "status": "ok",
        "knowledge_points": points,
        "categories": {cat: kps for cat, kps in categories.items()},
    }


@router.get("/{user_id}")
async def get_path(
    user_id: str,
    strategy: Optional[str] = Query(None, description="路径策略: steady/focused/practice"),
    db: Session = Depends(get_db),
):
    """获取个性化学习路径"""
    profile = profile_service.get_profile(db, user_id)
    if not profile:
        return {"status": "error", "message": "画像不存在，请先完成冷启动"}

    # 确定策略
    if strategy and strategy in [s.value for s in PathStrategy]:
        path_strategy = PathStrategy(strategy)
    else:
        path_strategy = path_service.recommend_strategy(profile)

    path = path_service.generate_path(profile, path_strategy)
    return {
        "status": "ok",
        "strategy": path_strategy.value,
        "recommended_strategy": path_service.recommend_strategy(profile).value,
        "path": path.model_dump(),
    }


@router.get("/{user_id}/options")
async def get_path_options(
    user_id: str,
    db: Session = Depends(get_db),
):
    """获取多路径对比方案 - 创新功能9"""
    profile = profile_service.get_profile(db, user_id)
    if not profile:
        return {"status": "error", "message": "画像不存在"}

    multi = path_service.generate_multi_path(profile)
    recommended = path_service.recommend_strategy(profile)

    return {
        "status": "ok",
        "recommended_strategy": recommended.value,
        "paths": {
            key: path.model_dump() for key, path in multi.items()
        },
    }


@router.get("/{user_id}/simulation")
async def get_path_simulation(
    user_id: str,
    strategy: Optional[str] = Query(None, description="路径策略"),
    db: Session = Depends(get_db),
):
    """路径模拟未来 - 创新功能8"""
    profile = profile_service.get_profile(db, user_id)
    if not profile:
        return {"status": "error", "message": "画像不存在"}

    if strategy and strategy in [s.value for s in PathStrategy]:
        path_strategy = PathStrategy(strategy)
    else:
        path_strategy = path_service.recommend_strategy(profile)

    path = path_service.generate_path(profile, path_strategy)
    simulations = path_service.simulate_future(profile, path)

    return {
        "status": "ok",
        "strategy": path_strategy.value,
        "simulations": [s.model_dump() for s in simulations],
    }


@router.get("/{user_id}/next")
async def get_next_step(
    user_id: str,
    db: Session = Depends(get_db),
):
    """推荐下一步学习内容"""
    profile = profile_service.get_profile(db, user_id)
    if not profile:
        return {"status": "error", "message": "画像不存在"}

    next_node = path_service.recommend_next_step(profile)
    if not next_node:
        return {"status": "ok", "message": "所有知识点已掌握！", "next": None}

    return {
        "status": "ok",
        "next": next_node.model_dump(),
    }


@router.get("/{user_id}/progress")
async def get_progress(
    user_id: str,
    db: Session = Depends(get_db),
):
    """获取学习进度概览"""
    profile = profile_service.get_profile(db, user_id)
    if not profile:
        return {"status": "error", "message": "画像不存在"}

    progress = path_service.get_progress(profile)
    return {
        "status": "ok",
        "progress": progress,
    }


@router.get("/{user_id}/methods")
async def get_method_recommendations(
    user_id: str,
    db: Session = Depends(get_db),
):
    """获取学习方式推荐"""
    profile = profile_service.get_profile(db, user_id)
    if not profile:
        return {"status": "error", "message": "画像不存在"}

    recommendations = path_service.get_method_recommendations(profile)
    return {
        "status": "ok",
        "recommendations": [r.model_dump() for r in recommendations],
    }


@router.post("/{user_id}/choose")
async def choose_path(
    user_id: str,
    strategy: str = Query(..., description="选择的策略: steady/focused/practice"),
    db: Session = Depends(get_db),
):
    """学生选择路径策略"""
    if strategy not in [s.value for s in PathStrategy]:
        return {"status": "error", "message": f"无效策略: {strategy}"}

    profile = profile_service.get_profile(db, user_id)
    if not profile:
        return {"status": "error", "message": "画像不存在"}

    path = path_service.generate_path(profile, PathStrategy(strategy))
    return {
        "status": "ok",
        "strategy": strategy,
        "path": path.model_dump(),
    }
