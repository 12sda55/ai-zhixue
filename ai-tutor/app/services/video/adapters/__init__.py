from .base import VideoAdapter, VideoResult
from .manim_adapter import ManimAdapter

ADAPTERS = {
    "manim": ManimAdapter,
}

# 降级链：Manim/Remotion（程序化渲染，1-3分钟教学视频）
# Manim 为主力：LLM生成脚本→程序化渲染→TTS旁白→拼接，质量可控
import os

_env_order = os.getenv("VIDEO_PROVIDER_ORDER", "manim")
FALLBACK_CHAIN = [p.strip() for p in _env_order.split(",") if p.strip() in ADAPTERS]

__all__ = ["VideoAdapter", "VideoResult", "ManimAdapter", "ADAPTERS", "FALLBACK_CHAIN"]
