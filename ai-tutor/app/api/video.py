"""视频生成API接口 - Manim/Remotion 程序化渲染 + 异步任务 + Skills系统

管线：Manim/Remotion（LLM生成脚本→程序化渲染→TTS旁白→拼接）
- POST /generate - 异步生成概念讲解视频（立即返回task_id）
- GET /task/{task_id} - 查询视频生成任务状态（轮询）
- DELETE /task/{task_id} - 删除任务记录和视频文件
- GET /tasks - 查询用户所有任务
- POST /task/{task_id}/retry - 重试失败任务
- GET /providers - 查询可用Provider列表
- GET /skills - 查询视频Skills类型列表
- GET /skill/{kp_id} - 查询知识点对应的Skill
- GET /list - 列出可用视频
- DELETE /video/{video_id} - 删除本地视频文件
- GET /play/{video_id} - 获取视频播放URL
- POST /tts - 单独生成TTS音频（用于测试）
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.video_service import video_service, VIDEO_OUTPUT_DIR
from app.services.video import video_orchestrator, video_task_manager
from app.services.video.adapters import FALLBACK_CHAIN
from app.services.video.skills import VideoSkill, infer_skill, get_skill_template_id, get_skill_recommended_duration

logger = logging.getLogger(__name__)
router = APIRouter()


class VideoGenerateRequest(BaseModel):
    """视频生成请求"""
    knowledge_point: str = Field(..., description="知识点ID，如 bubble_sort, bst")
    style: str = Field(default="relaxed", description="讲解风格: rigorous/relaxed/guided")
    with_tts: bool = Field(default=True, description="是否生成TTS旁白")
    user_id: str = Field(default="anonymous", description="用户ID")
    provider: Optional[str] = Field(default=None, description="指定Provider: manim")


class TTSRequest(BaseModel):
    """TTS测试请求"""
    text: str = Field(..., description="要合成的文本")
    voice: str = Field(default="xiaoyan", description="语音角色: xiaoyan/xiaoyu/xiaofeng")
    speed: int = Field(default=50, ge=0, le=100, description="语速 0-100")


@router.post("/generate")
async def generate_video(request: VideoGenerateRequest):
    """异步生成概念讲解视频（Manim/Remotion 管线）

    立即返回task_id，渲染在后台执行。
    通过 GET /task/{task_id} 轮询进度。
    """
    # 先检查缓存
    cached = video_service.get_cached_video(request.knowledge_point, request.style)
    if cached:
        # ★ 关键修复：缓存命中时创建新的 task 记录并标记为 done
        # 否则返回的旧 task_id 可能已过 Redis TTL（24h），前端轮询会 404
        cached_video_url = cached.get("video_url", "")
        new_task_id = video_task_manager.create_task(
            user_id=request.user_id,
            kp_id=request.knowledge_point,
            provider="manim",
        )
        video_task_manager.mark_done(new_task_id, cached_video_url)
        logger.info("[VIDEO CACHE HIT] kp=%s, created new task_id=%s -> cached_url=%s",
                    request.knowledge_point, new_task_id, cached_video_url)
        return {
            "task_id": new_task_id,
            "status": "completed",
            "message": "视频已缓存，直接返回",
            "video_url": cached_video_url,
        }

    # 通过 Orchestrator 提交任务（降级链）
    result = await video_orchestrator.generate_with_fallback(
        kp_id=request.knowledge_point,
        kp_name=request.knowledge_point,
        user_id=request.user_id,
        style=request.style,
        preferred_provider=request.provider,
    )

    return {
        "task_id": result["task_id"],
        "status": result["status"],
        "message": "视频生成已提交，通过 GET /task/{task_id} 查询进度",
    }


@router.get("/task/{task_id}")
async def get_video_task(task_id: str):
    """查询视频生成任务状态

    返回: { task_id, status, progress, video_url?, error? }
    status: pending / running / done / failed
    """
    task = video_task_manager.get_task(task_id)
    if not task:
        # 兼容旧接口：查 video_service 的任务
        old_task = video_service.get_video_task_status(task_id)
        if old_task:
            return old_task
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.get("/tasks")
async def get_user_tasks(user_id: str = Query(..., description="用户ID")):
    """查询用户所有视频生成任务"""
    tasks = video_task_manager.get_user_tasks(user_id)
    return {"status": "ok", "tasks": tasks}


@router.post("/task/{task_id}/retry")
async def retry_video_task(task_id: str):
    """重试失败的视频生成任务"""
    result = await video_orchestrator.retry_task(task_id)
    if not result:
        raise HTTPException(status_code=400, detail="任务不存在或不可重试")
    return {
        "task_id": result["task_id"],
        "status": result["status"],
        "message": "重试已提交",
    }


@router.delete("/task/{task_id}")
async def delete_video_task(task_id: str):
    """删除视频生成任务记录

    只能删除已完成(done)或失败(failed)的任务。
    正在进行的任务不允许删除。
    """
    task = video_task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.get("status") in ("pending", "running"):
        raise HTTPException(status_code=400, detail="正在进行的任务不允许删除，请等待完成")

    # 删除任务记录
    deleted = video_task_manager.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=400, detail="删除失败")

    # 如果是本地视频（Manim生成的），同时删除视频文件
    video_url = task.get("video_url", "")
    if video_url and "/static/videos/" in video_url:
        filename = video_url.split("/static/videos/")[-1]
        video_path = os.path.join(VIDEO_OUTPUT_DIR, filename)
        if os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError:
                pass

    return {"status": "ok", "message": "任务已删除", "task_id": task_id}


@router.delete("/video/{video_id}")
async def delete_video_file(video_id: str):
    """删除本地视频文件（Manim生成的视频）"""
    deleted_files = []
    for filename in os.listdir(VIDEO_OUTPUT_DIR):
        if filename.endswith(".mp4") and video_id in filename:
            video_path = os.path.join(VIDEO_OUTPUT_DIR, filename)
            try:
                os.remove(video_path)
                deleted_files.append(filename)
            except OSError:
                pass

    if not deleted_files:
        return {"status": "ok", "message": f"未找到视频 {video_id}"}

    return {"status": "ok", "message": f"已删除 {len(deleted_files)} 个视频文件", "deleted": deleted_files}


@router.get("/providers")
async def get_providers():
    """查询可用的视频生成Provider列表"""
    available = await video_orchestrator.get_available_providers()
    from app.services.video.adapters import FALLBACK_CHAIN
    return {
        "status": "ok",
        "available": available,
        "fallback_chain": FALLBACK_CHAIN,
    }


@router.get("/skills")
async def get_skills():
    """查询视频Skills类型列表"""
    from app.services.video.prompt_loader import list_templates
    return {
        "status": "ok",
        "skills": [
            {
                "id": skill.value,
                "name": {
                    "concept-explanation": "概念讲解",
                    "algorithm-demo": "算法演示",
                    "data-structure-visual": "数据结构可视化",
                    "comparison": "对比分析",
                    "step-by-step": "步骤演示",
                }.get(skill.value, skill.value),
                "template": get_skill_template_id(skill),
                "recommended_duration": get_skill_recommended_duration(skill, "manim"),
            }
            for skill in VideoSkill
        ],
        "fallback_chain": list(FALLBACK_CHAIN),
        "architecture": {
            "primary": "manim",
            "primary_desc": "Manim/Remotion 程序化渲染，1-3分钟教学视频，质量可控",
        },
    }


@router.get("/skill/{kp_id}")
async def get_skill_for_kp(kp_id: str):
    """查询知识点对应的Skill类型和推荐参数"""
    # 尝试获取知识点分类
    category = ""
    kp_name = kp_id
    try:
        from app.core.knowledge_cache import knowledge_cache
        node = knowledge_cache.get_node(kp_id)
        if node:
            category = node.get("category", "")
            kp_name = node.get("name", kp_id)
    except Exception:
        pass

    skill = infer_skill(kp_id, category)
    return {
        "status": "ok",
        "kp_id": kp_id,
        "kp_name": kp_name,
        "category": category,
        "skill": skill.value,
        "template": get_skill_template_id(skill),
        "recommended_duration": get_skill_recommended_duration(skill, "manim"),
    }


@router.get("/status/{video_id}")
async def get_video_status(video_id: str):
    """查询视频生成状态（兼容旧接口）"""
    task_status = video_service.get_task_status(video_id)
    if task_status:
        return {"status": "ok", "result": task_status}
    return {"status": "ok", "result": {"task_id": video_id, "status": "not_found"}}


@router.get("/list")
async def list_videos(knowledge_point: Optional[str] = Query(None)):
    """列出可用视频"""
    videos = video_service.list_available_videos()
    if knowledge_point:
        videos = [v for v in videos if v.get("knowledge_point") == knowledge_point]
    return {"status": "ok", "videos": videos}


@router.get("/play/{video_id}")
async def play_video(video_id: str):
    """获取视频播放URL"""
    for filename in os.listdir(VIDEO_OUTPUT_DIR):
        if filename.endswith(".mp4") and video_id in filename:
            video_path = os.path.join(VIDEO_OUTPUT_DIR, filename)
            return FileResponse(
                video_path,
                media_type="video/mp4",
                filename=filename,
            )
    return {"status": "error", "message": f"视频 {video_id} 不存在"}


@router.post("/tts")
async def generate_tts(request: TTSRequest):
    """单独生成TTS音频（用于测试）"""
    from app.services.tts_service import tts_service

    if not tts_service.available:
        return {
            "status": "ok",
            "message": "讯飞TTS未配置，请设置 IFLYTEK_APP_ID/IFLYTEK_API_KEY/IFLYTEK_API_SECRET",
            "audio_url": "",
        }

    audio_path = video_service.generate_tts_audio(
        text=request.text,
        voice=request.voice,
        speed=request.speed,
    )

    if audio_path and os.path.exists(audio_path):
        return {
            "status": "ok",
            "audio_url": f"/static/videos/{os.path.basename(audio_path)}",
            "audio_path": audio_path,
        }

    return {"status": "ok", "message": "TTS生成失败", "audio_url": ""}


@router.get("/templates")
async def list_templates():
    """列出可用的Manim模板"""
    from app.knowledge.manim_templates import list_available_templates
    templates = list_available_templates()
    return {"status": "ok", "templates": templates}


@router.get("/script/{knowledge_point}")
async def get_manim_script(knowledge_point: str, style: str = Query("rigorous")):
    """获取知识点的Manim脚本（不渲染）"""
    script = video_service.generate_manim_script(knowledge_point, style)
    return {
        "status": "ok",
        "knowledge_point": knowledge_point,
        "style": style,
        "script": script,
        "manim_available": video_service.manim_available,
        "ffmpeg_available": video_service.ffmpeg_available,
    }
