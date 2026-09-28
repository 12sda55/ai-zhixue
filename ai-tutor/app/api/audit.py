# -*- coding: utf-8 -*-
"""协同决策审计 API — 查询决策日志（答辩/评审展示、运行监控）"""
from fastapi import APIRouter, Query

from app.services.audit_service import list_decisions, count_decisions

router = APIRouter(prefix="/api/audit", tags=["审计"])


@router.get("/decisions")
async def get_decisions(
    limit: int = Query(20, ge=1, le=200),
    user_id: str = None,
):
    """查询协同决策日志（新→旧）"""
    return {
        "total": count_decisions(),
        "items": list_decisions(limit=limit, user_id=user_id),
    }
