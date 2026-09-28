"""画像接口 - 对照 ai_architecture_plan.md 的9维度画像定义"""

from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.profile import (
    StudentProfile, Major, Stage, CognitiveStyle,
    LearningPace, LearningPreference, DifficultyLevel,
)
from app.services.profile_service import profile_service
from app.services.cold_start_service import cold_start_service

router = APIRouter()


# ===== 请求模型 =====

class ProfileInitRequest(BaseModel):
    """冷启动画像构建请求 - 4个冷启动问题"""
    major: Major = Major.NON_CS
    stage: Stage = Stage.SYNCHRONOUS
    learning_goals: list[str] = []
    cognitive_style: CognitiveStyle = CognitiveStyle.VISUAL


class ProfileInitFromConversationRequest(BaseModel):
    """LLM冷启动画像构建请求 - 从对话中提取画像特征"""
    conversation: str


class ProfileUpdateRequest(BaseModel):
    """画像手动更新请求"""
    major: Optional[Major] = None
    stage: Optional[Stage] = None
    cognitive_style: Optional[CognitiveStyle] = None
    learning_goals: Optional[list[str]] = None
    learning_pace: Optional[LearningPace] = None
    learning_preference: Optional[LearningPreference] = None
    difficulty_level: Optional[DifficultyLevel] = None


class ColdStartChatRequest(BaseModel):
    """冷启动对话请求"""
    user_id: str
    message: str
    conversation_history: list[dict] = []  # [{role: "user"/"ai", content: "..."}]


class ColdStartChatResponse(BaseModel):
    """冷启动对话响应"""
    reply: str
    is_complete: bool  # 是否已收集足够信息
    profile: Optional[dict] = None  # is_complete=True时返回画像
    push_message: Optional[str] = None  # 完成后的推送消息（如"要我帮你规划学习路径吗？"）
    quick_action: Optional[str] = None  # 快捷动作标识
    quick_action_label: Optional[str] = None  # 快捷动作按钮文字


# ===== 接口 =====

@router.get("/{user_id}")
async def get_profile(user_id: str, db: Session = Depends(get_db)):
    """获取完整画像"""
    profile = profile_service.get_profile(db, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="画像不存在")
    return profile.model_dump()


@router.get("/{user_id}/radar")
async def get_profile_radar(user_id: str, db: Session = Depends(get_db)):
    """获取雷达图数据 - 5个维度的掌握度"""
    profile = profile_service.get_or_create_profile(db, user_id)

    # 按分类计算平均mastery
    from app.schemas.knowledge_graph import get_categories
    categories = get_categories()

    radar_data = []
    for category, node_ids in categories.items():
        masteries = [profile.get_knowledge_mastery(nid) for nid in node_ids]
        avg_mastery = sum(masteries) / len(masteries) if masteries else 0
        radar_data.append({
            "category": category,
            "mastery": round(avg_mastery, 2),
            "node_count": len(node_ids),
        })

    return {
        "user_id": user_id,
        "radar": radar_data,
        "weak_points": [wp.knowledge_point for wp in profile.weak_points],
        "difficulty_level": profile.difficulty_level.value,
        "conversation_count": profile.conversation_count,
    }


