"""GLM 代理路由 — SSE 流式 + JSON 同步"""

import os
import asyncio
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..database import get_db
from ..models import User
from ..auth import get_current_user_optional  # ★ 使用可选认证
from ..schemas import ChatReq

router = APIRouter()

GLM_API_KEY = os.getenv("GLM_API_KEY", "")
GLM_MODEL = os.getenv("GLM_MODEL", "deepseek-v4-flash")
GLM_BASE_URL = os.getenv("GLM_BASE_URL", "https://api.deepseek.com")

# 全局并发控制
_semaphore = asyncio.Semaphore(2)

# [DEBUG-glm] 文件日志 — 诊断智能体失败
_debug_logger = logging.getLogger("glm_debug")
_debug_logger.setLevel(logging.DEBUG)
# 使用相对路径（Docker 容器会映射到 /app/logs）
_log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
os.makedirs(_log_dir, exist_ok=True)
_fh = logging.FileHandler(os.path.join(_log_dir, "glm_debug.log"), encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
_debug_logger.addHandler(_fh)
_debug_logger.propagate = False

import httpx


@router.post("/chat")
async def chat_stream(
    request: Request,
    req: ChatReq,
    user: User = Depends(get_current_user_optional),
):
    """SSE 流式代理 — 将前端请求转发给 DeepSeek API"""
    req_id = f"{datetime.now().strftime('%H:%M:%S')}-{id(req):x}"
    msg_preview = (req.messages[-1].content[:80] + "...") if req.messages and req.messages[-1].content else "(empty)"
    _debug_logger.debug(f"[{req_id}] /chat START user={user.username if user else 'None'} model={req.model} max_tokens={req.max_tokens} msg_preview={msg_preview}")

    async def generate():
        try:
            async with _semaphore:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {GLM_API_KEY}",
                }
                payload = {
                    "model": req.model or GLM_MODEL,
                    "messages": [m.model_dump() for m in req.messages],
                    "stream": True,
                    "temperature": req.temperature,
                    "max_tokens": req.max_tokens,
                }

                async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
                    async with client.stream(
                        "POST",
                        f"{GLM_BASE_URL}/chat/completions",
                        headers=headers,
                        json=payload,
                    ) as resp:
                        if resp.status_code != 200:
                            error_body = await resp.aread()
                            err_msg = error_body.decode()[:200]
                            _debug_logger.error(f"[{req_id}] DeepSeek status={resp.status_code} error={err_msg}")
                            yield f"data: {json.dumps({'error': {'message': err_msg, 'status': resp.status_code}})}\n\n"
                            return

                        _debug_logger.debug(f"[{req_id}] DeepSeek 200 OK, streaming...")
                        chunk_count = 0
                        content_len = 0
                        async for line in resp.aiter_lines():
                            if line.strip():
                                chunk_count += 1
                                if line.startswith("data: ") and line != "data: [DONE]":
                                    try:
                                        c = json.loads(line[6:])
                                        delta = c.get("choices", [{}])[0].get("delta", {})
                                        content_len += len(delta.get("content") or "")
                                    except Exception:
                                        pass
                                yield f"{line}\n\n"
                        _debug_logger.debug(f"[{req_id}] Stream done: {chunk_count} chunks, content_len={content_len}")
        except asyncio.TimeoutError:
            _debug_logger.error(f"[{req_id}] TIMEOUT (120s)")
            yield f"data: {json.dumps({'error': {'message': 'Backend timeout', 'status': 504}})}\n\n"
        except Exception as e:
            _debug_logger.error(f"[{req_id}] EXCEPTION: {type(e).__name__}: {e}")
            yield f"data: {json.dumps({'error': {'message': str(e), 'status': 500}})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/chat-sync")
async def chat_sync(
    req: ChatReq,
    user: User = Depends(get_current_user_optional),
):
    """JSON 同步代理 — 等待完整响应返回"""
    async with _semaphore:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GLM_API_KEY}",
        }
        payload = {
            "model": req.model or GLM_MODEL,
            "messages": [m.model_dump() for m in req.messages],
            "stream": False,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            resp = await client.post(
                f"{GLM_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            return resp.json()
