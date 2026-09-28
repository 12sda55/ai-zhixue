"""语音合成服务

支持两种TTS引擎：
1. 讯飞TTS（WebSocket API）- 原有服务，发音人有限
2. Edge TTS（微软Azure神经网络）- 免费，中文自然度高，有情感语气

对照 ai_architecture_plan.md：
- 讯飞多模态工具用于视频/语音生成
- 支持多种语音角色
- 支持讲解风格选择
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import struct
import threading
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode, urlparse

import websocket

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 讯飞语音角色映射
# v2 API 支持的发音人，超拟人系列(x4_)基于大模型，有呼吸停顿等自然语气
VOICE_MAP = {
    # 普通发音人
    "xiaoyan": "xiaoyan",              # 小燕（女声，温柔，默认）
    "xiaoyu": "xiaoyu",                # 小宇（男声，沉稳）
    "xiaofeng": "xiaofeng",            # 小枫（男声，活泼）
    # 超拟人发音人（x4_ 系列，已授权，有语气情感，更自然）
    "x4_lingfeizhe_oral": "x4_lingfeizhe_oral",    # 聆飞哲（男声，沉稳，适合知识讲解）
    "x4_lingxiaoqi_oral": "x4_lingxiaoqi_oral",    # 聆小琪（女声，亲切自然）
    "x4_lingyuyan_oral": "x4_lingyuyan_oral",      # 聆玉言（女声，温暖治愈）
    "x4_lingfeiyi_oral": "x4_lingfeiyi_oral",      # 聆飞逸（男声，沉稳）
    "x4_lingxiaoxuan_oral": "x4_lingxiaoxuan_oral", # 聆小璇（女声）
    "x4_lingyuzhao_oral": "x4_lingyuzhao_oral",    # 聆玉昭（女声）
    # 极速超拟人（x6_ 系列，免费，流式合成）
    "x6_xiaoqiChat_pro": "x6_xiaoqiChat_pro",      # 聆小琪极速版
    "x6_lingfeizhe_pro": "x6_lingfeizhe_pro",      # 聆飞哲极速版
    "x6_lingyuyan_pro": "x6_lingyuyan_pro",        # 聆玉言极速版
    # 旧版超拟人（ais 系列）
    "aisjiuxu": "aisjiuxu",            # 艾小纯（女声，超拟人）
    "aisxping": "aisxping",            # 艾小萍（女声，超拟人）
}


class TTSService:
    """讯飞语音合成服务"""

    def __init__(self):
        settings = get_settings()
        self.app_id = settings.xunfei_app_id
        self.api_key = settings.xunfei_api_key
        self.api_secret = settings.xunfei_api_secret
        self._available = bool(self.app_id and self.api_key and self.api_secret)

    @property
    def available(self) -> bool:
        """检查讯飞TTS是否可用（凭据已配置）"""
        return self._available

    def _create_auth_url(self) -> str:
        """生成讯飞WebSocket鉴权URL"""
        url = "wss://tts-api.xfyun.cn/v2/tts"
        now = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")

        signature_origin = f"host: ws-api.xfyun.cn\ndate: {now}\nGET /v2/tts HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode(encoding="utf-8")

        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(
            encoding="utf-8"
        )

        params = {"authorization": authorization, "date": now, "host": "ws-api.xfyun.cn"}
        return url + "?" + urlencode(params)

    def synthesize(self, text: str, voice: str = "xiaoyan", speed: int = 50) -> bytes:
        """合成语音

        Args:
            text: 要合成的文本
            voice: 语音角色
                - xiaoyan: 小燕（女声，温柔）
                - xiaoyu: 小宇（男声，沉稳）
                - xiaofeng: 小枫（男声，活泼）
            speed: 语速 0-100

        Returns:
            音频数据（MP3格式）
        """
        if not self._available:
            logger.warning("讯飞TTS未配置凭据，返回空音频")
            return b""

        voice_name = VOICE_MAP.get(voice, "xiaoyan")

        # 构建请求参数
        business_params = {
            "aue": "lame",  # MP3格式
            "sfl": 1,       # 开启流式返回
            "auf": "audio/L16;rate=16000",
            "vcn": voice_name,
            "speed": speed,
            "volume": 50,
            "pitch": 50,
            "bgs": 0,
            "tte": "UTF8",
        }

        data_params = {
            "status": 2,  # 一次性发送
            "text": str(base64.b64encode(text.encode("utf-8")), "utf-8"),
        }

        common_params = {
            "app_id": self.app_id,
        }

        request_json = json.dumps(
            {
                "common": common_params,
                "business": business_params,
                "data": data_params,
            }
        )

        audio_data = bytearray()

        def on_message(ws, message):
            try:
                result = json.loads(message)
                code = result.get("code", -1)
                if code != 0:
                    error_msg = result.get("message", "unknown error")
                    logger.error("讯飞TTS错误: code=%s, msg=%s", code, error_msg)
                    ws.close()
                    return

                data = result.get("data", {})
                audio = data.get("audio", "")
                status = data.get("status", 0)

                if audio:
                    audio_data.extend(base64.b64decode(audio))

                if status == 2:
                    ws.close()
            except Exception as e:
                logger.error("讯飞TTS消息处理失败: %s", e)
                ws.close()

        def on_error(ws, error):
            logger.error("讯飞TTS WebSocket错误: %s", error)

        def on_close(ws, close_status_code, close_msg):
            pass

        def on_open(ws):
            ws.send(request_json)

        try:
            auth_url = self._create_auth_url()
            ws = websocket.WebSocketApp(
                auth_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open,
            )
            ws.run_forever()
        except Exception as e:
            logger.error("讯飞TTS合成失败: %s", e)
            return b""

        return bytes(audio_data)

    def save_audio(self, text: str, output_path: str, voice: str = "xiaoyan", speed: int = 50) -> str:
        """合成语音并保存到文件

        Args:
            text: 要合成的文本
            output_path: 输出文件路径（.mp3）
            voice: 语音角色
            speed: 语速

        Returns:
            音频文件路径，失败返回空字符串
        """
        audio_data = self.synthesize(text, voice, speed)
        if not audio_data:
            logger.warning("TTS合成返回空音频，未保存文件")
            return ""

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_data)

        logger.info("TTS音频已保存: %s (%d bytes)", output_path, len(audio_data))
        return output_path


class EdgeTTSService:
    """Edge TTS 语音合成服务（微软Azure神经网络，免费，中文自然度高）

    相比讯飞TTS的优势：
    - 免费，无需API Key
    - 中文发音人自然度高，有情感语气
    - 支持流式合成

    发音人选择（已测试全部可用且声音独立）：
    - zh-CN-XiaoxiaoNeural: 晓晓（女声，亲切自然，最受欢迎）
    - zh-CN-YunxiNeural: 云希（男声，温暖自然，适合讲解）
    - zh-CN-YunyangNeural: 云扬（男声，新闻播报风格）
    - zh-CN-XiaoyiNeural: 晓伊（女声，活泼）
    - zh-CN-YunjianNeural: 云健（男声，沉稳有力）
    """

    # Edge TTS 可用的中文发音人
    AVAILABLE_VOICES = {
        "zh-CN-XiaoxiaoNeural": "晓晓（女声，亲切自然）",
        "zh-CN-YunxiNeural": "云希（男声，温暖自然，适合讲解）",
        "zh-CN-YunyangNeural": "云扬（男声，新闻播报风格）",
        "zh-CN-XiaoyiNeural": "晓伊（女声，活泼）",
        "zh-CN-YunjianNeural": "云健（男声，沉稳有力）",
    }

    def __init__(self):
        try:
            import edge_tts  # noqa: F401
            self._available = True
        except ImportError:
            self._available = False
            logger.warning("edge-tts未安装，Edge TTS不可用。请运行: pip install edge-tts")

    @property
    def available(self) -> bool:
        return self._available

    @staticmethod
    def _convert_speed(speed: int) -> str:
        """将讯飞语速(0-100, 50=正常)转换为Edge TTS语速百分比字符串

        讯飞: 50=正常, <50慢, >50快
        Edge: +0%=正常, -10%慢, +10%快
        """
        # 讯飞50对应Edge +0%，每偏离10对应Edge ±2%
        rate = (speed - 50) * 2
        return f"{rate:+d}%"

    def save_audio(self, text: str, output_path: str, voice: str = "zh-CN-YunxiNeural", speed: int = 50) -> str:
        """合成语音并保存到文件

        Args:
            text: 要合成的文本
            output_path: 输出文件路径（.mp3）
            voice: Edge TTS发音人，默认云希（男声，适合讲解）
            speed: 语速 0-100（50=正常），会自动转换为Edge TTS格式

        Returns:
            音频文件路径，失败返回空字符串
        """
        if not self._available:
            logger.warning("Edge TTS不可用，返回空")
            return ""

        import edge_tts

        # 验证发音人
        if voice not in self.AVAILABLE_VOICES:
            logger.warning("未知Edge TTS发音人: %s，使用默认云希", voice)
            voice = "zh-CN-YunxiNeural"

        rate = self._convert_speed(speed)
        logger.info("Edge TTS合成: voice=%s rate=%s text='%s...'",
                    voice, rate, text[:30])

        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # edge-tts是异步的，需要在事件循环中运行
            # ★ 添加超时机制：Sealos pod 网络可能受限，edge-tts 连接微软服务器可能超时
            async def _synthesize():
                communicate = edge_tts.Communicate(text, voice, rate=rate)
                # 30秒超时：单段旁白通常 < 15 秒，超时说明网络不通
                await asyncio.wait_for(communicate.save(output_path), timeout=30.0)

            # 在新的事件循环中运行（避免与主循环冲突）
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_synthesize())
            finally:
                loop.close()

            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                logger.info("Edge TTS音频已保存: %s (%d bytes)",
                            output_path, os.path.getsize(output_path))
                return output_path
            else:
                logger.warning("Edge TTS合成失败：文件过小或不存在")
                return ""

        except asyncio.TimeoutError:
            logger.error("[TTS FAILED] Edge TTS 超时（30秒）| voice=%s, text='%s...' | 可能是容器网络无法访问微软服务器",
                         voice, text[:50])
            return ""
        except Exception as e:
            logger.error("[TTS FAILED] Edge TTS合成异常: %s | voice=%s, text='%s...'", str(e), voice, text[:50], exc_info=True)
            return ""


def get_tts_service(voice: str) -> object:
    """根据发音人名称选择TTS服务

    Args:
        voice: 发音人名称
            - 以 "zh-CN-" 开头：使用Edge TTS
            - 其他：使用讯飞TTS

    Returns:
        TTS服务实例（TTSService 或 EdgeTTSService）
    """
    if voice and voice.startswith("zh-CN-"):
        return edge_tts_service
    return tts_service


# 全局单例
tts_service = TTSService()
edge_tts_service = EdgeTTSService()
