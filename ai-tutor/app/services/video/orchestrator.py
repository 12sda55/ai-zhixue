"""视频生成调度器

架构设计（借鉴 OpenMAIC）：
- Manim/Remotion 为主力：LLM生成脚本→程序化渲染→TTS旁白→拼接，1-3分钟教学视频

两阶段管线（借鉴 OpenMAIC pipeline-runner.ts）：
  Stage 1: 知识点 → Skill 推断
  Stage 2: LLM生成讲解脚本 → LLM生成Manim代码 → 渲染 → TTS → 拼接
"""

import asyncio
import logging
from typing import Optional

from .adapters import FALLBACK_CHAIN, ADAPTERS
from .adapters.base import VideoAdapter, VideoResult
from .task_manager import video_task_manager
from .skills import (
    VideoSkill,
    infer_skill,
    get_skill_template_id,
    get_skill_recommended_duration,
)

logger = logging.getLogger(__name__)


def _get_knowledge_details(kp_id: str) -> dict:
    """从知识缓存获取知识点详情"""
    try:
        from app.core.knowledge_cache import knowledge_cache
        node = knowledge_cache.get_node(kp_id)
        if node:
            deps = knowledge_cache.get_dependencies(kp_id) or []
            dep_names = []
            for dep_id in deps:
                dep_node = knowledge_cache.get_node(dep_id)
                if dep_node:
                    dep_names.append(dep_node.get("name", dep_id))
            return {
                "name": node.get("name", kp_id),
                "category": node.get("category", ""),
                "description": node.get("description", ""),
                "dependencies": ", ".join(dep_names) if dep_names else "",
            }
    except Exception as e:
        logger.debug("Failed to get knowledge details for %s: %s", kp_id, e)

    return {"name": kp_id, "category": "", "description": "", "dependencies": ""}


class VideoOrchestrator:
    """视频生成调度器 - Manim/Remotion 管线"""

    def __init__(self):
        self._adapters: dict[str, VideoAdapter] = {}
        for provider_id, adapter_cls in ADAPTERS.items():
            self._adapters[provider_id] = adapter_cls()

    async def get_available_providers(self) -> list[str]:
        """获取当前可用的Provider列表"""
        available = []
        for provider_id in FALLBACK_CHAIN:
            adapter = self._adapters.get(provider_id)
            if adapter and await adapter.check_availability():
                available.append(provider_id)
        return available

    async def generate_with_fallback(
        self,
        kp_id: str,
        kp_name: str,
        user_id: str,
        style: str = "relaxed",
        preferred_provider: Optional[str] = None,
    ) -> dict:
        """生成教学视频（Manim/Remotion 管线）

        Returns:
            dict with task_id for async tracking
        """
        # 创建任务
        task_id = video_task_manager.create_task(user_id, kp_id, preferred_provider or "manim")

        # 在后台执行生成
        asyncio.create_task(
            self._run_generation(task_id, kp_id, kp_name, style, preferred_provider)
        )

        return {"task_id": task_id, "status": "pending"}

    async def _run_generation(
        self,
        task_id: str,
        kp_id: str,
        kp_name: str,
        style: str,
        preferred_provider: Optional[str],
    ):
        """实际执行视频生成（后台任务）"""
        # 获取知识点详情
        kp_details = _get_knowledge_details(kp_id)
        effective_name = kp_details.get("name") or kp_name or kp_id

        # 构建降级链
        chain = list(FALLBACK_CHAIN)
        if preferred_provider and preferred_provider in chain:
            chain.remove(preferred_provider)
            chain.insert(0, preferred_provider)

        for provider_id in chain:
            adapter = self._adapters.get(provider_id)
            if not adapter:
                continue

            if not await adapter.check_availability():
                logger.info("Provider %s not available, skipping", provider_id)
                continue

            try:
                video_task_manager.mark_running(task_id, provider=provider_id)
                logger.info("Generating video for %s with %s", kp_id, provider_id)

                # Manim 完整管线：LLM生成讲解脚本 → Manim代码 → 渲染 → TTS → 拼接
                result = await self._generate_with_manim(task_id, kp_id, effective_name, style)

                video_task_manager.mark_done(task_id, result.url, result.duration)
                logger.info("Video generated for %s with %s: %s", kp_id, provider_id, result.url)
                return

            except Exception as e:
                logger.warning("Provider %s failed for %s: %s", provider_id, kp_id, e)
                video_task_manager.mark_failed(task_id, str(e))
                continue

        # 所有Provider都失败
        video_task_manager.mark_failed(task_id, f"All providers failed for {kp_id}")
        logger.error("All providers failed for %s", kp_id)

    async def _generate_with_manim(self, task_id: str, kp_id: str, kp_name: str, style: str) -> VideoResult:
        """使用 Manim/Remotion 完整管线生成教学视频

        在线程池中运行同步的 generate_concept_video，通过 progress_callback 实时更新进度。
        """
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        from app.services.video_service import video_service

        loop = asyncio.get_event_loop()
        result_holder = {}

        def _progress_callback(progress: int, message: str):
            """同步回调：将进度更新到 video_task_manager"""
            video_task_manager.update_status(task_id, "running", progress=progress, message=message)

        def _run_sync():
            try:
                result = video_service.generate_concept_video(
                    kp_id, style=style, progress_callback=_progress_callback
                )
                result_holder["result"] = result
            except Exception as e:
                result_holder["error"] = e

        # 在线程池中启动同步渲染
        with ThreadPoolExecutor(max_workers=1) as pool:
            await loop.run_in_executor(pool, _run_sync)

        if "error" in result_holder:
            raise result_holder["error"]

        result = result_holder["result"]
        if result.get("status") != "completed":
            raise RuntimeError(f"Manim generation failed: {result.get('message', '')}")

        return VideoResult(
            url=result.get("video_url", ""),
            duration=result.get("duration", 0),
            width=1280,
            height=720,
            provider="manim",
            has_audio=result.get("has_audio", False),
        )

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """查询任务状态"""
        return video_task_manager.get_task(task_id)

    def get_user_tasks(self, user_id: str) -> list:
        """查询用户所有任务"""
        return video_task_manager.get_user_tasks(user_id)

    async def retry_task(self, task_id: str) -> Optional[dict]:
        """重试失败的任务"""
        task = video_task_manager.get_task(task_id)
        if not task or task["status"] != "failed":
            return None

        kp_details = _get_knowledge_details(task["kp_id"])

        return await self.generate_with_fallback(
            kp_id=task["kp_id"],
            kp_name=kp_details.get("name", task["kp_id"]),
            user_id=task["user_id"],
            preferred_provider=task.get("provider"),
        )


# 全局单例
video_orchestrator = VideoOrchestrator()
