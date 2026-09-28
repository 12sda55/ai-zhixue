"""资源接口 - 对照 AI开发指南_产品内核与架构规范.md 第6.2节

所有Agent生成的资源持久化存储，每个资源关联知识图谱节点。
"""

from __future__ import annotations
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.profile import ResourceModel

router = APIRouter()


# ===== 请求模型 =====

class ResourceQueryRequest(BaseModel):
    """资源查询请求"""
    type: Optional[str] = None
    kg_node_id: Optional[str] = None
    path_node_id: Optional[str] = None
    limit: int = 20


# ===== 接口 =====

@router.get("/{user_id}")
async def list_resources(
    user_id: str,
    type: Optional[str] = Query(None, description="资源类型过滤"),
    kg_node_id: Optional[str] = Query(None, description="知识图谱节点ID过滤"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """列出用户的所有资源"""
    query = db.query(ResourceModel).filter(ResourceModel.user_id == user_id)

    if type:
        query = query.filter(ResourceModel.type == type)

    if kg_node_id:
        # kg_node_ids 是JSON数组，用LIKE模糊匹配
        query = query.filter(ResourceModel.kg_node_ids.contains(kg_node_id))

    resources = query.order_by(ResourceModel.created_at.desc()).limit(limit).all()

    return {
        "user_id": user_id,
        "resources": [
            {
                "id": r.id,
                "type": r.type,
                "title": r.title,
                "kg_node_ids": json.loads(r.kg_node_ids) if r.kg_node_ids else [],
                "path_node_id": r.path_node_id or None,
                "parent_resource_id": r.parent_resource_id or None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in resources
        ],
        "count": len(resources),
    }


@router.get("/{user_id}/{resource_id}")
async def get_resource(
    user_id: str,
    resource_id: str,
    db: Session = Depends(get_db),
):
    """获取单个资源的完整内容"""
    resource = db.query(ResourceModel).filter(
        ResourceModel.id == resource_id,
        ResourceModel.user_id == user_id,
    ).first()

    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")

    return {
        "id": resource.id,
        "type": resource.type,
        "title": resource.title,
        "content": json.loads(resource.content_json) if resource.content_json else {},
        "kg_node_ids": json.loads(resource.kg_node_ids) if resource.kg_node_ids else [],
        "path_node_id": resource.path_node_id or None,
        "parent_resource_id": resource.parent_resource_id or None,
        "user_id": resource.user_id,
        "created_at": resource.created_at.isoformat() if resource.created_at else None,
    }


@router.get("/{user_id}/by-kp/{knowledge_point}")
async def get_resources_by_knowledge_point(
    user_id: str,
    knowledge_point: str,
    db: Session = Depends(get_db),
):
    """根据知识点ID查找关联的所有资源

    对照规范：当用户学到某个路径节点时，系统能自动找到该节点下已有的资源
    """
    resources = db.query(ResourceModel).filter(
        ResourceModel.user_id == user_id,
        ResourceModel.kg_node_ids.contains(knowledge_point),
    ).order_by(ResourceModel.created_at.desc()).all()

    return {
        "user_id": user_id,
        "knowledge_point": knowledge_point,
        "resources": [
            {
                "id": r.id,
                "type": r.type,
                "title": r.title,
                "kg_node_ids": json.loads(r.kg_node_ids) if r.kg_node_ids else [],
                "path_node_id": r.path_node_id or None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in resources
        ],
        "count": len(resources),
    }


@router.delete("/{user_id}/{resource_id}")
async def delete_resource(
    user_id: str,
    resource_id: str,
    db: Session = Depends(get_db),
):
    """删除资源"""
    resource = db.query(ResourceModel).filter(
        ResourceModel.id == resource_id,
        ResourceModel.user_id == user_id,
    ).first()

    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")

    db.delete(resource)
    db.commit()
    return {"message": "资源已删除"}