@router.post("/cold-start/chat")
async def cold_start_chat(request: ColdStartChatRequest, db: Session = Depends(get_db)):
    """冷启动对话 - 通过3-5轮自然对话采集画像信息

    流程：
    1. 用户首次进入，系统自动打招呼
    2. 用户回答后，LLM追问（每轮只问1个问题）
    3. 3-5轮对话后，LLM提取画像特征，构建画像
    4. 采集完成后，通过SessionStateMachine过渡到idle状态
    5. 通过ProactivePushSystem触发"after_cold_start_completed"
    6. 老用户回归不再触发冷启动
    """
    from app.core.llm import llm_client
    from app.core.session_state import session_state_machine, SessionState
    from app.core.proactive_push import proactive_push

    # 老用户回归检查：如果已有画像，不再触发冷启动
    existing = profile_service.get_profile(db, request.user_id)
    if existing is not None:
        return ColdStartChatResponse(
            reply="欢迎回来！你的画像已存在，可以直接开始学习。",
            is_complete=True,
            profile=existing.model_dump(),
        )

    # 计算当前对话轮次（用户消息数）
    user_msg_count = sum(1 for m in request.conversation_history if m.get("role") == "user")
    if request.message:
        user_msg_count += 1

    # 构建对话上下文
    system_prompt = """你是小智，一个学习辅导老师。你的任务是通过自然对话了解学生的背景，以便为他制定个性化学习方案。

你需要了解以下信息（按优先级排列）：
1. 专业背景（计算机/理工科/文科/跨考）
2. 当前学习阶段（预习/同步学习/复习/备考）
3. 学习目标（期末考试/考研/提升能力等）
4. 对各学科知识点的熟悉程度（哪些学过，哪些不会）
5. 学习偏好（看图/读文档/写代码）

对话规则：
- 用自然、亲切的语气提问，像朋友聊天一样
- **每轮只问1个问题**，不要一次问多个
- 根据学生的回答灵活追问，深入挖掘
- 对话必须进行3-5轮后再完成采集
- 前2轮不要结束采集，即使信息看起来够了也要追问细节
- 当你确认已收集到足够信息（至少3轮对话后），在回复末尾加上 [PROFILE_COMPLETE]
- 回复要简洁，每次回复控制在2-3句话以内

第一轮对话时，请先打招呼并询问学生的专业背景。"""

    # 构建消息列表
    messages = [{"role": "system", "content": system_prompt}]

    # 添加历史对话
    for msg in request.conversation_history:
        role = "assistant" if msg.get("role") == "ai" else "user"
        messages.append({"role": role, "content": msg.get("content", "")})

    # 添加当前用户消息
    if request.message:
        messages.append({"role": "user", "content": request.message})

    try:
        reply = llm_client.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=512,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM调用失败: {e}")

    # 判断是否收集完成
    is_complete = "[PROFILE_COMPLETE]" in reply
    reply = reply.replace("[PROFILE_COMPLETE]", "").strip()

    # 强制：不足3轮不允许完成
    if is_complete and user_msg_count < 3:
        is_complete = False
        reply += "\n\n对了，还有个问题想了解一下——"

    profile_dict = None
    push_message = None
    quick_action = None
    quick_action_label = None

    if is_complete:
        # 构建完整对话文本用于画像提取
        conversation_parts = []
        for msg in request.conversation_history:
            role_label = "AI" if msg.get("role") == "ai" else "学生"
            conversation_parts.append(f"{role_label}: {msg.get('content', '')}")
        conversation_parts.append(f"学生: {request.message}")
        conversation_text = "\n".join(conversation_parts)

        try:
            profile = cold_start_service.build_from_conversation(
                user_id=request.user_id,
                conversation=conversation_text,
            )
            profile = profile_service.create_profile(db, profile)
            profile_dict = profile.model_dump()
        except Exception as e:
            # 画像构建失败，降级为默认画像
            from app.schemas.profile import StudentProfile as SP
            default_profile = SP(user_id=request.user_id)
            profile = profile_service.create_profile(db, default_profile)
            profile_dict = profile.model_dump()

        # 通过SessionStateMachine过渡到idle状态
        try:
            session_state_machine.transition(request.user_id, SessionState.IDLE)
            session_state_machine.save_to_redis(request.user_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"SessionStateMachine transition failed: {e}")

        # 通过ProactivePushSystem触发"after_cold_start_completed"
        try:
            push_msg = proactive_push.check_and_push(
                "after_cold_start_completed",
                context={"user_id": request.user_id},
            )
            if push_msg:
                push_message = push_msg.text
                quick_action = push_msg.quick_action
                quick_action_label = push_msg.quick_action_label
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"ProactivePushSystem check_and_push failed: {e}")

    return ColdStartChatResponse(
        reply=reply,
        is_complete=is_complete,
        profile=profile_dict,
        push_message=push_message,
        quick_action=quick_action,
        quick_action_label=quick_action_label,
    )


@router.post("/{user_id}/init")
async def init_profile(user_id: str, request: ProfileInitRequest, db: Session = Depends(get_db)):
    """冷启动画像构建 - 4个冷启动问题（结构化输入）"""
    # 检查是否已有画像
    existing = profile_service.get_profile(db, user_id)
    if existing is not None:
        raise HTTPException(status_code=400, detail="画像已存在，请使用更新接口")

    # 使用冷启动服务构建画像
    profile = cold_start_service.build_from_structured(
        user_id=user_id,
        major=request.major,
        stage=request.stage,
        learning_goals=request.learning_goals,
        cognitive_style=request.cognitive_style,
    )

    profile = profile_service.create_profile(db, profile)
    return {"message": "画像创建成功", "profile": profile.model_dump()}


