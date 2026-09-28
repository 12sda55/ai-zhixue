"""智能辅导接口 - 对照 ai_architecture_plan.md Agent 8

完整实现：
- POST /ask - 智能辅导（Socratic引导/渐进提示/直接讲解）
- POST /classify - 问题类型分类
- GET /hints - 渐进式提示
- POST /safety-valve - 安全阀检查
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.profile_service import profile_service
from app.services.tutor_service import tutor_service, QuestionType

router = APIRouter()


class TutorAskRequest(BaseModel):
    """辅导请求"""
    knowledge_point: str
    question: str
    mode: str = Field(default="socratic", description="辅导模式: socratic/hint/explain")
    user_id: str = ""


class ClassifyRequest(BaseModel):
    """问题分类请求"""
    question: str
    knowledge_point: str = ""


class HintsRequest(BaseModel):
    """渐进提示请求"""
    knowledge_point: str
    question: str
    user_id: str = ""


class SafetyValveRequest(BaseModel):
    """安全阀检查请求"""
    user_id: str
    knowledge_point: str
    question: str = ""


@router.post("/ask")
async def tutor_ask(
    req: TutorAskRequest,
    db: Session = Depends(get_db),
):
    """智能辅导主入口"""
    profile = None
    if req.user_id:
        profile = profile_service.get_profile(db, req.user_id)

    result = tutor_service.tutor(
        knowledge_point=req.knowledge_point,
        question=req.question,
        mode=req.mode,
        profile=profile,
    )
    return {"status": "ok", **result}


@router.post("/classify")
async def classify_question(req: ClassifyRequest):
    """问题类型分类"""
    q_type = tutor_service.classify_question(req.question, req.knowledge_point)
    return {
        "status": "ok",
        "question_type": q_type.value,
        "description": {
            "conceptual": "概念性问题 - 直接回答+类比",
            "understanding": "理解性问题 - Socratic多步引导",
            "debugging": "调试性问题 - 提示方向",
            "application": "应用性问题 - 提示思路",
        }.get(q_type.value, ""),
    }


@router.post("/hints")
async def get_progressive_hints(
    req: HintsRequest,
    db: Session = Depends(get_db),
):
    """获取渐进式提示"""
    profile = None
    if req.user_id:
        profile = profile_service.get_profile(db, req.user_id)

    hints = tutor_service.generate_progressive_hints(
        knowledge_point=req.knowledge_point,
        question=req.question,
        profile=profile,
    )
    return {"status": "ok", "hints": hints}


@router.post("/safety-valve")
async def check_safety_valve(req: SafetyValveRequest):
    """安全阀检查"""
    result = tutor_service.check_safety_valve(
        user_id=req.user_id,
        knowledge_point=req.knowledge_point,
        question=req.question,
    )
    return {"status": "ok", **result}
