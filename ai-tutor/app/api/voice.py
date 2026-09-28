"""语音对话API — ASR WebSocket代理 + TTS WebSocket流式"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
import logging
import base64

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.websocket("/asr")
async def asr_websocket(websocket: WebSocket):
    """ASR WebSocket代理：浏览器→后端→讯飞IAT

    流程：
    1. 浏览器连接后端WebSocket
    2. 后端连接讯飞IAT WebSocket
    3. 浏览器发送录音数据（PCM）→后端转发给讯飞
    4. 讯飞返回识别结果→后端转发给浏览器
    5. 识别完成后浏览器收到最终文本
    """
    await websocket.accept()

    try:
        # 获取讯飞ASR配置
        from app.core.config import get_settings
        settings = get_settings()

        app_id = settings.xunfei_app_id
        api_key = settings.xunfei_api_key
        api_secret = settings.xunfei_api_secret

        if not all([app_id, api_key, api_secret]):
            await websocket.send_json({"type": "error", "message": "讯飞ASR未配置"})
            await websocket.close()
            return

        # 构建讯飞IAT WebSocket URL
        import hmac
        import hashlib
        from datetime import datetime
        from urllib.parse import urlencode

        # 生成鉴权URL
        now = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        signature_origin = f"host: iat-api.xfyun.cn\ndate: {now}\nGET /v2/iat HTTP/1.1"
        signature_sha = hmac.new(
            api_secret.encode(), signature_origin.encode(), digestmod=hashlib.sha256
        ).digest()
        signature = base64.b64encode(signature_sha).decode()
        authorization = base64.b64encode(
            f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'.encode()
        ).decode()

        url = f"wss://iat-api.xfyun.cn/v2/iat?{urlencode({'authorization': authorization, 'date': now, 'host': 'iat-api.xfyun.cn'})}"

        # 连接讯飞IAT
        import websockets

        async with websockets.connect(url) as xunfei_ws:
            # 发送初始参数
            params = {
                "common": {"app_id": app_id},
                "business": {
                    "language": "zh_cn",
                    "domain": "iat",
                    "accent": "mandarin",
                    "vad_eos": 2000,
                    "dwa": "wpgs"
                },
                "data": {
                    "status": 0,
                    "format": "audio/L16;rate=16000",
                    "encoding": "raw"
                }
            }
            await xunfei_ws.send(json.dumps(params))

            # 双向转发
            async def browser_to_xunfei():
                """浏览器→讯飞"""
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        # 转发给讯飞
                        frame = {
                            "data": {
                                "status": 1,  # 中间帧
                                "format": "audio/L16;rate=16000",
                                "encoding": "raw",
                                "audio": base64.b64encode(data).decode()
                            }
                        }
                        await xunfei_ws.send(json.dumps(frame))
                except WebSocketDisconnect:
                    # 浏览器断开，发送结束帧
                    end_frame = {
                        "data": {
                            "status": 2,  # 结束帧
                            "format": "audio/L16;rate=16000",
                            "encoding": "raw",
                            "audio": ""
                        }
                    }
                    try:
                        await xunfei_ws.send(json.dumps(end_frame))
                    except Exception:
                        pass

            async def xunfei_to_browser():
                """讯飞→浏览器"""
                try:
                    async for msg in xunfei_ws:
                        result = json.loads(msg)
                        code = result.get("code", -1)

                        if code != 0:
                            await websocket.send_json({
                                "type": "error",
                                "message": result.get("message", "ASR error")
                            })
                            break

                        data = result.get("data", {})
                        # 提取识别文本
                        ws_list = data.get("result", {}).get("ws", [])
                        text = "".join(
                            cw.get("w", [{}])[0].get("wp", "")
                            for ws in ws_list
                            for cw in ws.get("cw", [{}])
                        ) if ws_list else ""

                        # 发送给浏览器
                        await websocket.send_json({
                            "type": "partial" if data.get("status", 2) == 1 else "final",
                            "text": text,
                            "is_end": data.get("status", 2) == 2
                        })

                        if data.get("status", 2) == 2:
                            break
                except Exception as e:
                    logger.error(f"Xunfei ASR error: {e}")
                    try:
                        await websocket.send_json({"type": "error", "message": "识别失败"})
                    except Exception:
                        pass

            # 并行执行双向转发
            await asyncio.gather(
                browser_to_xunfei(),
                xunfei_to_browser(),
                return_exceptions=True
            )

    except Exception as e:
        logger.error(f"ASR WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/tts")
async def tts_websocket(websocket: WebSocket):
    """TTS WebSocket流式合成：浏览器请求→后端→讯飞TTS→浏览器播放

    流程：
    1. 浏览器连接后端WebSocket
    2. 浏览器发送要合成的文本
    3. 后端连接讯飞TTS WebSocket
    4. 讯飞返回PCM音频数据→后端转发给浏览器
    5. 浏览器用AudioContext播放
    """
    await websocket.accept()

    try:
        # 接收要合成的文本
        data = await websocket.receive_json()
        text = data.get("text", "")
        voice = data.get("voice", "xiaoyu")  # 默认教书先生风格

        if not text:
            await websocket.send_json({"type": "error", "message": "No text provided"})
            await websocket.close()
            return

        # 限制语音回复80字
        if len(text) > 80:
            text = text[:77] + "..."
            await websocket.send_json({
                "type": "info",
                "message": "回复较长，已截断为语音版，完整内容请查看文字"
            })

        from app.core.config import get_settings
        settings = get_settings()

        app_id = settings.xunfei_app_id
        api_key = settings.xunfei_api_key
        api_secret = settings.xunfei_api_secret

        if not all([app_id, api_key, api_secret]):
            await websocket.send_json({"type": "error", "message": "讯飞TTS未配置"})
            await websocket.close()
            return

        # 构建讯飞TTS WebSocket URL
        import hmac
        import hashlib
        from datetime import datetime
        from urllib.parse import urlencode

        now = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        signature_origin = f"host: tts-api.xfyun.cn\ndate: {now}\nGET /v2/tts HTTP/1.1"
        signature_sha = hmac.new(
            api_secret.encode(), signature_origin.encode(), digestmod=hashlib.sha256
        ).digest()
        signature = base64.b64encode(signature_sha).decode()
        authorization = base64.b64encode(
            f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'.encode()
        ).decode()

        url = f"wss://tts-api.xfyun.cn/v2/tts?{urlencode({'authorization': authorization, 'date': now, 'host': 'tts-api.xfyun.cn'})}"

        # 连接讯飞TTS
        import websockets

        async with websockets.connect(url) as xunfei_ws:
            # 发送TTS请求
            params = {
                "common": {"app_id": app_id},
                "business": {
                    "aue": "raw",  # PCM格式
                    "auf": "audio/L16;rate=16000",
                    "vcn": voice,  # 发音人
                    "speed": 50,
                    "volume": 50,
                    "pitch": 50,
                    "bgs": 0,
                    "tte": "UTF8"
                },
                "data": {
                    "status": 2,
                    "text": base64.b64encode(text.encode()).decode()
                }
            }
            await xunfei_ws.send(json.dumps(params))

            # 接收音频数据
            async for msg in xunfei_ws:
                result = json.loads(msg)
                code = result.get("code", -1)

                if code != 0:
                    await websocket.send_json({
                        "type": "error",
                        "message": result.get("message", "TTS error")
                    })
                    break

                data = result.get("data", {})
                audio = data.get("audio", "")
                status = data.get("status", 2)

                if audio:
                    # 发送PCM音频数据
                    await websocket.send_bytes(base64.b64decode(audio))

                if status == 2:
                    # 合成完成
                    await websocket.send_json({"type": "end"})
                    break

    except Exception as e:
        logger.error(f"TTS WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
