"""
智能生成 API - SSE 流式端点

POST /api/generate/stream
  接收用户自然语言需求 → DispatcherAgent分析 → 流式推送进度 → 产出视频等资源
"""
import json
import logging
import asyncio
import time
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.agents.dispatcher_agent import DispatcherAgent
from app.services.video_service import VideoService

logger = logging.getLogger(__name__)
router = APIRouter()

# 简单会话存储：追踪用户画像采集状态
_session_profiles: dict[str, dict] = {}

# 需要先了解用户水平的课程级意图关键词
_COURSE_INTENT_KW = ["速通", "系统学习", "三周", "两周", "一周", "期末复习", "从头", "入门到", "零基础", "如何学习"]


def _need_profile_check(query: str) -> bool:
    """判断是否需要先了解用户水平"""
    return any(kw in query for kw in _COURSE_INTENT_KW)


def _profile_questions(kp: str) -> str:
    """生成了解用户水平的引导问题"""
    return (
        f"好的！在帮你规划「{kp}」之前，我想先了解一下你的情况，这样才能给出最适合你的方案。\n\n"
        f"**1.** 你目前的基础怎么样？是零基础、有一点了解、还是已经学过一些了？\n"
        f"**2.** 你学习的目标是什么？应付考试、找实习、还是深入理解原理？\n"
        f"**3.** 你一般每天能花多长时间学习?\n\n"
        f"简单告诉我一下就好，我会根据你的回答来调整学习方案 😊"
    )


class GenerateRequest(BaseModel):
    query: str
    style: str = "rigorous"
    voice: str = ""
    user_id: str = "anonymous"
    # 新增：前端传递的画像信息（统一画像系统）
    profile_data: dict = {}  # 包含 base_level, study_goal, weak_points 等


