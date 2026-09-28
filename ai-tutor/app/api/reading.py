"""拓展阅读接口 - 对照规范 B7

完整实现：
- POST /generate - 生成拓展阅读
- GET /{user_id}/{knowledge_point} - 获取缓存的拓展阅读
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.reading_service import reading_service
from app.services.profile_service import profile_service
from app.models.profile import ResourceModel

router = APIRouter()


class ReadingGenerateRequest(BaseModel):
    """拓展阅读生成请求"""
    knowledge_point: str
    user_id: str = ""


@router.post("/generate")
async def generate_reading(
    req: ReadingGenerateRequest,
    db: Session = Depends(get_db),
):
    """生成拓展阅读材料"""
    profile = None
    if req.user_id:
        profile = profile_service.get_profile(db, req.user_id)

    result = reading_service.generate_reading(
        knowledge_point=req.knowledge_point,
        profile=profile,
    )
    return {"status": "ok", **result}


@router.get("/{user_id}/{knowledge_point}")
async def get_cached_reading(
    user_id: str,
    knowledge_point: str,
    db: Session = Depends(get_db),
):
    """获取缓存的拓展阅读"""
    # 从资源表中查找最近的reading类型资源
    resource = (
        db.query(ResourceModel)
        .filter(
            ResourceModel.user_id == user_id,
            ResourceModel.type == "reading",
            ResourceModel.kg_node_ids.contains(knowledge_point),
        )
        .order_by(ResourceModel.created_at.desc())
        .first()
    )

    if resource:
        import json
        content = json.loads(resource.content_json) if resource.content_json else {}
        return {
            "status": "ok",
            "resource_id": resource.id,
            "title": resource.title,
            "content": content.get("content", ""),
            "references": content.get("references", []),
            "knowledge_point": knowledge_point,
            "kg_node_ids": json.loads(resource.kg_node_ids) if resource.kg_node_ids else [],
            "created_at": resource.created_at.isoformat() if resource.created_at else None,
        }

    return {"status": "ok", "message": "暂无缓存的拓展阅读", "content": None}
