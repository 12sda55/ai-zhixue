"""事件回调接口 - 前端上报学习行为，触发画像规则引擎

对照 ai_architecture_plan.md 的11条P0规则
"""

from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.rules.profile_rules import LearningEvent, EventType, DifficultyLevel
from app.services.profile_service import profile_service

router = APIRouter()


class EventRequest(BaseModel):
    """学习行为事件请求"""
    user_id: str
    event_type: str
    knowledge_point: Optional[str] = None
    difficulty: Optional[str] = None  # basic/intermediate/advanced
    data: dict = {}


# 事件类型映射（前端字符串 → EventType枚举）
EVENT_TYPE_MAP = {
    "answer_correct": EventType.ANSWER_CORRECT,
    "answer_wrong": EventType.ANSWER_WRONG,
    "consecutive_correct_3": EventType.CONSECUTIVE_CORRECT_3,
    "consecutive_wrong_2": EventType.CONSECUTIVE_WRONG_2,
    "self_report_weak": EventType.SELF_REPORT_WEAK,
    "self_report_mastered": EventType.SELF_REPORT_MASTERED,
    "express_confusion": EventType.EXPRESS_CONFUSION,
    "code_pass_1_2_iterations": EventType.CODE_PASS_1_2_ITERATIONS,
    "code_pass_6_plus_iterations": EventType.CODE_PASS_6_PLUS_ITERATIONS,
    "code_performance_deviation": EventType.CODE_PERFORMANCE_DEVIATION,
    "forgetting_curve_decay": EventType.FORGETTING_CURVE_DECAY,
}

# 难度映射
DIFFICULTY_MAP = {
    "basic": DifficultyLevel.BASIC,
    "intermediate": DifficultyLevel.INTERMEDIATE,
    "advanced": DifficultyLevel.ADVANCED,
}


@router.post("/")
async def report_event(event: EventRequest, db: Session = Depends(get_db)):
    """前端上报学习行为事件

    支持的事件类型：
    - answer_correct（答题正确）
    - answer_wrong（答题错误）
    - consecutive_correct_3（连续正确3题）
    - consecutive_wrong_2（连续错误2题）
    - self_report_weak（自述薄弱）
    - self_report_mastered（自述已掌握）
    - express_confusion（表达困惑）
    - code_pass_1_2_iterations（代码1-2次迭代通过）
    - code_pass_6_plus_iterations（代码6+次迭代通过）
    - code_performance_deviation（代码性能偏离理论值）
    """
    # 映射事件类型
    event_type = EVENT_TYPE_MAP.get(event.event_type)
    if event_type is None:
        return {"status": "error", "message": f"未知事件类型: {event.event_type}"}

    # 构建LearningEvent
    difficulty = DIFFICULTY_MAP.get(event.difficulty or "intermediate", DifficultyLevel.INTERMEDIATE)

    learning_event = LearningEvent(
        event_type=event_type,
        user_id=event.user_id,
        knowledge_point=event.knowledge_point or "",
        difficulty=difficulty,
        data=event.data,
    )

    # 调用画像规则引擎
    changes = profile_service.process_event(db, learning_event)

    return {
        "status": "ok",
        "event_type": event.event_type,
        "changes_count": len(changes),
        "changes": [
            {
                "dimension": c.dimension,
                "field": c.field,
                "old_value": c.old_value,
                "new_value": c.new_value,
                "reason": c.reason,
            }
            for c in changes
        ],
    }


@router.post("/batch")
async def report_events(events: list[EventRequest], db: Session = Depends(get_db)):
    """批量上报学习行为事件（防抖动：同一维度多次变更合并）"""
    learning_events = []

    for event in events:
        event_type = EVENT_TYPE_MAP.get(event.event_type)
        if event_type is None:
            continue

        difficulty = DIFFICULTY_MAP.get(event.difficulty or "intermediate", DifficultyLevel.INTERMEDIATE)

        learning_events.append(LearningEvent(
            event_type=event_type,
            user_id=event.user_id,
            knowledge_point=event.knowledge_point or "",
            difficulty=difficulty,
            data=event.data,
        ))

    changes = profile_service.batch_process_events(db, learning_events)

    return {
        "status": "ok",
        "total_events": len(events),
        "processed_events": len(learning_events),
        "changes_count": len(changes),
    }


@router.post("/trigger_decay")
async def trigger_forgetting_decay():
    """手动触发遗忘曲线衰减检查（定时任务手动触发）"""
    from app.core.scheduler import scheduler_service
    result = await scheduler_service.trigger_forgetting_decay()
    return {"status": "ok", **result}


@router.post("/trigger_review/{user_id}")
async def trigger_profile_review(user_id: str):
    """手动触发指定用户的画像审视（定时任务手动触发）"""
    from app.core.scheduler import scheduler_service
    result = await scheduler_service.trigger_profile_review(user_id)
    return {"status": "ok", **result}
