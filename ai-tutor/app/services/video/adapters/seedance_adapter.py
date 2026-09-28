"""豆包 Seedance 视频生成适配器

异步任务模式：submitTask → pollTaskStatus → getResult
API文档: https://www.volcengine.com/docs/82379/1520758

创建任务: POST /api/v3/contents/generations/tasks
查询任务: GET  /api/v3/contents/generations/tasks/{id}

模型选择:
  - doubao-seedance-2-0-260128       标准版 (480p/720p/1080p, 支持原生音频)
  - doubao-seedance-2-0-fast-260128  快速版 (480p/720p, 更快)
  - doubao-seedance-1-5-pro-251215   1.5 Pro (支持原生音频)

任务状态: queued → running → succeeded / failed / expired / cancelled
视频URL有效期24小时，需及时下载或转存。
"""

import asyncio
import logging
import os

import httpx

from .base import VideoAdapter, VideoResult, ProviderCapabilities

logger = logging.getLogger(__name__)

SEEDANCE_BASE_URL = "https://ark.cn-beijing.volces.com"
POLL_INTERVAL = 5  # 轮询间隔(秒)
MAX_POLL_ATTEMPTS = 72  # 最多轮询6分钟(5s*72=360s)


class SeedanceAdapter(VideoAdapter):
    """豆包 Seedance 视频生成适配器"""

    def __init__(self):
        # 延迟读取环境变量（避免模块导入时dotenv还没加载）
        self._api_key = None
        self._model = None
        self._base_url = None

    def _ensure_config(self):
        """延迟加载配置（dotenv加载后再读取）"""
        if self._api_key is None:
            self._api_key = os.getenv("SEEDANCE_API_KEY", "")
            self._model = os.getenv("SEEDANCE_MODEL", "doubao-seedance-1-5-pro-251215")
            self._base_url = os.getenv("SEEDANCE_BASE_URL", SEEDANCE_BASE_URL)

    @property
    def provider_id(self) -> str:
        return "seedance"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_aspect_ratios=["16:9", "4:3", "1:1", "9:16", "3:4", "21:9"],
            supported_durations=[5, 10],
            supported_resolutions=["480p", "720p", "1080p"],
            max_duration=15,
            supports_audio=True,  # Seedance 2.0 / 1.5 Pro 支持原生音频
        )

    async def check_availability(self) -> bool:
        """检查API Key是否配置"""
        self._ensure_config()
        if not self._api_key:
            return False
        return True

    async def generate(self, prompt: str, **kwargs) -> VideoResult:
        """生成视频：提交任务 → 轮询直到完成"""
        self._ensure_config()
        options = self.normalize_options(**kwargs)
        aspect_ratio = options.get("aspect_ratio", "16:9")
        duration = options.get("duration", 10)
        resolution = options.get("resolution", "720p")
        generate_audio = options.get("generate_audio", True)

        # 1. 提交任务
        task_id = await self._submit_task(prompt, aspect_ratio, duration, resolution, generate_audio)
        logger.info("Seedance task submitted: %s (model=%s)", task_id, self._model)

        # 2. 轮询直到完成
        return await self._poll_until_done(task_id)

    async def _submit_task(
        self, prompt: str, aspect_ratio: str, duration: int, resolution: str, generate_audio: bool
    ) -> str:
        """提交视频生成任务，返回task_id

        API: POST /api/v3/contents/generations/tasks
        """
        # 清理 prompt 中的特殊字符（Seedance API 不允许某些字符）
        import re
        clean_prompt = re.sub(r'\{\{[^}]*\}\}', '', prompt)  # 移除未替换的模板变量
        clean_prompt = re.sub(r'\{[^}]*\}', '', clean_prompt)  # 移除花括号内容
        clean_prompt = clean_prompt.strip()
        if not clean_prompt:
            clean_prompt = f"Educational animation video, 10 seconds, visual only, no text"

        body = {
            "model": self._model,
            "content": [{"type": "text", "text": clean_prompt}],
            "ratio": aspect_ratio,
            "duration": duration,
            "resolution": resolution,
            "watermark": False,
            "generate_audio": generate_audio,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self._base_url}/api/v3/contents/generations/tasks",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
                json=body,
            )

        if resp.status_code != 200:
            raise RuntimeError(f"Seedance task submission failed ({resp.status_code}): {resp.text}")

        data = resp.json()
        task_id = data.get("id")
        if not task_id:
            raise RuntimeError(f"Seedance returned empty task ID: {data}")
        return task_id

    async def _poll_until_done(self, task_id: str) -> VideoResult:
        """轮询任务状态直到完成或失败

        API: GET /api/v3/contents/generations/tasks/{id}
        状态: queued / running / succeeded / failed / expired / cancelled
        成功响应:
        {
            "id": "cgt-xxx",
            "status": "succeeded",
            "content": {"video_url": "https://...mp4"},
            "duration": 5,
            "ratio": "16:9",
            "resolution": "720p",
            "generate_audio": true
        }
        """
        for attempt in range(MAX_POLL_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL)

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self._base_url}/api/v3/contents/generations/tasks/{task_id}",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )

            if resp.status_code != 200:
                logger.warning("Seedance poll failed (%d), retrying...", resp.status_code)
                continue

            data = resp.json()
            status = data.get("status", "")

            if status == "succeeded":
                content = data.get("content", {})
                video_url = content.get("video_url") if isinstance(content, dict) else None
                if not video_url:
                    raise RuntimeError("Seedance task succeeded but no video URL returned")
                has_audio = data.get("generate_audio", False)
                return VideoResult(
                    url=video_url,
                    duration=data.get("duration", 5),
                    width=self._estimate_width(data.get("ratio", "16:9"), data.get("resolution", "720p")),
                    height=self._estimate_height(data.get("resolution", "720p")),
                    provider=self.provider_id,
                    has_audio=has_audio,
                )

            if status == "failed":
                error_obj = data.get("error")
                error_msg = error_obj.get("message", str(error_obj)) if isinstance(error_obj, dict) else str(error_obj)
                raise RuntimeError(f"Seedance video generation failed: {error_msg}")

            if status == "expired":
                raise RuntimeError(f"Seedance task expired (task: {task_id})")

            if status == "cancelled":
                raise RuntimeError(f"Seedance task was cancelled (task: {task_id})")

            # queued or running, continue polling
            logger.debug("Seedance task %s status: %s (attempt %d/%d)", task_id, status, attempt + 1, MAX_POLL_ATTEMPTS)

        raise RuntimeError(f"Seedance video generation timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL}s (task: {task_id})")

    @staticmethod
    def _estimate_height(resolution: str) -> int:
        return {"480p": 480, "720p": 720, "1080p": 1080}.get(resolution, 720)

    @staticmethod
    def _estimate_width(ratio: str, resolution: str) -> int:
        h = SeedanceAdapter._estimate_height(resolution)
        parts = ratio.split(":")
        if len(parts) == 2:
            try:
                w, rh = int(parts[0]), int(parts[1])
                return round(h * w / rh)
            except ValueError:
                pass
        return round(h * 16 / 9)
