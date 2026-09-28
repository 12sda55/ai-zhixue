"""Manim/Remotion 视频生成适配器

封装 Manim + Remotion 降级渲染逻辑。
- Manim: 程序化动画引擎，需要 LaTeX + Cairo + FFmpeg
- Remotion: React 视频框架，Windows 降级方案

Manim 不可用时自动降级到 Remotion（需要 remotion-service 运行在 localhost:3000）
"""

import logging
import os
import shutil
import uuid

from .base import VideoAdapter, VideoResult, ProviderCapabilities

logger = logging.getLogger(__name__)


class ManimAdapter(VideoAdapter):
    """Manim/Remotion 程序化动画适配器

    主力视频生成方案：LLM生成脚本→程序化渲染→TTS旁白→拼接
    产出1-3分钟完整教学视频，质量可控
    """

    def __init__(self):
        self._manim_available = self._check_manim()
        self._remotion_available = self._check_remotion()

    @property
    def provider_id(self) -> str:
        return "manim"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_aspect_ratios=["16:9"],
            supported_durations=[30, 60, 90, 120],
            supported_resolutions=["720p", "1080p"],
            max_duration=180,  # 最长3分钟
            supports_audio=True,  # 通过TTS后处理添加音频
        )

    async def check_availability(self) -> bool:
        """Manim 或 Remotion 任一可用即可"""
        return self._manim_available or self._remotion_available

    async def generate(self, prompt: str, **kwargs) -> VideoResult:
        """使用 Manim/Remotion 生成视频

        注意：此适配器主要在 VideoOrchestrator 中被调用，
        Orchestrator 会先调用 LLM 生成脚本，再通过 video_service 完整管线渲染。
        此方法仅作为直接调用入口。
        """
        script = kwargs.get("manim_script", "")
        scene_class = kwargs.get("scene_class", "")
        output_dir = kwargs.get("output_dir", "")

        if not script or not scene_class:
            raise ValueError("ManimAdapter requires manim_script and scene_class parameters")

        if not self._manim_available and not self._remotion_available:
            raise RuntimeError("Neither Manim nor Remotion is available")

        result = self._render_video(script, scene_class, output_dir)
        if result.get("status") != "completed":
            raise RuntimeError(f"Rendering failed: {result.get('message', 'Unknown error')}")

        return VideoResult(
            url=result.get("video_url", ""),
            duration=result.get("duration", 0),
            width=1280,
            height=720,
            provider=self.provider_id,
            has_audio=result.get("has_audio", False),
        )

    def _render_video(self, script: str, scene_class: str, output_dir: str) -> dict:
        """渲染视频：Manim 优先，Remotion 降级"""
        from app.services.video_service import VIDEO_OUTPUT_DIR

        if not output_dir:
            output_dir = VIDEO_OUTPUT_DIR

        os.makedirs(output_dir, exist_ok=True)

        # Manim 可用则用 Manim
        if self._manim_available:
            return self._render_with_manim(script, scene_class, output_dir)

        # 降级到 Remotion
        if self._remotion_available:
            return self._render_with_remotion(script, scene_class, output_dir)

        return {"status": "failed", "message": "Neither Manim nor Remotion is available"}

    def _render_with_manim(self, script: str, scene_class: str, output_dir: str) -> dict:
        """使用 Manim 渲染"""
        task_id = str(uuid.uuid4())[:8]
        script_dir = os.path.join(output_dir, f"tmp_{task_id}")
        os.makedirs(script_dir, exist_ok=True)
        script_path = os.path.join(script_dir, f"{scene_class}.py")

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)

        try:
            video_path = self._render_with_manim_api(script, script_dir, scene_class)

            if video_path is None:
                # Manim 渲染失败，尝试 Remotion 降级
                shutil.rmtree(script_dir, ignore_errors=True)
                if self._remotion_available:
                    return self._render_with_remotion(script, scene_class, output_dir)
                return {"status": "failed", "message": "Manim rendering returned no output"}

            final_name = f"{scene_class}_{task_id}.mp4"
            final_path = os.path.join(output_dir, final_name)
            shutil.move(video_path, final_path)
            shutil.rmtree(script_dir, ignore_errors=True)

            return {
                "status": "completed",
                "video_path": final_path,
                "video_url": f"/static/videos/{final_name}",
            }
        except Exception as e:
            logger.error("Manim rendering error: %s", e)
            shutil.rmtree(script_dir, ignore_errors=True)
            # 降级到 Remotion
            if self._remotion_available:
                return self._render_with_remotion(script, scene_class, output_dir)
            return {"status": "failed", "message": str(e)}

    def _render_with_manim_api(self, script: str, script_dir: str, scene_class: str):
        """使用 Manim Python API 渲染"""
        try:
            import importlib.util
            import sys

            spec = importlib.util.spec_from_file_location("manim_scene", os.path.join(script_dir, f"{scene_class}.py"))
            module = importlib.util.module_from_spec(spec)
            sys.modules["manim_scene"] = module
            spec.loader.exec_module(module)

            scene_class_obj = getattr(module, scene_class)
            scene = scene_class_obj()
            scene.render()
            return self._find_rendered_video(script_dir)
        except Exception as e:
            logger.error("Manim API rendering failed: %s", e)
            return None

    def _render_with_remotion(self, script: str, scene_class: str, output_dir: str) -> dict:
        """使用 Remotion 渲染视频（Windows 降级方案）"""
        try:
            import requests

            remotion_service_url = os.getenv("REMOTION_SERVICE_URL", "http://localhost:3000")
            task_id = str(uuid.uuid4())[:8]

            payload = {
                "scene_class": scene_class,
                "script": script,
                "output_path": os.path.join(output_dir, f"{scene_class}_{task_id}.mp4"),
            }

            logger.info("Using Remotion fallback rendering...")
            response = requests.post(
                f"{remotion_service_url}/render",
                json=payload,
                timeout=300,
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "status": "completed",
                    "video_url": result.get("video_url", f"/static/videos/{scene_class}_{task_id}.mp4"),
                    "rendered_by": "remotion",
                }
            else:
                return {
                    "status": "failed",
                    "message": f"Remotion rendering failed: {response.text}",
                }
        except requests.ConnectionError:
            return {
                "status": "failed",
                "message": "Remotion service not running. Start: cd C:\\Users\\24711\\Desktop\\remotion-service && npm start",
            }
        except Exception as e:
            return {"status": "failed", "message": f"Remotion error: {e}"}

    def _find_rendered_video(self, script_dir: str):
        """查找 Manim 渲染输出的视频文件"""
        media_dir = os.path.join(script_dir, "media")
        if not os.path.exists(media_dir):
            return None

        for root, dirs, files in os.walk(media_dir):
            for f in files:
                if f.endswith(".mp4"):
                    return os.path.join(root, f)
        return None

    @staticmethod
    def _check_manim() -> bool:
        """检查 Manim 是否可用"""
        try:
            import manim
            return True
        except ImportError:
            return False

    @staticmethod
    def _check_remotion() -> bool:
        """检查 Remotion 服务是否可用"""
        try:
            import requests
            remotion_url = os.getenv("REMOTION_SERVICE_URL", "http://localhost:3000")
            response = requests.get(f"{remotion_url}/health", timeout=3)
            return response.status_code == 200
        except Exception:
            return False