async def event_generator(query: str, style: str, voice: str = "", user_id: str = "anonymous", profile_data: dict = {}) -> AsyncGenerator[dict, None]:
    """
    SSE 事件生成器：分析需求 → 调度资源 → 通知前端
    
    Args:
        query: 用户学习需求
        style: 视频风格
        voice: 语音选项
        user_id: 用户ID
        profile_data: 前端传递的画像信息（统一画像系统）
    """
    start_time = time.time()
    print(f"[SSE-DEBUG] event_generator STARTED query={query[:50]} user={user_id[:20]}", flush=True)

    # ═══ Step 0: 检查是否需要先了解用户水平 ═══
    print(f"[SSE-DEBUG] Step 0: checking profile for user={user_id[:20]}", flush=True)
    
    # 如果前端已经传递了画像信息，跳过 Step 0（统一画像系统）
    has_profile = profile_data and profile_data.get("phase") != "initial"
    print(f"[SSE-DEBUG] Step 0: has_profile={has_profile}, profile_data={profile_data}", flush=True)
    
    if has_profile:
        print(f"[SSE-DEBUG] Step 0: skipping profile check (frontend already has profile)", flush=True)
        # 直接进入 Step 1
    else:
        # 原有的画像采集逻辑（仅用于没有前端画像的情况）
        session = _session_profiles.get(user_id)
        print(f"[SSE-DEBUG] Step 0: session={session}, need_profile_check={_need_profile_check(query)}", flush=True)
        
        try:
            if session and session.get("awaiting_profile"):
                # 用户正在回答水平问题 → 提取信息并更新会话
                print(f"[SSE-DEBUG] Step 0: awaiting_profile=True, extracting profile", flush=True)
                profile_info = query.strip()
                session["profile_info"] = profile_info
                session["awaiting_profile"] = False
                
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "content": f"了解了！{profile_info[:50]}{'...' if len(profile_info) > 50 else ''}\n\n我来给你定制方案，请稍候~"
                    }, ensure_ascii=False)
                }
                print(f"[SSE-DEBUG] Step 0: yielded message event", flush=True)
                # 用原始知识点继续生成
                query = session.get("original_query", query)
            elif _need_profile_check(query) and (not session or not session.get("profiled")):
                # 首次课程级意图 → 先问水平
                print(f"[SSE-DEBUG] Step 0: need_profile_check=True, asking profile", flush=True)
                _session_profiles[user_id] = {
                    "awaiting_profile": True,
                    "original_query": query,
                    "profiled": False,
                }
                
                kp = query.strip()
                yield {
                    "event": "message",
                    "data": json.dumps({"content": _profile_questions(kp)}, ensure_ascii=False)
                }
                print(f"[SSE-DEBUG] Step 0: yielded message event (profile question)", flush=True)
                yield {
                    "event": "done",
                    "data": json.dumps({"resources": []}, ensure_ascii=False)
                }
                print(f"[SSE-DEBUG] Step 0: yielded done event, returning", flush=True)
                return
            else:
                print(f"[SSE-DEBUG] Step 0: skipping profile check", flush=True)
        except Exception as e:
            print(f"[SSE-DEBUG] Step 0 EXCEPTION: {e}", flush=True)
            logger.error("[SSE] Step 0 failed: %s", e, exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"message": f"初始化失败: {str(e)}"}, ensure_ascii=False)
            }
            return

    # ═══ Step 1: 分析需求 ═══
    logger.info("[SSE] Step 1: Analyzing query='%s'", query)
    yield {
        "event": "status",
        "data": json.dumps({
            "stage": "analyzing",
            "message": "正在分析学习需求，拆分知识点...",
            "progress": 10,
        }, ensure_ascii=False)
    }
    await asyncio.sleep(0.1)  # 确保事件发送

    try:
        logger.info("[SSE] Creating DispatcherAgent...")
        dispatcher = DispatcherAgent()
        logger.info("[SSE] Calling think...")
        plan = await dispatcher.think({"query": query})
        logger.info("[SSE] think done, plan tasks=%d", len(plan.tasks))
        logger.info("[SSE] Calling execute...")
        result = await dispatcher.execute(plan)
        logger.info("[SSE] execute done, resources=%d", len(result.resources))

        kp = result.data.get("knowledge_point", query)
        scope = result.data.get("scope", "single")
        resources = result.resources  # List[Dict]
        response_msg = result.data.get("message", "")
        logger.info("[SSE] kp=%s, scope=%s, has_video=%s", kp, scope, any(r["type"]=="video" for r in resources))

    except Exception as e:
        logger.error("[SSE] Dispatcher agent failed: %s", e, exc_info=True)
        yield {
            "event": "error",
            "data": json.dumps({"message": f"分析失败: {str(e)}"}, ensure_ascii=False)
        }
        return

    # ═══ Step 2: 返回分析结果 ═══
    yield {
        "event": "status",
        "data": json.dumps({
            "stage": "analyzing",
            "message": f"已识别：{kp}（{'系统课程' if scope == 'course' else '单知识点'}）",
            "progress": 30,
        }, ensure_ascii=False)
    }

    # 发送 AI 回复
    yield {
        "event": "message",
        "data": json.dumps({"content": response_msg}, ensure_ascii=False)
    }

    # 发送资源列表
    for res in resources:
        yield {
            "event": "resource",
            "data": json.dumps({
                "id": res.get("id", ""),
                "type": res.get("type", ""),
                "title": res.get("title", ""),
                "description": res.get("description", ""),
                "status": res.get("status", "queued"),
            }, ensure_ascii=False)
        }

    # ═══ Step 3: 生成视频（实时进度推送） ═══
    has_video = any(r["type"] == "video" for r in resources)

    if has_video:
        try:
            vs = VideoService()

            # 先启动视频生成，立即获取 task_id
            task_id = vs.start_video_generation(kp, style, voice)
            logger.info("[SSE] Video generation started, task_id=%s", task_id)

            # 立即发送 task_id，让前端开始轮询（不依赖 SSE while 循环）
            yield {
                "event": "status",
                "data": json.dumps({
                    "stage": "generating",
                    "message": "正在启动视频生成...",
                    "progress": 45,
                    "task_id": task_id,  # 关键：立即发送 task_id
                }, ensure_ascii=False)
            }
            await asyncio.sleep(0.1)

            # 实时进度轮询：每2秒查询一次 Redis 进度
            max_wait_time = 600  # 最长等待10分钟
            start_time = asyncio.get_event_loop().time()

            while True:
                await asyncio.sleep(2)  # 每2秒查询一次

                # 检查是否超时
                elapsed_time = asyncio.get_event_loop().time() - start_time
                if elapsed_time > max_wait_time:
                    logger.error("[SSE] Video generation timeout after %d seconds", max_wait_time)
                    yield {
                        "event": "status",
                        "data": json.dumps({
                            "stage": "error",
                            "message": f"视频生成超时（{max_wait_time}秒），请重试",
                            "progress": 80,
                        }, ensure_ascii=False)
                    }
                    yield {
                        "event": "done",
                        "data": json.dumps({"resources": []}, ensure_ascii=False)
                    }
                    return

                # 查询实时进度（从 Redis）
                task_status = vs.get_video_task_status(task_id)
                if not task_status:
                    logger.warning("[SSE] Task status not found: %s", task_id)
                    continue

                status = task_status.get("status", "")
                progress = task_status.get("progress", 0)
                message = task_status.get("message", "视频生成中...")

                logger.info("[SSE] Task %s: status=%s, progress=%d, message=%s", task_id, status, progress, message)

                # 推送实时进度
                yield {
                    "event": "status",
                    "data": json.dumps({
                        "stage": "generating",
                        "message": message,
                        "progress": 45 + int(progress * 0.35),  # 进度映射到 45-80
                        "task_id": task_id,
                    }, ensure_ascii=False)
                }

                # 检查是否完成或失败
                if status == "completed":
                    video_url = task_status.get("video_url", "")
                    logger.info("[SSE] Video generation completed, url=%s", video_url)

                    # 更新资源状态
                    yield {
                        "event": "status",
                        "data": json.dumps({
                            "stage": "rendering",
                            "message": "视频生成完毕！",
                            "progress": 80,
                        }, ensure_ascii=False)
                    }

                    yield {
                        "event": "resource",
                        "data": json.dumps({
                            "id": f"video_{kp}",
                            "type": "video",
                            "title": resources[0].get("title", f"【视频】{kp}"),
                            "description": resources[0].get("description", ""),
                            "status": "ready",
                            "url": video_url,
                        }, ensure_ascii=False)
                    }

                    yield {
                        "event": "status",
                        "data": json.dumps({
                            "stage": "done",
                            "message": "视频生成完毕！",
                            "progress": 100,
                        }, ensure_ascii=False)
                    }
                    break

                elif status in ("failed", "manim_not_available", "remotion_not_available", "remotion_failed"):
                    logger.error("[SSE] Video generation failed: %s", status)
                    yield {
                        "event": "status",
                        "data": json.dumps({
                            "stage": "error",
                            "message": f"视频生成失败：{message}",
                            "progress": 80,
                        }, ensure_ascii=False)
                    }
                    yield {
                        "event": "done",
                        "data": json.dumps({"resources": []}, ensure_ascii=False)
                    }
                    return

        except Exception as e:
            logger.error("[SSE] Video generation exception: %s", e, exc_info=True)
            yield {
                "event": "status",
                "data": json.dumps({
                    "stage": "error",
                    "message": f"视频生成出错: {str(e)}",
                    "progress": 80,
                }, ensure_ascii=False)
            }
            # 发送 done 事件，让前端知道流程已结束
            yield {
                "event": "done",
                "data": json.dumps({"resources": []}, ensure_ascii=False)
            }
            return

    # ═══ Done ═══
    elapsed = time.time() - start_time
    yield {
        "event": "status",
        "data": json.dumps({
            "stage": "done",
            "message": f"所有内容生成完毕！（耗时 {elapsed:.1f}s）",
            "progress": 100,
        }, ensure_ascii=False)
    }

    yield {
        "event": "done",
        "data": json.dumps({"resources": resources}, ensure_ascii=False)
    }


@router.get("/video-status/{task_id}")
async def video_status(task_id: str):
    """轮询视频生成进度端点
    
    前端每 2 秒轮询此端点获取实时进度。
    返回：{status, progress, message, video_url}
    """
    vs = VideoService()
    task = vs.get_video_task_status(task_id)
    if not task:
        return {"status": "not_found", "progress": 0, "message": "任务未找到", "video_url": ""}
    return task


@router.post("/stream")
async def generate_stream(request: GenerateRequest):
    """智能生成 SSE 流式端点
    
    Args:
        request: 包含 query, style, voice, user_id, profile_data
    """
    return EventSourceResponse(
        event_generator(
            request.query, 
            request.style, 
            request.voice, 
            request.user_id,
            request.profile_data  # 传递前端画像信息
        )
    )
