"""对话接口 - Orchestrator编排 + SSE流式输出

对照 AI开发指南_产品内核与架构规范.md：
- Orchestrator为系统中枢神经，统一调度Agent
- 所有Agent共享ExecutionContext，不自己开DB连接
- SSE流式输出 + 状态条可视化 + DAG流程图
- 保留非流式端点用于向后兼容
"""

from __future__ import annotations
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.services.profile_service import profile_service

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    """对话请求"""
    user_id: str
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """对话响应"""
    user_id: str
    reply: str
    agent_calls: list = []
    status_bar: list = []
    dag: dict = {"nodes": [], "edges": []}


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """对话接口 - 使用Orchestrator编排（非流式，向后兼容）"""
    from app.core.orchestrator import orchestrator

    t0 = time.time()

    # 获取画像
    profile = profile_service.get_profile(db, request.user_id)

    # 获取对话历史
    dialogue_history = []
    if request.conversation_id:
        conversations = profile_service.get_conversations(
            db, request.user_id, request.conversation_id, limit=20
        )
        if conversations:
            dialogue_history = [
                {"role": c["role"], "content": c["content"]}
                for c in conversations
            ]

    # 通过Orchestrator编排，收集所有事件
    full_response = ""
    agent_calls = []
    dag = {"nodes": [], "edges": []}
    status_bar = []

    async for event in orchestrator.handle_message(
        user_input=request.message,
        db=db,
        user_id=request.user_id,
        profile=profile,
        dialogue_history=dialogue_history,
    ):
        evt = event.get("event", "")
        try:
            data = json.loads(event.get("data", "{}"))
        except (json.JSONDecodeError, TypeError):
            data = {}

        if evt == "message":
            full_response += data.get("content", "")
        elif evt == "agent_status":
            status_bar.append(data)
        elif evt == "agent_result":
            agent_calls.append(data.get("agent", ""))
        elif evt == "dag":
            dag = data

    # 保存对话记录
    if request.conversation_id and full_response:
        profile_service.save_conversation(
            db, request.user_id, request.conversation_id, "user", request.message
        )
        profile_service.save_conversation(
            db, request.user_id, request.conversation_id, "assistant", full_response
        )
        profile_service.increment_conversation_count(db, request.user_id)

    # 协同决策审计日志（失败不影响主流程）
    try:
        from app.services.audit_service import record_decision
        record_decision({
            "user_id": request.user_id,
            "message": request.message[:200],
            "agent_calls": agent_calls,
            "dag_nodes": len(dag.get("nodes", [])),
            "dag_edges": len(dag.get("edges", [])),
            "reply_length": len(full_response),
            "latency_s": round(time.time() - t0, 2),
            "success": True,
        })
    except Exception as e:
        logger.warning(f"审计记录失败: {e}")

    return ChatResponse(
        user_id=request.user_id,
        reply=full_response,
        agent_calls=agent_calls,
        status_bar=status_bar,
        dag=dag,
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    """SSE流式对话 - 使用Orchestrator编排

    对照 AI开发指南_产品内核与架构规范.md 第4.1节：
    - Orchestrator是中枢神经，不是Agent
    - 能同时调度多个Agent（不是if/elif选一个）
    - 能处理Agent间的数据依赖
    - 能决定回复策略
    """
    from app.core.orchestrator import orchestrator

    # 获取画像
    profile = profile_service.get_profile(db, request.user_id)

    # 获取对话历史
    dialogue_history = []
    if request.conversation_id:
        conversations = profile_service.get_conversations(
            db, request.user_id, request.conversation_id, limit=20
        )
        if conversations:
            dialogue_history = [
                {"role": c["role"], "content": c["content"]}
                for c in conversations
            ]

    async def event_generator():
        full_response = ""
        try:
            async for event in orchestrator.handle_message(
                user_input=request.message,
                db=db,
                user_id=request.user_id,
                profile=profile,
                dialogue_history=dialogue_history,
            ):
                # 收集message事件中的内容用于保存对话
                if event.get("event") == "message":
                    try:
                        data = json.loads(event["data"])
                        full_response += data.get("content", "")
                    except (json.JSONDecodeError, KeyError):
                        pass
                yield event

            # 保存对话
            if request.conversation_id and full_response:
                profile_service.save_conversation(
                    db, request.user_id, request.conversation_id, "user", request.message
                )
                profile_service.save_conversation(
                    db, request.user_id, request.conversation_id, "assistant", full_response
                )
                profile_service.increment_conversation_count(db, request.user_id)

        except Exception as e:
            logger.error(f"SSE流式对话异常: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"message": f"服务异常: {str(e)}"}, ensure_ascii=False)
            }

    return EventSourceResponse(event_generator())
