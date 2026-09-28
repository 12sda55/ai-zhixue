"""题库API - Phase 4（MySQL持久化）

对照 ai_architecture_plan.md：
- 画像驱动出题（薄弱点/难度偏好/认知风格）
- 难度阶梯（L1概念 → L2原理 → L3代码）
- 题目+答案 MySQL持久化
- 答题记录追踪（连续正确/错误统计）
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.profile_service import ProfileService
from app.services.question_service import question_service
from app.rules.profile_rules import LearningEvent, EventType

logger = logging.getLogger(__name__)

router = APIRouter()
profile_service = ProfileService()


class SubmitAnswerRequest(BaseModel):
    question_id: str
    answer: str
    knowledge_point: str
    question_type: str = ""
    current_level: int = 1
    is_correct: bool = True
    time_spent: int = 0


@router.get("/{user_id}/next")
async def get_next_question(
    user_id: str,
    knowledge_point: str = Query(..., description="知识点ID"),
    current_level: Optional[int] = Query(None, description="当前难度等级"),
    db: Session = Depends(get_db),
):
    """获取下一道题（画像驱动 + 难度阶梯 + MySQL持久化）

    1. 根据学生画像（掌握度/薄弱点/难度偏好/认知风格）决定等级和题型
    2. 优先从MySQL经典题库查 → 不够则LLM动态生成并入库
    3. 返回结构化题目（选择/判断/填空/分析/编程）
    """
    profile = profile_service.get_profile(db, user_id)

    result = question_service.get_next_question(
        user_id=user_id,
        knowledge_point=knowledge_point,
        db=db,
        profile=profile,
        current_level=current_level,
    )

    return {
        "user_id": user_id,
        "knowledge_point": knowledge_point,
        "question": result["question"],
        "level": result["level"],
        "source": result["source"],
        "is_cold_start": result.get("is_cold_start", False),
    }


@router.get("/{user_id}/batch")
async def get_question_batch(
    user_id: str,
    knowledge_point: str = Query(..., description="知识点ID"),
    batch_size: int = Query(5, ge=1, le=20, description="批加载题数"),
    db: Session = Depends(get_db),
):
    """批量加载题目（前端会话模式）

    一次性返回 N 道题，前端本地管理进度：
    - 显示 "第 X/N 题" 进度条
    - 支持跳过、上一题、切换知识点
    - 会话结束时本地统计正确率
    """
    profile = profile_service.get_profile(db, user_id)

    result = question_service.get_question_batch(
        user_id=user_id,
        knowledge_point=knowledge_point,
        db=db,
        profile=profile,
        batch_size=batch_size,
    )

    # 确保每个题目的 options 和 test_cases 是 list（不是 JSON 字符串）
    for q in result["questions"]:
        if isinstance(q.get("options"), str):
            import json as _json
            try:
                q["options"] = _json.loads(q["options"])
            except Exception:
                q["options"] = []
        if isinstance(q.get("test_cases"), str):
            import json as _json
            try:
                q["test_cases"] = _json.loads(q["test_cases"])
            except Exception:
                q["test_cases"] = []

    return {
        "user_id": user_id,
        "knowledge_point": knowledge_point,
        "questions": result["questions"],
        "total": result["total"],
        "level": result["level"],
        "source_summary": result["source_summary"],
        "is_cold_start": result["is_cold_start"],
    }


@router.post("/{user_id}/submit")
async def submit_answer(
    user_id: str,
    req: SubmitAnswerRequest,
    db: Session = Depends(get_db),
):
    """提交答案 → 快速返回结果，后台异步更新画像

    优化：先返回答案+解析，画像更新放后台（不阻塞响应）
    """
    profile = profile_service.get_profile(db, user_id)
    if not profile:
        return {"error": "用户画像不存在，请先完成冷启动"}

    # 1. 记录答题到MySQL（轻量操作）
    record_result = question_service.record_answer(
        user_id=user_id,
        question_id=req.question_id,
        knowledge_point=req.knowledge_point,
        user_answer=req.answer,
        is_correct=req.is_correct,
        db=db,
        level=req.current_level,
        time_spent=req.time_spent,
    )

    # 2. 后台异步触发画像规则引擎（不阻塞响应）
    import asyncio
    event_type = EventType.ANSWER_CORRECT if req.is_correct else EventType.ANSWER_WRONG
    event = LearningEvent(
        event_type=event_type,
        user_id=user_id,
        knowledge_point=req.knowledge_point,
        data={
            "question_id": req.question_id,
            "question_type": req.question_type,
            "current_level": req.current_level,
        },
    )
    # 用后台任务执行画像更新
    asyncio.get_event_loop().run_in_executor(
        None,
        lambda: _update_profile_bg(user_id, event),
    )

    return {
        "user_id": user_id,
        "correct": req.is_correct,
        "consecutive_correct": record_result["consecutive_correct"],
        "consecutive_wrong": record_result["consecutive_wrong"],
        "current_level": req.current_level,
        "next_level": record_result["next_level"],
        "knowledge_point": req.knowledge_point,
    }


def _update_profile_bg(user_id: str, event):
    """后台更新画像（独立session，避免并发问题）"""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        profile_service.process_event(db, event)
        db.commit()
    except Exception as e:
        logger.warning(f"后台画像更新失败: {e}")
        db.rollback()
    finally:
        db.close()


@router.get("/answers/{knowledge_point}/{question_id}")
async def get_answer(
    knowledge_point: str,
    question_id: str,
    db: Session = Depends(get_db),
):
    """获取题目答案和解析"""
    result = question_service.get_answer(knowledge_point, question_id, db)
    return result


@router.get("/{user_id}/list")
async def list_questions(
    user_id: str,
    knowledge_point: str = Query(...),
    level: int = Query(1, ge=1, le=3),
    count: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """获取指定知识点和难度等级的题目列表（从MySQL）"""
    questions = question_service.get_questions_by_level(
        knowledge_point=knowledge_point,
        level=level,
        count=count,
        db=db,
    )
    return {
        "user_id": user_id,
        "knowledge_point": knowledge_point,
        "level": level,
        "count": len(questions),
        "questions": questions,
    }


@router.get("/{user_id}/history")
async def get_answer_history(
    user_id: str,
    knowledge_point: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取答题历史记录"""
    from app.models.profile import AnswerRecordModel

    query = db.query(AnswerRecordModel).filter(
        AnswerRecordModel.user_id == user_id,
    )
    if knowledge_point:
        query = query.filter(AnswerRecordModel.knowledge_point == knowledge_point)

    records = query.order_by(AnswerRecordModel.created_at.desc()).limit(limit).all()

    return {
        "user_id": user_id,
        "count": len(records),
        "records": [
            {
                "question_id": r.question_id,
                "knowledge_point": r.knowledge_point,
                "is_correct": r.is_correct,
                "time_spent": r.time_spent,
                "level": r.level_at_question,
                "created_at": str(r.created_at),
            }
            for r in records
        ],
    }
