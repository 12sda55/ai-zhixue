"""视频生成适配器抽象基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VideoResult:
    """视频生成结果"""
    url: str  # 视频文件URL或本地路径
    duration: float = 0.0
    width: int = 1280
    height: int = 720
    poster: Optional[str] = None  # 封面图URL
    provider: str = ""  # 由哪个provider生成
    has_audio: bool = False  # 是否包含音频


@dataclass
class ProviderCapabilities:
    """Provider能力声明"""
    supported_aspect_ratios: list = field(default_factory=lambda: ["16:9"])
    supported_durations: list = field(default_factory=lambda: [5, 10])
    supported_resolutions: list = field(default_factory=lambda: ["720p", "1080p"])
    max_duration: int = 10
    supports_audio: bool = False


class VideoAdapter(ABC):
    """视频生成适配器抽象基类

    所有视频生成Provider必须实现此接口。
    参考 OpenMAIC 的 VideoProviderConfig + MediaTaskAdapter 设计。
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Provider唯一标识"""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Provider能力声明"""
        ...

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> VideoResult:
        """生成视频

        Args:
            prompt: 视频描述文本
            **kwargs: Provider特定参数（aspect_ratio, duration, resolution等）

        Returns:
            VideoResult 生成结果
        """
        ...

    @abstractmethod
    async def check_availability(self) -> bool:
        """检查Provider是否可用（API Key是否配置、服务是否可达）"""
        ...

    def normalize_options(self, **kwargs) -> dict:
        """归一化生成参数，将不支持的参数降级为Provider支持的值

        参考 OpenMAIC 的 normalizeVideoOptions
        """
        caps = self.capabilities
        normalized = dict(kwargs)

        if "aspect_ratio" in normalized:
            if normalized["aspect_ratio"] not in caps.supported_aspect_ratios:
                normalized["aspect_ratio"] = caps.supported_aspect_ratios[0]

        if "duration" in normalized:
            if normalized["duration"] not in caps.supported_durations:
                normalized["duration"] = caps.supported_durations[0]
            normalized["duration"] = min(normalized["duration"], caps.max_duration)

        if "resolution" in normalized:
            if normalized["resolution"] not in caps.supported_resolutions:
                normalized["resolution"] = caps.supported_resolutions[0]

        return normalized
