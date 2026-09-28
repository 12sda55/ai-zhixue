"""文档接口 - 文档生成Agent

对照 ai_architecture_plan.md：
- RAG知识库检索 + LLM个性化文档生成
- 画像感知：根据掌握度/薄弱环节/认知风格调整内容
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.knowledge_service import knowledge_service
from app.services.profile_service import profile_service

router = APIRouter()


@router.get("/detail/{knowledge_point}")
async def get_document(
    knowledge_point: str,
    user_id: Optional[str] = None,
    style: str = "concept",
    db: Session = Depends(get_db),
):
    """获取个性化文档（RAG + LLM生成）"""
    profile = None
    if user_id:
        profile = profile_service.get_profile(db, user_id)

    result = knowledge_service.generate_document(
        knowledge_point=knowledge_point,
        user_id=user_id or "anonymous",
        profile=profile,
        style=style,
    )
    return result


@router.get("/search")
async def search_knowledge(query: str, n: int = 3):
    """RAG检索：搜索相关知识"""
    results = knowledge_service.search(query, n_results=n)
    return {"query": query, "results": results}


@router.get("/mindmap/{knowledge_point}")
async def get_mindmap(knowledge_point: str):
    """获取思维导图数据"""
    from app.schemas.knowledge_graph import get_knowledge_node, get_dependencies
    node = get_knowledge_node(knowledge_point)
    if not node:
        return {"error": f"知识点 {knowledge_point} 不存在"}

    deps = get_dependencies(knowledge_point)
    return {
        "center": {"id": knowledge_point, "name": node.name},
        "dependencies": [
            {"id": d, "name": get_knowledge_node(d).name if get_knowledge_node(d) else d}
            for d in deps
        ],
    }


@router.get("/{knowledge_point}/outline")
async def get_document_outline(knowledge_point: str, user_id: Optional[str] = None):
    """获取文档大纲"""
    text = knowledge_service.get_knowledge_text(knowledge_point)
    if not text:
        return {"error": f"知识点 {knowledge_point} 不存在"}

    # 从markdown文本中提取标题作为大纲
    lines = text.strip().split("\n")
    outline = []
    for line in lines:
        if line.startswith("#"):
            level = line.count("#")
            title = line.lstrip("#").strip()
            outline.append({"level": level, "title": title})

    return {"knowledge_point": knowledge_point, "outline": outline}