@router.post("/{user_id}/init_from_conversation")
async def init_profile_from_conversation(
    user_id: str,
    request: ProfileInitFromConversationRequest,
    db: Session = Depends(get_db),
):
    """冷启动画像构建 - LLM从对话中提取画像特征"""
    # 检查是否已有画像
    existing = profile_service.get_profile(db, user_id)
    if existing is not None:
        raise HTTPException(status_code=400, detail="画像已存在，请使用更新接口")

    # 使用LLM从对话中提取画像特征
    profile = cold_start_service.build_from_conversation(
        user_id=user_id,
        conversation=request.conversation,
    )

    profile = profile_service.create_profile(db, profile)
    return {"message": "LLM冷启动画像创建成功", "profile": profile.model_dump()}


@router.put("/{user_id}")
async def update_profile(user_id: str, request: ProfileUpdateRequest, db: Session = Depends(get_db)):
    """手动更新画像"""
    profile = profile_service.get_profile(db, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="画像不存在")

    # 只更新非None的字段
    if request.major is not None:
        profile.major = request.major
    if request.stage is not None:
        profile.stage = request.stage
    if request.cognitive_style is not None:
        profile.cognitive_style = request.cognitive_style
    if request.learning_goals is not None:
        profile.learning_goals = request.learning_goals
    if request.learning_pace is not None:
        profile.learning_pace = request.learning_pace
    if request.learning_preference is not None:
        profile.learning_preference = request.learning_preference
    if request.difficulty_level is not None:
        profile.difficulty_level = request.difficulty_level

    profile_service.update_profile(db, profile, "用户手动更新画像")
    return {"message": "画像更新成功", "profile": profile.model_dump()}


@router.get("/{user_id}/snapshots")
async def get_snapshots(user_id: str, limit: int = 20, db: Session = Depends(get_db)):
    """获取画像快照列表（学习成长轨迹）"""
    snapshots = profile_service.get_snapshots(db, user_id, limit)
    return {
        "user_id": user_id,
        "snapshots": [
            {
                "id": s["id"],
                "reason": s["reason"],
                "created_at": s["created_at"].isoformat(),
                "weak_points": [wp.knowledge_point for wp in s["profile"].weak_points],
                "difficulty_level": s["profile"].difficulty_level.value,
            }
            for s in snapshots
        ],
    }


@router.get("/{user_id}/dashboard")
async def get_dashboard(user_id: str, db: Session = Depends(get_db)):
    """学习效果仪表盘数据"""
    profile = profile_service.get_or_create_profile(db, user_id)
    from app.schemas.knowledge_graph import get_categories, KNOWLEDGE_GRAPH

    categories = get_categories()
    total_nodes = len(KNOWLEDGE_GRAPH)
    mastered_count = sum(1 for nid in [n.id for n in KNOWLEDGE_GRAPH]
                         if profile.get_knowledge_mastery(nid) >= 0.7)

    return {
        "user_id": user_id,
        "total_progress": round(mastered_count / total_nodes, 2) if total_nodes > 0 else 0,
        "mastered_count": mastered_count,
        "total_nodes": total_nodes,
        "weak_points_count": len(profile.weak_points),
        "weak_points": [wp.knowledge_point for wp in profile.weak_points],
        "difficulty_level": profile.difficulty_level.value,
        "conversation_count": profile.conversation_count,
        "is_new_user": profile.is_new_user(),
        "radar": [
            {
                "category": cat,
                "mastery": round(
                    sum(profile.get_knowledge_mastery(nid) for nid in nids) / len(nids), 2
                ) if nids else 0,
            }
            for cat, nids in categories.items()
        ],
    }


@router.get("/{user_id}/changes")
async def get_recent_changes(user_id: str, limit: int = 20):
    """获取用户最近的画像变更记录（Redis历史）"""
    changes = profile_service.get_recent_changes(user_id, limit)
    return {"user_id": user_id, "changes": changes, "count": len(changes)}


@router.delete("/{user_id}")
async def delete_profile(user_id: str, db: Session = Depends(get_db)):
    """删除画像"""
    success = profile_service.delete_profile(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="画像不存在")
    return {"message": "画像删除成功"}

