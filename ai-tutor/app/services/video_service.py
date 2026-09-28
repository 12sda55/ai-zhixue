"""视频生成服务 - 两步生成管线：LLM讲解脚本 → Manim动画 + TTS旁白 + MoviePy拼接

对照 ai_architecture_plan.md Agent 5 第二层：
- 旁白文案由LLM生成（不是手写模板拼接）
- 两步生成：LLM先生成讲解脚本→再生成Manim代码
- TTS发音人改为xiaoyu（教书先生风格）
- MoviePy拼接视频+多段音频+字幕叠加
- VideoAgent纳入对话系统（已在AGENT_REGISTRY中注册）
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from typing import Optional

from app.core.llm import llm_client
from app.knowledge.manim_templates import get_manim_template, list_available_templates
from app.services.tts_service import tts_service, edge_tts_service, get_tts_service

logger = logging.getLogger(__name__)

# Windows 下隐藏子进程终端窗口（防止 ffmpeg/manim 弹出黑色 cmd 窗口）
CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

# 视频输出目录
VIDEO_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "videos")

# 讲解风格对应的TTS参数 — 使用Edge TTS（微软Azure神经网络，免费且中文自然度高）
# Edge TTS发音人已测试全部可用且声音独立，有情感语气，对标OpenMAIC质量
STYLE_CONFIG = {
    "rigorous": {"voice": "zh-CN-YunxiNeural", "speed": 45},      # 严谨：云希（男声，温暖自然，适合知识讲解）
    "relaxed": {"voice": "zh-CN-XiaoxiaoNeural", "speed": 55},    # 轻松：晓晓（女声，亲切自然，最受欢迎）
    "guided": {"voice": "zh-CN-XiaoyiNeural", "speed": 50},       # 引导：晓伊（女声，活泼）
    "whiteboard": {"voice": "zh-CN-YunxiNeural", "speed": 48},    # 白板：云希（男声，适合教学）
}


def _check_command(cmd: str) -> bool:
    """检查命令是否可用"""
    return shutil.which(cmd) is not None


class VideoGenerationTask:
    """视频生成任务状态"""

    def __init__(self, task_id: str, knowledge_point: str, style: str):
        self.task_id = task_id
        self.knowledge_point = knowledge_point
        self.style = style
        self.status = "pending"  # pending / generating / completed / failed / manim_not_available
        self.progress = 0
        self.message = ""
        self.video_path = ""
        self.video_url = ""
        self.subtitle_url = ""  # VTT字幕文件URL（用于软字幕开关）
        self.script_content = ""
        self.created_at = ""

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "knowledge_point": self.knowledge_point,
            "style": self.style,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "video_path": self.video_path,
            "video_url": self.video_url,
            "subtitle_url": self.subtitle_url,  # 返回字幕URL
            "script_content": self.script_content,
            "created_at": self.created_at,
        }


class VideoService:
    """视频生成服务 - Manim白板动画 + 讯飞TTS"""

    # 内存存储兜底（Redis 不可用时使用）
    _memory_store: dict = {}

    def __init__(self):
        self._manim_available = _check_command("manim") or self._check_manim_import()
        self._ffmpeg_available = _check_command("ffmpeg") or self._check_ffmpeg_in_path()
        os.makedirs(VIDEO_OUTPUT_DIR, exist_ok=True)
        self._redis_available = self._check_redis()

    @staticmethod
    def _check_manim_import() -> bool:
        """通过 Python import 检测 Manim 是否可用"""
        try:
            import manim
            return True
        except ImportError:
            return False

    @staticmethod
    def _check_ffmpeg_in_path() -> bool:
        """检测 FFmpeg 是否在常见路径中可用"""
        # 检查 Remotion 自带的 FFmpeg
        remotion_ffmpeg = os.path.join(
            os.path.expanduser("~"),
            "Desktop", "remotion-service", "node_modules",
            "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe"
        )
        if os.path.exists(remotion_ffmpeg):
            # 加入 PATH
            ffmpeg_dir = os.path.dirname(remotion_ffmpeg)
            if ffmpeg_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + ffmpeg_dir
            return True
        return False

    def _get_redis(self):
        """获取Redis连接"""
        import redis
        from app.core.config import get_settings
        settings = get_settings()
        return redis.from_url(settings.redis_url)

    def _check_redis(self) -> bool:
        """检查 Redis 是否可用"""
        try:
            r = self._get_redis()
            r.ping()
            logger.info("Redis 连接成功，使用 Redis 存储任务状态")
            return True
        except Exception as e:
            logger.warning("Redis 不可用 (%s)，使用内存存储兜底", e)
            return False

    # ----- task Redis/内存操作 -----
    def _save_task(self, task: VideoGenerationTask):
        """保存任务到Redis或内存"""
        if self._redis_available:
            try:
                r = self._get_redis()
                r.hset(f"video:task:{task.task_id}", mapping=task.to_dict())
                r.expire(f"video:task:{task.task_id}", 7 * 86400)
                return
            except Exception as e:
                logger.warning("Redis保存任务失败: %s，降级到内存存储", e)
        # 内存存储兜底
        self.__class__._memory_store[f"video:task:{task.task_id}"] = task.to_dict()

    def _get_task(self, task_id: str) -> Optional[VideoGenerationTask]:
        """从Redis或内存获取任务"""
        data = None
        
        if self._redis_available:
            try:
                r = self._get_redis()
                data = r.hgetall(f"video:task:{task_id}")
                if data:
                    decoded = {k.decode() if isinstance(k, bytes) else k: (v.decode() if isinstance(v, bytes) else v) for k, v in data.items()}
            except Exception as e:
                logger.warning("Redis获取任务失败: %s，尝试内存存储", e)
        
        # 内存存储兜底
        if not data:
            raw = self.__class__._memory_store.get(f"video:task:{task_id}")
            if not raw:
                return None
            decoded = raw
        task = VideoGenerationTask(
            task_id=decoded.get("task_id", task_id),
            knowledge_point=decoded.get("knowledge_point", ""),
            style=decoded.get("style", "rigorous"),
        )
        task.status = decoded.get("status", "pending")
        task.progress = int(decoded.get("progress", 0))
        task.message = decoded.get("message", "")
        task.video_path = decoded.get("video_path", "")
        task.video_url = decoded.get("video_url", "")
        task.subtitle_url = decoded.get("subtitle_url", "")  # 加载字幕URL
        task.script_content = decoded.get("script_content", "")
        task.created_at = decoded.get("created_at", "")
        return task

    def _delete_task(self, task_id: str):
        """从Redis或内存删除任务"""
        if self._redis_available:
            try:
                r = self._get_redis()
                r.delete(f"video:task:{task_id}")
                return
            except Exception as e:
                logger.warning("Redis删除任务失败: %s", e)
        # 内存存储兜底
        self.__class__._memory_store.pop(f"video:task:{task_id}", None)

    # ----- cache Redis操作 -----
    def _save_cache(self, key: str, value: dict):
        """保存缓存到Redis"""
        try:
            r = self._get_redis()
            r.setex(f"video:cache:{key}", 7 * 86400, json.dumps(value, ensure_ascii=False))
        except Exception as e:
            logger.warning("Redis保存缓存失败: %s", e)

    def _get_cache(self, key: str) -> Optional[dict]:
        """从Redis获取缓存"""
        try:
            r = self._get_redis()
            data = r.get(f"video:cache:{key}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning("Redis获取缓存失败: %s", e)
            return None

    def _delete_cache(self, key: str):
        """从Redis删除缓存"""
        try:
            r = self._get_redis()
            r.delete(f"video:cache:{key}")
        except Exception as e:
            logger.warning("Redis删除缓存失败: %s", e)

    @property
    def manim_available(self) -> bool:
        return self._manim_available

    @property
    def ffmpeg_available(self) -> bool:
        return self._ffmpeg_available

    def generate_manim_script(self, knowledge_point: str, style: str = "rigorous") -> str:
        """生成Manim动画脚本

        根据知识点和讲解风格，生成Manim Python脚本。
        白板动画风格：白底黑字简笔画。

        优先使用预置模板，无模板时使用LLM生成。
        """
        # 1. 优先使用预置模板
        template = get_manim_template(knowledge_point)
        if template:
            logger.info("使用预置Manim模板: %s", knowledge_point)
            import re
            return re.sub(r'#SEG_DUR_\d+#', '1.0', template["script"])

        # 2. 使用LLM生成Manim脚本
        logger.info("使用LLM生成Manim脚本: %s", knowledge_point)
        return self._generate_script_with_llm(knowledge_point, style)

    def _generate_script_with_llm(self, knowledge_point: str, style: str) -> str:
        """使用LLM生成Manim脚本"""
        style_desc = {
            "rigorous": "严谨学术风格，注重原理推导和数学表达",
            "relaxed": "轻松活泼风格，用生活化比喻和幽默语言",
            "guided": "引导启发风格，通过提问引导学生思考",
        }

        # 生成合法的Scene类名（只包含ASCII字符）
        import re
        safe_class_name = re.sub(r'[^\w]', '', knowledge_point.replace(' ', '_'))
        # 如果全是中文或其他非ASCII字符，使用通用名称
        if not safe_class_name or not re.match(r'^[a-zA-Z_]', safe_class_name):
            safe_class_name = 'KnowledgePoint'

        prompt = f"""请为知识点「{knowledge_point}」生成一个Manim动画脚本。

要求：
1. 使用Manim Community版本语法（from manim import *）
2. 白底黑字简笔画风格：self.camera.background_color = WHITE，所有文字和线条颜色用BLACK
3. 创建一个Scene类，类名为{safe_class_name}Scene（必须是合法Python标识符，只包含字母、数字、下划线）
4. 动画时长1-3分钟
5. 步骤清晰，每步有self.wait()暂停
6. 包含标题、概念说明、动画演示、总结
7. 使用Square/Rectangle/Circle/Text/Arrow/Line等基本对象。**严格按以下API用法，第一个位置参数都是color，尺寸必须用关键字参数**：
   - Rectangle(width=1, height=1, color=BLACK)  ✅  禁止 Rectangle(1, 1, color=BLACK) ❌
   - Square(side_length=1, color=BLUE)  ✅  禁止 Square(1, color=BLUE) ❌
   - Circle(radius=0.5, color=RED)  ✅  禁止 Circle(0.5, color=RED) ❌
   - Line(start=LEFT, end=RIGHT, color=BLACK)  ✅
   - Arrow(start=UP, end=DOWN, color=BLACK)  ✅
   - Text("内容", color=BLACK)  ✅
8. 用颜色高亮关键元素（**只使用以下Manim预定义颜色：BLACK, WHITE, RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE, PINK, TEAL, MAROON**）
   - YELLOW表示比较/查找中
   - RED表示不符合（需要旋转/交换）
   - GREEN表示符合/完成
   - **禁止使用 DARK_GREEN、DARK_RED 等非标准颜色名称！**
9. 讲解风格：{style_desc.get(style, style_desc['rigorous'])}
10. **关键：所有显示的文字必须使用中文！仅专业术语保留英文（如Red-Black Tree、BST、O(log n)等）**
11. **中文文字必须使用 MarkupText() 并指定字体：MarkupText("中文内容", font="Microsoft YaHei", color=BLACK)**
12. **纯英文文字（如专业术语）使用 Text()：Text("BST", color=BLACK)**
   - **禁止使用 `size` 参数！Text/MarkupText 只支持 `font_size` 参数，例如 Text("BST", color=BLACK, font_size=28)**
   - 错误示例：Text("BST", size=28) ❌
   - 正确示例：Text("BST", font_size=28) ✅
13. 文字要简短精炼，每条不超过15个字
14. **坐标必须用3D元组 (x, y, 0)，禁止使用2D坐标 (x, y)**。例如：move_to((2, 0, 0))、shift(UP*2)、move_to(np.array([1, 2, 0]))
15. **【关键API规则】禁止把Python列表直接传给 .next_to() / .move_to() / .shift()！**
    - 错误示例：label.next_to(boxes, DOWN)  # boxes 是 list，触发 ValueError
    - 正确做法：label.next_to(Group(*boxes), DOWN) 或 label.next_to(boxes[-1], DOWN)
16. **【关键API规则】禁止用 hasattr(obj, 'get_X') 做防御性检查访问Manim属性！**
    - Manim 的 Mobject.__getattr__ 会对任何 'get_*' 前缀返回 lambda，hasattr 永远返回 True 但调用报错
    - 错误示例：text = obj.get_tex_string() if hasattr(obj, 'get_tex_string') else obj.text
    - 正确做法：直接用 obj.text 访问文本内容
17. **【关键API规则】Table 取单元格内容用 get_entries()，不要用 get_cell()！**
    - table.get_cell((row, col)) 返回边框 Rectangle（无 .text 属性）
    - table.get_entries((row, col)) 返回单元格内容 mobject（有 .text 属性）
    - 推荐做法：直接用源数据列表内容判断，避免访问 mobject 属性
18. **【关键API规则】禁止使用 self.mobjects_from_animations！此API在Manim Community 0.19.0中不存在！**
    - 错误示例：for line in self.mobjects_from_animations:
    - 正确做法：for line in self.mobjects:  # 使用 self.mobjects 访问场景中的所有Mobject
    - self.mobjects_from_animations 会导致 AttributeError，必须用 self.mobjects 替代
19. **【关键文字规则】MarkupText 中禁止使用 Pango 特殊字符：→ ← ↑ ↓ ≤ ≥ × 等！**
    - MarkupText 使用 Pango XML 解析，这些字符会被误解析导致 ValueError
    - 错误示例：MarkupText("6<8 → 左")  # ← 和 → 导致 Pango 报错
    - 正确做法：MarkupText("6小于8, 走左边") 或 MarkupText("6&lt;8, 左")  # 用中文替代或XML转义
    - < 必须写成 &lt;，> 必须写成 &gt;，& 必须写成 &amp;
    - → 用 "变为" 或 "到" 替代；← 用 "来自" 替代
    - 不要在 MarkupText 的文本内容中使用任何箭头符号
20. **【关键布局规则】使用相对定位（next_to / to_edge / shift）而非绝对坐标布局，避免元素重叠！**
    - 错误示例：text.move_to((3, 2, 0))  # 容易和其他元素重叠
    - 正确示例：text.next_to(box, RIGHT, buff=0.5)  # 自动计算位置，不会重叠
    - 标题用 title.to_edge(UP, buff=0.3)，内容用 .shift(DOWN*0.5) 避免和标题重叠
21. **【关键布局规则】每个动画步骤完成后，及时 FadeOut 不再需要的旧元素！**
    - 错误示例：直接 self.play(Write(new_text))  # 旧文字还留在屏幕上，造成重叠
    - 正确做法：先 self.play(FadeOut(old_text)) 再 self.play(Write(new_text))
    - 或同时：self.play(FadeOut(old_text), Write(new_text))
22. **【关键布局规则】多元素排列用 VGroup.arrange()，间距至少 0.5！**
    - 错误示例：box1.move_to((-2,0,0)); box2.move_to((-1,0,0))  # 间距太小，视觉重叠
    - 正确示例：group = VGroup(box1, box2, box3).arrange(RIGHT, buff=0.8)
    - next_to 的 buff 参数至少 0.5：label.next_to(box, DOWN, buff=0.5)

请直接输出完整的Python脚本，不要其他解释。脚本必须可以独立运行。"""

        try:
            result = llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4000,
            )
            # 提取代码块
            if "```python" in result:
                result = result.split("```python")[1].split("```")[0]
            elif "```" in result:
                result = result.split("```")[1].split("```")[0]
            return result.strip()
        except Exception as e:
            logger.error("LLM生成Manim脚本失败: %s", e)
            # 返回一个最小可运行脚本
            class_name = knowledge_point.title().replace("_", "")
            return f'''from manim import *

class {class_name}Scene(Scene):
    def construct(self):
        self.camera.background_color = WHITE
        title = MarkupText("{knowledge_point}", font="Microsoft YaHei", color=BLACK, font_size=40).to_edge(UP)
        self.play(Write(title))
        self.wait(1)
        note = MarkupText("请安装Manim后渲染此脚本", font="Microsoft YaHei", color=BLACK, font_size=24).shift(DOWN)
        self.play(Write(note))
        self.wait(2)
'''

    @staticmethod
    def _fix_chinese_text_in_script(script: str) -> str:
        """修复 Manim 脚本中的中文 Text() 调用 + 转义 MarkupText 中的 XML 特殊字符

        Manim 的 Text() 默认不支持中文，需要替换为 MarkupText() + font='Microsoft YaHei'
        MarkupText 使用 Pango 渲染，< 和 & 需要转义为 XML 实体
        同时替换 Pango 不兼容的 Unicode 特殊字符（→ ← 等）
        """
        import re

        # 匹配中文字符
        def has_chinese(s):
            return bool(re.search(r'[\u4e00-\u9fff]', s))

        # 步骤0：替换 Pango 不兼容的 Unicode 特殊字符（→ ← ↑ ↓ 等）
        pango_unsafe_chars = {
            '→': '到', '←': '来自', '↑': '上', '↓': '下',
            '⇒': '得出', '⇐': '来自', '⇑': '上', '⇓': '下',
            '⟶': '到', '⟵': '来自', '⟹': '得出',
        }
        for char, replacement in pango_unsafe_chars.items():
            script = script.replace(char, replacement)

        # 步骤1：转义所有 MarkupText/Text 调用中的 < > & 字符（防止 Pango XML 解析错误）
        # 匹配 MarkupText("...") 或 Text("...")
        xml_pattern = r'(MarkupText|Text)\(\s*["\']([^"\']+)["\']'

        def escape_xml(match):
            func_name = match.group(1)
            text_content = match.group(2)
            # 检查是否包含需要转义的字符
            if '<' in text_content or '>' in text_content or '&' in text_content:
                escaped = text_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                return f'{func_name}("{escaped}"'
            return match.group(0)

        script = re.sub(xml_pattern, escape_xml, script)

        # 步骤2：替换 Text() 为 MarkupText()（仅中文内容）
        pattern = r'(?<!Markup)Text\(\s*["\']([^"\']+)["\']([^)]*)\)'

        def replacer(match):
            text_content = match.group(1)
            rest_args = match.group(2)
            if has_chinese(text_content):
                if 'font=' in rest_args:
                    return f"MarkupText(\"{text_content}\"{rest_args})"
                else:
                    return f"MarkupText(\"{text_content}\", font=\"Microsoft YaHei\"{rest_args})"
            return match.group(0)

        fixed = re.sub(pattern, replacer, script)

        if fixed != script:
            # 确保 MarkupText 已导入：_render.py 只 from manim import config, Scene，
            # 若用户脚本用 `from manim import Scene, Text`，替换后的 MarkupText 未定义会导致 NameError
            has_star_import = bool(re.search(r'from\s+manim\s+import\s+\*', fixed))
            has_markup_import = bool(re.search(r'from\s+manim\s+import\s+[^\n]*\bMarkupText\b', fixed))
            if not has_star_import and not has_markup_import:
                m_imp = re.search(r'from\s+manim\s+import\s+[^\n]+', fixed)
                if m_imp:
                    fixed = fixed[:m_imp.end()] + ', MarkupText' + fixed[m_imp.end():]
                else:
                    fixed = 'from manim import MarkupText\n' + fixed
            logger.info("已自动修复脚本中的中文 Text() 调用（含 MarkupText 导入）")

        return fixed

    @staticmethod
    def _fix_2d_coordinates(script: str) -> str:
        """修复 Manim 脚本中的 2D 坐标问题

        通过在脚本开头注入 monkey-patch，让 Manim 的 Mobject 方法
        自动将 2D 坐标 (x, y) 转换为 3D 坐标 (x, y, 0)。
        这比正则替换更可靠，不会误伤其他代码。
        """
        # 在 from manim import * 之后注入 monkey-patch
        patch_code = '''
# === 自动注入：2D坐标兼容补丁 ===
import numpy as np
from manim import Mobject, Line, Arrow, Dot, Brace, CubicBezier, Group
from manim.mobject.geometry.line import Line as _Line
from manim.mobject.geometry.tips import ArrowTip

def _to_3d(p):
    """将2D坐标转为3D"""
    if isinstance(p, (tuple, list, np.ndarray)):
        arr = np.array(p, dtype=float)
        if arr.ndim == 1 and len(arr) == 2:
            return np.append(arr, 0.0)
    return p

# 修复 Mobject.move_to
_orig_move_to = Mobject.move_to
def _safe_move_to(self, point_or_mobject, *args, **kwargs):
    # 先处理 list of Mobjects（LLM 常见错误：传 Python list 而非 Mobject）
    if isinstance(point_or_mobject, list):
        if len(point_or_mobject) == 0:
            return self
        if all(isinstance(m, Mobject) for m in point_or_mobject):
            point_or_mobject = Group(*point_or_mobject)
            return _orig_move_to(self, point_or_mobject, *args, **kwargs)
    if isinstance(point_or_mobject, (tuple, list, np.ndarray)):
        arr = np.array(point_or_mobject, dtype=float)
        if arr.ndim == 1 and len(arr) == 2:
            arr = np.append(arr, 0.0)
            return _orig_move_to(self, arr, *args, **kwargs)
    return _orig_move_to(self, point_or_mobject, *args, **kwargs)
Mobject.move_to = _safe_move_to

# 修复 Mobject.shift
_orig_shift = Mobject.shift
def _safe_shift(self, vector, *args, **kwargs):
    if isinstance(vector, (tuple, list, np.ndarray)):
        arr = np.array(vector, dtype=float)
        if arr.ndim == 1 and len(arr) == 2:
            arr = np.append(arr, 0.0)
            return _orig_shift(self, arr, *args, **kwargs)
    return _orig_shift(self, vector, *args, **kwargs)
Mobject.shift = _safe_shift

# 修复 Line 构造函数
_orig_line_init = _Line.__init__
def _safe_line_init(self, *args, **kwargs):
    if len(args) >= 1:
        args = (_to_3d(args[0]),) + args[1:] if args[0] is not None else args
    if len(args) >= 2:
        args = args[:1] + (_to_3d(args[1]),) + args[2:] if args[1] is not None else args
    if 'start' in kwargs:
        kwargs['start'] = _to_3d(kwargs['start'])
    if 'end' in kwargs:
        kwargs['end'] = _to_3d(kwargs['end'])
    return _orig_line_init(self, *args, **kwargs)
_Line.__init__ = _safe_line_init

# 修复 Arrow 构造函数
_orig_arrow_init = Arrow.__init__
def _safe_arrow_init(self, *args, **kwargs):
    if len(args) >= 1:
        args = (_to_3d(args[0]),) + args[1:] if args[0] is not None else args
    if len(args) >= 2:
        args = args[:1] + (_to_3d(args[1]),) + args[2:] if args[1] is not None else args
    if 'start' in kwargs:
        kwargs['start'] = _to_3d(kwargs['start'])
    if 'end' in kwargs:
        kwargs['end'] = _to_3d(kwargs['end'])
    return _orig_arrow_init(self, *args, **kwargs)
Arrow.__init__ = _safe_arrow_init

# 修复 Dot 构造函数
_orig_dot_init = Dot.__init__
def _safe_dot_init(self, *args, **kwargs):
    if len(args) >= 1:
        args = (_to_3d(args[0]),) + args[1:] if args[0] is not None else args
    if 'point' in kwargs:
        kwargs['point'] = _to_3d(kwargs['point'])
    return _orig_dot_init(self, *args, **kwargs)
Dot.__init__ = _safe_dot_init

# 修复 next_to 接收 list 的情况（LLM 常见错误：传 Python list 而非 Mobject）
_orig_next_to = Mobject.next_to
def _safe_next_to(self, mobject_or_point, *args, **kwargs):
    if isinstance(mobject_or_point, list):
        if len(mobject_or_point) == 0:
            return self
        # 检查列表元素是否是 Mobject，若是则用 Group 包裹
        if all(isinstance(m, Mobject) for m in mobject_or_point):
            mobject_or_point = Group(*mobject_or_point)
    return _orig_next_to(self, mobject_or_point, *args, **kwargs)
Mobject.next_to = _safe_next_to

# 修复 Paragraph 没有 .text 属性（Table 默认用 Paragraph 作为单元格内容，LLM 常误用 cell.text）
from manim.mobject.text.text_mobject import Paragraph
def _paragraph_text_getter(self):
    if hasattr(self, 'lines_text') and self.lines_text is not None:
        return getattr(self.lines_text, 'text', '')
    return ''
Paragraph.text = property(_paragraph_text_getter)

# 修复 MarkupText 的 Pango XML 解析问题（LLM 经常在文本中使用 < > → 等特殊字符）
from manim.mobject.text.text_mobject import MarkupText as _OrigMarkupText
_orig_markup_init = _OrigMarkupText.__init__
def _safe_markup_init(self, text, *args, **kwargs):
    # 自动转义 Pango 不兼容的字符
    if isinstance(text, str):
        # 替换 Unicode 箭头为中文
        _pango_replacements = {
            '\u2192': '\u5230', '\u2190': '\u6765\u81ea', '\u2191': '\u4e0a', '\u2193': '\u4e0b',
            '\u21d2': '\u5f97\u51fa', '\u21d0': '\u6765\u81ea', '\u21d1': '\u4e0a', '\u21d3': '\u4e0b',
            '\u27f6': '\u5230', '\u27f5': '\u6765\u81ea', '\u27f9': '\u5f97\u51fa',
        }
        for char, repl in _pango_replacements.items():
            text = text.replace(char, repl)
        # 转义 XML 特殊字符（保护已转义的实体）
        import re as _re
        # 先把已转义的 XML 实体保护起来
        _escaped = []
        def _save_escaped(m):
            _escaped.append(m.group(0))
            return '__ESCAPED_%d__' % (len(_escaped) - 1)
        text = _re.sub(r'&(?:lt|gt|amp|quot|apos|#[0-9]+|#x[0-9a-fA-F]+);', _save_escaped, text)
        # 转义剩余的 < > &
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        # 还原已转义的实体
        for i, ent in enumerate(_escaped):
            text = text.replace('__ESCAPED_%d__' % i, ent)
    return _orig_markup_init(self, text, *args, **kwargs)
_OrigMarkupText.__init__ = _safe_markup_init
# === 补丁结束 ===
'''
        # 在 from manim import * 后注入
        if 'from manim import *' in script and '自动注入：2D坐标兼容补丁' not in script:
            script = script.replace('from manim import *', 'from manim import *' + patch_code, 1)
            logger.info("已注入 2D 坐标兼容补丁（含Line/Arrow/Dot/next_to/Paragraph.text）")
        return script

    @staticmethod
    def _fix_llm_mobject_bugs(script: str) -> str:
        """修复 LLM 生成的 Manim 脚本中的常见 API 误用

        修复5类LLM高频错误：
        1. hasattr(obj, 'get_X') 防御式三元表达式 — Manim __getattr__ 魔法使其失效
        2. table.get_cell() 误用于取单元格文本内容 — 应使用 get_entries()
        3. get_tex_string() 调用 — Text/Paragraph 无此方法，应直接用 .text
        4. stroke_style= 关键字参数 — 本版本 Manim 不支持，需移除
        5. Create/Write/Uncreate 用于不支持的 Mobject — 替换为 FadeIn/FadeOut（全类型兼容）
        """
        import re
        original = script

        # 修复1：obj.get_tex_string() if hasattr(obj, 'get_tex_string') else obj.text  →  obj.text
        pattern1 = r'(\w+)\.get_tex_string\(\)\s+if\s+hasattr\(\1,\s*["\']get_tex_string["\']\)\s+else\s+\1\.text'
        script = re.sub(pattern1, r'\1.text', script)

        # 修复2：table.get_cell((row, col))  →  table.get_entries((row, col))
        script = re.sub(r'\.get_cell\(', '.get_entries(', script)

        # 修复3：剩余的 .get_tex_string() 调用统一替换为 .text
        script = re.sub(r'\.get_tex_string\(\)', '.text', script)

        # 修复4：移除 stroke_style=... 关键字参数（本版本 Manim 的 VMobject.__init__ 不接受）
        # 匹配 stroke_style=['"]...['"] 或 stroke_style=变量名 或 stroke_style=数字
        script = re.sub(r',\s*stroke_style\s*=\s*[^,)\]]+', '', script)
        script = re.sub(r'stroke_style\s*=\s*[^,)\]]+\s*,\s*', '', script)
        script = re.sub(r'stroke_style\s*=\s*[^,)\]]+', '', script)

        # 修复5：Create/Write/Uncreate → FadeIn/FadeOut（避免 NotImplementedError）
        # Create/Write 对某些 Mobject（如 Group、VGroup 含非 VMobject）会抛
        # "This animation is not defined for this Mobject." FadeIn/FadeOut 全类型兼容
        script = re.sub(r'\bCreate\b\s*\(', 'FadeIn(', script)
        script = re.sub(r'\bUncreate\b\s*\(', 'FadeOut(', script)
        script = re.sub(r'\bWrite\b\s*\(', 'FadeIn(', script)

        # 修复6：Tex/MathTex → Text（本机未安装 LaTeX 编译器，Tex 会触发 FileNotFoundError）
        # 先清理 LaTeX 语法：\text{X}→X, \frac{a}{b}→a/b, \sqrt{x}→√x, 去除其他 \command
        # 以及 $...$ 行内公式
        def _latex_to_plain(s: str) -> str:
            # 移除 $...$ 行内公式边界符
            s = re.sub(r'\$([^$]*)\$', r'\1', s)
            # 常见 LaTeX 命令转换
            s = re.sub(r'\\text\{([^}]*)\}', r'\1', s)
            s = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', r'\1/\2', s)
            s = re.sub(r'\\sqrt\{([^}]*)\}', r'√\1', s)
            s = re.sub(r'\\times', '×', s)
            s = re.sub(r'\\cdot', '·', s)
            s = re.sub(r'\\le', '≤', s)
            s = re.sub(r'\\ge', '≥', s)
            s = re.sub(r'\\ne', '≠', s)
            s = re.sub(r'\\rightarrow', '→', s)
            s = re.sub(r'\\leftarrow', '←', s)
            s = re.sub(r'\\in', '∈', s)
            s = re.sub(r'\\sum', 'Σ', s)
            s = re.sub(r'\\pi', 'π', s)
            s = re.sub(r'\\infty', '∞', s)
            s = re.sub(r'\\partial', '∂', s)
            s = re.sub(r'\\approx', '≈', s)
            s = re.sub(r'\\equiv', '≡', s)
            s = re.sub(r'\\pm', '±', s)
            # 处理 O(n^2) 等复杂度表示 — n^2 → n²
            s = re.sub(r'\^2', '²', s)
            s = re.sub(r'\^3', '³', s)
            s = re.sub(r'\^\{([^}]*)\}', r'^\1', s)  # 保留其他指数
            # 处理剩余 \cmd{X} → X
            s = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', s)
            # 残留的 \cmd
            s = re.sub(r'\\[a-zA-Z]+', '', s)
            # 清理花括号
            s = s.replace('{', '').replace('}', '')
            s = s.replace('$$', '').replace('&', '')
            return s.strip()

        # 替换 Tex("...") / MathTex("...") / Tex(r"...") → Text("...")
        # 支持单引号、双引号、r前缀、f前缀等
        def _replace_tex(m: re.Match) -> str:
            prefix = m.group(1)  # Tex 或 MathTex
            quote = m.group(2)   # 引号字符
            content = m.group(3) # LaTeX 内容
            plain = _latex_to_plain(content)
            # 保留后续参数（font_size, color 等）
            return f'Text({quote}{plain}{quote}'

        # 匹配 Tex(r"...") 或 Tex("...") 等格式
        script = re.sub(
            r'\b(Tex|MathTex)\s*\(\s*(?:r|f)?(["\'])(.*?)\2',
            _replace_tex,
            script,
        )
        # 处理 Tex 变量赋值形式：如 label = Tex("...")
        # 已被上面覆盖。处理多参数情况：Tex("...", font_size=24) → Text("...", font_size=24)
        # 上面的正则已保留 ( 后的部分，font_size 等参数会自然保留

        # 修复7：self.wait() 负数/零值 → 最小值 0.1（Manim 要求 duration > 0）
        # LLM 可能生成 self.wait(duration - offset) 导致负数
        # 策略：将 self.wait(<=0) 替换为 self.wait(0.1)
        # 匹配 self.wait(数字) 或 self.wait(表达式)
        def _fix_wait_duration(s: str) -> str:
            # 先处理显式的负数/零数字：self.wait(-0.3), self.wait(0), self.wait(0.0)
            s = re.sub(r'self\.wait\s*\(\s*(-?\d*\.?\d+)\s*\)', lambda m: f'self.wait({max(0.1, float(m.group(1)))})', s)
            return s

        script = _fix_wait_duration(script)

        # 修复8：强制修正超出安全区域的位置坐标
        # 标题位置太高（UP * 3.5, UP * 4, .to_edge(UP)）→ 修正为 UP * 2.5
        # 内容位置太高（UP * 3, UP * 3.5）→ 修正为 UP * 2
        # 内容位置太低（DOWN * 4, DOWN * 5）→ 修正为 DOWN * 3
        def _fix_positions(s: str) -> str:
            # .to_edge(UP) → UP * 2.5（标题太高会被遮挡）
            s = re.sub(r'\.to_edge\s*\(\s*UP\s*\)', 'UP * 2.5', s)
            # UP * 4, UP * 3.5, UP * 3 → UP * 2.5（标题安全区）
            s = re.sub(r'UP\s*\*\s*4(?:\.0)?', 'UP * 2.5', s)
            s = re.sub(r'UP\s*\*\s*3\.5', 'UP * 2.5', s)
            s = re.sub(r'UP\s*\*\s*3(?:\.0)?(?![\.5])', 'UP * 2', s)  # 非标题内容
            # DOWN * 4, DOWN * 5, DOWN * 3.5 → DOWN * 3（底部安全区）
            s = re.sub(r'DOWN\s*\*\s*[4-9](?:\.0)?', 'DOWN * 3', s)
            s = re.sub(r'DOWN\s*\*\s*3\.5', 'DOWN * 3', s)
            # LEFT/RIGHT 超出范围（LEFT * 7, RIGHT * 7）→ LEFT * 6 / RIGHT * 6
            s = re.sub(r'LEFT\s*\*\s*[7-9](?:\.0)?', 'LEFT * 6', s)
            s = re.sub(r'RIGHT\s*\*\s*[7-9](?:\.0)?', 'RIGHT * 6', s)
            # buff=0.3 → buff=1.0（强制增大间距避免重叠）
            s = re.sub(r'buff\s*=\s*0\.3', 'buff=1.0', s)
            s = re.sub(r'buff\s*=\s*0\.5', 'buff=1.0', s)
            # buff=0 (无间距) → buff=1.0
            s = re.sub(r'buff\s*=\s*0(?![\.0-9])', 'buff=1.0', s)
            return s

        script = _fix_positions(script)

        if script != original:
            logger.info("已自动修复 LLM 脚本中的 Mobject API 误用（hasattr/get_cell/stroke_style/Create→FadeIn/Tex→Text/wait负值/位置修正/间距修正）")
        return script

    def render_video(self, script: str, scene_class: str, output_dir: str = VIDEO_OUTPUT_DIR) -> dict:
        """渲染Manim脚本为视频

        执行: manim -pql script.py SceneName
        返回视频文件路径
        """
        if not self._manim_available:
            logger.error("[MANIM FAILED] Manim未安装 | 请执行: pip install manim")
            return {
                "status": "failed",
                "message": "Manim 未安装。请安装: pip install manim",
                "script_content": script,
            }

        # 预处理脚本：将包含中文的 Text() 替换为 MarkupText() + 中文字体
        script = self._fix_chinese_text_in_script(script)
        # 预处理脚本：将 2D 坐标 (x, y) 转换为 3D 坐标 (x, y, 0)
        script = self._fix_2d_coordinates(script)
        # 预处理脚本：修复 LLM 常见 Mobject API 误用（hasattr 防御式三元、get_cell 误用等）
        script = self._fix_llm_mobject_bugs(script)

        # 写入临时脚本文件
        task_id = str(uuid.uuid4())[:8]
        script_dir = os.path.join(output_dir, f"tmp_{task_id}")
        os.makedirs(script_dir, exist_ok=True)
        script_path = os.path.join(script_dir, f"{scene_class}.py")

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)

        try:
            # 预渲染语法检查：用 py_compile 快速捕获 SyntaxError，避免浪费子进程启动时间
            import py_compile
            try:
                py_compile.compile(script_path, doraise=True)
                logger.info("[MANIM] 脚本语法检查通过 | path=%s", script_path)
            except py_compile.PyCompileError as e:
                logger.error("[MANIM FAILED] 脚本语法错误 | path=%s, error=%s", script_path, str(e))
                return {
                    "status": "failed",
                    "message": f"脚本语法错误: {e}",
                    "script_content": script,
                }

            # 使用 Manim Python API 渲染
            logger.info("[MANIM] 开始渲染子进程 | script_path=%s", script_path)
            video_path = self._render_with_manim_api(script, script_dir, scene_class)

            if video_path is None:
                logger.error("[MANIM FAILED] 渲染返回空路径 | script_dir=%s, scene_class=%s", script_dir, scene_class)
                return {
                    "status": "failed",
                    "message": "Manim渲染失败，请检查脚本语法或坐标格式",
                    "script_content": script,
                }

            # 移动到输出目录
            final_name = f"{scene_class}_{task_id}.mp4"
            final_path = os.path.join(output_dir, final_name)
            shutil.move(video_path, final_path)

            # 清理临时目录
            shutil.rmtree(script_dir, ignore_errors=True)

            logger.info("[MANIM SUCCESS] 渲染完成 | final_path=%s, size=%d bytes",
                       final_path, os.path.getsize(final_path) if os.path.exists(final_path) else 0)
            return {
                "status": "completed",
                "video_path": final_path,
                "video_url": f"/static/videos/{final_name}",
            }

        except subprocess.TimeoutExpired:
            logger.error("[MANIM FAILED] 渲染超时(5分钟) | scene_class=%s", scene_class)
            return {
                "status": "failed",
                "message": "Manim渲染超时（5分钟）",
                "script_content": script,
            }
        except Exception as e:
            import traceback
            logger.error("[MANIM FAILED] 渲染异常 | scene_class=%s, error=%s", scene_class, str(e))
            logger.error("[MANIM FAILED] Traceback: %s", traceback.format_exc())
            return {
                "status": "failed",
                "message": f"Manim渲染异常: {e}",
                "script_content": script,
            }

    def _render_with_remotion(self, script: str, scene_class: str, output_dir: str) -> dict:
        """使用 Remotion 渲染视频（Windows 降级方案）

        调用 remotion-service 的渲染接口
        """
        try:
            import requests

            remotion_service_url = "http://localhost:3000"  # Remotion 服务默认端口
            task_id = str(uuid.uuid4())[:8]

            # 准备渲染请求
            payload = {
                "scene_class": scene_class,
                "script": script,
                "output_path": os.path.join(output_dir, f"{scene_class}_{task_id}.mp4"),
            }

            logger.info("尝试 Remotion 降级渲染...")
            response = requests.post(
                f"{remotion_service_url}/render",
                json=payload,
                timeout=300
            )

            if response.status_code == 200:
                result = response.json()
                video_path = result.get("video_path")
                if video_path and os.path.exists(video_path):
                    logger.info(f"Remotion 渲染成功: {video_path}")
                    return {
                        "status": "completed",
                        "video_path": video_path,
                        "video_url": f"/static/videos/{os.path.basename(video_path)}",
                        "rendered_by": "remotion",
                    }

            logger.warning(f"Remotion 渲染失败: {response.status_code} - {response.text}")
            return {
                "status": "remotion_failed",
                "message": "Manim 和 Remotion 均不可用，无法生成视频。请安装 Manim: pip install manim",
                "script_content": script,
            }

        except requests.exceptions.ConnectionError:
            logger.error("Remotion 服务未启动，请先启动: cd C:\\Users\\24711\\Desktop\\remotion-service && npm start")
            return {
                "status": "remotion_not_available",
                "message": "Remotion 服务未启动。请先启动服务或安装 Manim: pip install manim",
                "script_content": script,
            }
        except Exception as e:
            logger.error(f"Remotion 渲染异常: {e}")
            return {
                "status": "failed",
                "message": f"视频渲染失败: {str(e)}",
                "script_content": script,
            }

    def _render_with_manim_api(self, script: str, script_dir: str, scene_class: str) -> Optional[str]:
        """使用 Manim Community Python API 渲染视频

        在独立子进程中渲染（避免 Manim 的 OpenGL/Cairo 与 uvicorn 事件循环冲突导致进程崩溃）。
        使用正斜杠路径避免 Windows 路径转义问题。
        """
        try:
            import subprocess

            # 构建渲染脚本，使用正斜杠路径和绝对路径
            # 确保所有路径都是绝对路径，避免 cwd 和 script_path 混乱
            abs_script_dir = os.path.abspath(script_dir)
            safe_script_dir = abs_script_dir.replace("\\", "/")

            render_code = f'''import sys, os, inspect
from manim import config, Scene

# Manim 内置 Scene 类名列表（需要排除）
BUILTIN_SCENES = [
    'Scene', 'MovingCameraScene', 'ZoomedScene', 'ThreeDScene',
    'LinearTransformationScene', 'VectorScene', 'GraphScene',
    'CodeScene', 'TableScene', 'NumberLineScene', 'SampleSpaceScene',
    'SpecialThreeDScene', 'ThreeDScene', 'Pendulum', 'InteractiveScene',
    'MobjectScene', 'ReconfigurableScene', 'DefaultScene'
]

# 使用 medium_quality (720p30) 保证画面清晰度
config.quality = "medium_quality"
config.output_file = "{scene_class}"
config.media_dir = "{safe_script_dir}/media"

script_path = "{safe_script_dir}/{scene_class}.py"
exec(open(script_path, encoding="utf-8").read(), globals())

scene_classes = [
    obj for name, obj in globals().items()
    if inspect.isclass(obj) and issubclass(obj, Scene) and obj is not Scene
    and obj.__name__.lower() == "{scene_class}".lower()
]

if not scene_classes:
    # 如果精确匹配失败，获取脚本定义的 Scene 子类（排除 Manim 内置类）
    scene_classes = [
        obj for name, obj in globals().items()
        if inspect.isclass(obj) and issubclass(obj, Scene) and obj is not Scene
        and obj.__name__ not in BUILTIN_SCENES
        and not any(obj.__name__.startswith(b) for b in ['Moving', 'Zoomed', 'ThreeD', 'Special', 'Linear', 'Vector', 'Graph', 'Code', 'Table', 'NumberLine', 'Sample', 'Pendulum', 'Interactive', 'Mobject', 'Reconfigurable', 'Default'])
    ]

if not scene_classes:
    print("ERROR: Scene class {scene_class} not found")
    sys.exit(1)

scene = scene_classes[0]()
scene.render()
print("RENDER_OK")
'''

            # 写入渲染脚本（使用绝对路径）
            render_script_path = os.path.join(abs_script_dir, "_render.py")
            with open(render_script_path, "w", encoding="utf-8") as f:
                f.write(render_code)

            # 在子进程中执行渲染（使用绝对路径，cwd 也使用绝对路径）
            # ffmpeg 在 Docker 中通过 apt-get 安装，已在默认 PATH 中

            result = subprocess.run(
                [sys.executable, render_script_path],
                capture_output=True,
                encoding='utf-8',
                errors='ignore',
                timeout=600,
                cwd=abs_script_dir,  # 使用绝对路径，避免路径混乱
                creationflags=CREATE_NO_WINDOW,
            )

            if result.returncode != 0:
                logger.error("Manim渲染进程退出码: %d", result.returncode)
                logger.error("stderr: %s", result.stderr[-800:])
                logger.error("stdout: %s", result.stdout[-800:])
                # 仍然检查视频文件是否存在（Manim有时崩溃但视频已生成）
            else:
                logger.info("Manim渲染完成: %s", scene_class)

            # 查找生成的视频文件
            video_path = self._find_rendered_video(script_dir, scene_class)
            if video_path:
                return video_path

            logger.error("未找到渲染输出的视频文件")
            return None

        except Exception as e:
            logger.error("Manim API渲染失败: %s", e)
            return None

    @staticmethod
    def _run_render_process(render_script_path: str) -> bool:
        """在子进程中运行渲染脚本"""
        import subprocess
        result = subprocess.run(
            [sys.executable, render_script_path],
            capture_output=True,
            text=True,
            timeout=300,
            creationflags=CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            logger.error("渲染进程错误 (exit=%d): %s", result.returncode, result.stderr[-500:])
            # Manim 有时返回非零退出码但实际已生成视频，不直接返回 False
            logger.warning("Manim退出码非零，但继续检查视频文件...")
        return True  # 继续检查视频文件

    def _find_rendered_video(self, script_dir: str, scene_class: str) -> Optional[str]:
        """查找Manim渲染输出的最终视频文件

        Manim输出结构：
        - media/videos/{script_name}/480p15/{SceneName}.mp4  ← 最终完整视频
        - media/videos/{script_name}/480p15/partial_movie_files/{SceneName}/*.mp4  ← 片段（不要！）

        必须返回最终完整视频，不能返回 partial_movie_files 里的片段。
        """
        media_dir = os.path.join(script_dir, "media")
        if not os.path.isdir(media_dir):
            return None

        # 优先查找最终完整视频（不在 partial_movie_files 目录中）
        # 路径模式: media/videos/*/480p15/{SceneName}.mp4 或 media/videos/*/480p30/...
        videos_dir = os.path.join(media_dir, "videos")
        if os.path.isdir(videos_dir):
            for quality_dir in os.listdir(videos_dir):
                quality_path = os.path.join(videos_dir, quality_dir)
                if not os.path.isdir(quality_path):
                    continue
                # 查找所有子目录中的最终视频
                for sub in os.listdir(quality_path):
                    sub_path = os.path.join(quality_path, sub)
                    if os.path.isdir(sub_path):
                        # 这是 partial_movie_files 目录，跳过
                        continue
                    # 这是视频文件 - 匹配任何 .mp4 文件（不精确匹配类名）
                    if sub.endswith(".mp4"):
                        logger.info("找到最终视频: %s", sub_path)
                        return sub_path

        # 降级：遍历查找，但排除 partial_movie_files 目录
        for root, dirs, files in os.walk(media_dir):
            # 跳过 partial_movie_files 目录
            if "partial_movie_files" in root:
                continue
            for f in files:
                if f.endswith(".mp4"):
                    logger.info("找到视频(降级): %s", os.path.join(root, f))
                    return os.path.join(root, f)

        logger.error("未找到最终视频文件（已排除partial_movie_files）")
        return None

    def generate_tts_audio(self, text: str, voice: str = "zh-CN-YunxiNeural", speed: int = 50) -> str:
        """生成旁白音频，根据voice自动选择TTS引擎

        Args:
            text: 旁白文本
            voice: 发音人（"zh-CN-*"用Edge TTS，其他用讯飞TTS）
            speed: 语速 0-100

        Returns:
            音频文件路径
        """
        service = get_tts_service(voice)
        if not service.available:
            logger.warning("TTS服务不可用: voice=%s，跳过音频生成", voice)
            return ""

        audio_id = str(uuid.uuid4())[:8]
        audio_path = os.path.join(VIDEO_OUTPUT_DIR, f"tts_{audio_id}.mp3")

        result = service.save_audio(text, audio_path, voice, speed)
        return result

    def combine_video_audio(self, video_path: str, audio_path: str, output_path: str) -> str:
        """合并视频和音频

        使用ffmpeg合并Manim视频和TTS音频。
        如果视频比音频短，自动循环视频以匹配音频时长。
        """
        if not self._ffmpeg_available:
            logger.warning("ffmpeg未安装，无法合并视频音频，返回原始视频")
            return video_path

        if not os.path.exists(video_path) or not os.path.exists(audio_path):
            logger.warning("视频或音频文件不存在，返回原始视频")
            return video_path

        try:
            # -stream_loop -1 让视频无限循环，-shortest 让输出在音频结束时停止
            # 注意：-stream_loop 必须在 -i video_path 之前；循环需要重新编码视频
            cmd = [
                "ffmpeg", "-y",
                "-stream_loop", "-1",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='ignore', timeout=120, creationflags=CREATE_NO_WINDOW)

            if result.returncode == 0 and os.path.exists(output_path):
                logger.info("视频音频合并成功: %s", output_path)
                return output_path
            else:
                logger.error("ffmpeg合并失败: %s", result.stderr[-200:])
                return video_path

        except Exception as e:
            logger.error("视频音频合并异常: %s", e)
            return video_path

    def generate_concept_video(self, knowledge_point: str, style: str = "rigorous", voice: str = "", with_tts: bool = True, progress_callback=None) -> dict:
        """音画同步视频生成流程 - 先生成TTS测实际时长，再传给Manim确保音画同步"""
        task_id = str(uuid.uuid4())[:8]
        task = VideoGenerationTask(task_id, knowledge_point, style)
        task.created_at = __import__("datetime").datetime.now().isoformat()
        self._save_task(task)

        try:
            # Step 1: LLM生成讲解脚本
            task.status = "generating"
            task.progress = 10
            task.message = "正在生成讲解脚本..."
            self._save_task(task)
            if progress_callback:
                progress_callback(10, "正在生成讲解脚本...")

            script = self._generate_narration_script(knowledge_point, style)
            task.script_content = json.dumps(script, ensure_ascii=False, indent=2)

            # Step 2: 先生成TTS音频并测量实际时长（关键改进！）
            task.progress = 25
            task.message = "正在生成TTS旁白..."
            self._save_task(task)
            if progress_callback:
                progress_callback(25, "正在生成TTS旁白...")

            audio_segments = []
            actual_durations = []
            tts_available = edge_tts_service.available or tts_service.available
            if with_tts and tts_available:
                style_config = STYLE_CONFIG.get(style, STYLE_CONFIG["rigorous"])
                use_voice = voice if voice else style_config["voice"]
                segments = script.get("segments", [])
                for i, segment in enumerate(segments):
                    audio_path = self._generate_tts_audio(
                        text=segment["narration"],
                        voice=use_voice,
                        speed=style_config["speed"],
                    )
                    if audio_path:
                        audio_segments.append(audio_path)
                        try:
                            from moviepy import AudioFileClip
                            clip = AudioFileClip(audio_path)
                            real_dur = clip.duration
                            clip.close()
                        except Exception:
                            real_dur = segment.get("duration", 5)
                        actual_durations.append(real_dur)
                        logger.info("TTS段%d: 预估%.1fs -> 实际%.1fs", i+1,
                                    segment.get("duration", 5), real_dur)
                    else:
                        actual_durations.append(segment.get("duration", 5))
                    task.progress = 25 + int(15 * (i + 1) / max(len(segments), 1))
                    self._save_task(task)
                    if progress_callback:
                        progress_callback(task.progress, f"TTS ({i+1}/{len(segments)})...")

            # Step 3: 用实际时长生成Manim代码
            task.progress = 45
            task.message = "正在生成Manim动画代码..."
            self._save_task(task)
            if progress_callback:
                progress_callback(45, "正在生成Manim动画代码...")

            manim_code = self._generate_manim_from_script_with_durations(
                knowledge_point, script, style, actual_durations
            )

            # 确定Scene类名 - 优先使用模板注册的类名，避免大小写不匹配
            # 确定Scene类名（与Manim代码中的class名一致）
            template = get_manim_template(knowledge_point)
            if template:
                scene_class = template["scene_class"]
            else:
                # ★ 生成合法的Scene类名（只包含ASCII字符）
                import re
                safe_class_name = re.sub(r'[^\w]', '', knowledge_point.replace(' ', '_'))
                if not safe_class_name or not re.match(r'^[a-zA-Z_]', safe_class_name):
                    safe_class_name = 'KnowledgePoint'
                scene_class = safe_class_name + "Scene"

            task.progress = 55
            task.message = "正在渲染Manim视频..."
            self._save_task(task)
            if progress_callback:
                progress_callback(55, "正在渲染Manim视频...")

            # Step 4: 渲染Manim视频（动画时长已匹配音频，音画同步）
            # 最多重试3次（LLM 生成的 Manim 脚本有随机性，可能含 NameError/SyntaxError）
            max_retries = 3
            render_result = None
            for attempt in range(max_retries):
                render_result = self.render_video(manim_code, scene_class)
                if render_result["status"] == "completed":
                    break
                if render_result["status"] in ("manim_not_available", "remotion_not_available", "remotion_failed"):
                    break  # 环境问题，重试无意义
                # 渲染失败，重新生成 Manim 代码重试
                if attempt < max_retries - 1:
                    err_msg = render_result.get("message", "")
                    logger.warning("Manim渲染失败(第%d次)，重新生成代码重试: %s", attempt + 1, err_msg)
                    if progress_callback:
                        progress_callback(55, f"渲染失败(第{attempt+1}次)，正在重新生成Manim代码重试...")
                    manim_code = self._generate_manim_from_script_with_durations(
                        knowledge_point, script, style, actual_durations
                    )
                else:
                    logger.error("Manim渲染失败，已用尽%d次重试", max_retries)

            if render_result["status"] in ("manim_not_available", "remotion_not_available", "remotion_failed"):
                task.status = "failed"
                task.message = render_result.get("message", "渲染不可用")
                task.script_content = render_result.get("script_content", "")
                task.progress = 55
                return task.to_dict()

            if render_result["status"] == "failed":
                task.status = "failed"
                task.message = render_result["message"]
                task.progress = 55
                return task.to_dict()

            video_path = render_result.get("video_path", "")
            if not video_path and "video_url" in render_result:
                video_url = render_result["video_url"]
                video_path = os.path.join(VIDEO_OUTPUT_DIR, os.path.basename(video_url))
            if not video_path:
                task.status = "failed"
                task.message = "渲染成功但未返回视频路径"
                task.progress = 55
                return task.to_dict()
            task.video_path = video_path
            task.progress = 80
            if progress_callback:
                progress_callback(80, "Manim视频渲染完成")

            task.progress = 90
            task.message = "正在拼接视频和音频..."
            self._save_task(task)
            if progress_callback:
                progress_callback(90, "正在拼接视频和音频...")

            # Step 5: 拼接视频+音频+SRT字幕（字幕时间轴基于实际TTS时长，音字同步）
            if audio_segments:
                narrations_for_video = [s["narration"] for s in script.get("segments", [])][:len(audio_segments)]
                final_path = self._compose_final_video(
                    video_path=video_path,
                    audio_segments=audio_segments,
                    narrations=narrations_for_video,
                    durations=actual_durations,
                    task_id=task_id,
                    knowledge_point=knowledge_point,
                    style=style,
                )
                if final_path:
                    task.video_path = final_path
                    task.video_url = f"/static/videos/{os.path.basename(final_path)}"
                    # VTT字幕文件URL（用于软字幕开关）
                    task.subtitle_url = f"/static/videos/subs_{task_id}.vtt"
                else:
                    task.video_url = f"/static/videos/{os.path.basename(video_path)}"
                    task.subtitle_url = f"/static/videos/subs_{task_id}.vtt"
            else:
                task.video_url = f"/static/videos/{os.path.basename(video_path)}"
                task.subtitle_url = ""  # 无音频时不生成字幕

            task.status = "completed"
            task.progress = 100
            task.message = "视频生成完成"

            # 缓存
            cache_key = f"{knowledge_point}_{style}"
            self._save_cache(cache_key, task.to_dict())
            self._save_task(task)

        except Exception as e:
            task.status = "failed"
            task.message = f"视频生成失败: {str(e)}"
            logger.error("视频生成失败: %s", e)
            self._save_task(task)

        return task.to_dict()

    # ===== 两步生成核心方法 =====

    def _generate_narration_script(self, knowledge_point: str, style: str = "rigorous") -> dict:
        """第1步：用LLM生成讲解脚本

        Returns:
            {
                "title": "知识点标题",
                "segments": [
                    {
                        "narration": "旁白文案",
                        "visual_description": "视觉描述（指导Manim动画）",
                        "duration": 8  # 秒
                    },
                    ...
                ]
            }
        """
        style_desc = {
            "rigorous": "严谨学术风格，注重原理推导和数学表达",
            "relaxed": "轻松活泼风格，用生活化比喻和幽默语言",
            "guided": "引导启发风格，通过提问引导学生思考",
            "whiteboard": "白板教学风格，像老师在黑板上边画边讲",
        }

        prompt = f"""请为知识点「{knowledge_point}」生成一个详细的教学视频分段讲解脚本。

讲解风格：{style_desc.get(style, style_desc['rigorous'])}

请严格按照以下JSON格式输出，不要输出其他内容：
{{
    "title": "{knowledge_point}讲解",
    "segments": [
        {{
            "narration": "这一段的旁白文案，用自然口语化的语言，像老师在讲课一样，内容详实",
            "visual_description": "这一段需要展示的动画内容描述，具体到每个图形、颜色、位置、动画过程",
            "duration": 20
        }}
    ]
}}

要求：
1. 分8-12个段落，覆盖知识点的各个方面
2. 每段旁白控制在60-150字（约20-40秒的讲解），内容要详实，不能太简略
3. 旁白用自然口语化的语言，像老师在讲课一样，要有完整的解释和过渡
4. visual_description要非常具体，指导Manim动画的呈现，包括：显示什么图形、如何变化、高亮什么、文字标注等
5. duration是每段的预估时长（秒），根据旁白长度合理估算，一般20-40秒
6. 内容结构建议（根据知识点学科性质灵活调整，不要套用单一学科模板）：
   - 段落1-2：概念引入（是什么、为什么需要）
   - 段落3-4：基本性质/特征/规则
   - 段落5-7：核心内容演示（根据学科选择合适的演示方式：理科用推导/运算，语言类用例句/语法，文科用案例/论证）
   - 段落8-9：对比/扩展/易混淆点辨析
   - 段落10-11：实际应用场景
   - 段落12：总结回顾
7. 总时长目标3-5分钟（180-300秒），确保内容充实完整"""

        try:
            result = llm_client.chat(
                messages=[
                    {"role": "system", "content": "你是教学视频脚本编写专家，擅长为任意学科知识点制作详细、系统的教学视频脚本。只输出JSON格式。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )
            script = json.loads(result)

            # 验证基本结构
            if "segments" not in script or not isinstance(script["segments"], list):
                raise ValueError("脚本缺少segments字段")

            for seg in script["segments"]:
                if "narration" not in seg:
                    seg["narration"] = ""
                if "visual_description" not in seg:
                    seg["visual_description"] = ""
                if "duration" not in seg:
                    seg["duration"] = 5

            logger.info("LLM讲解脚本生成成功: %s, %d段", knowledge_point, len(script["segments"]))
            return script

        except json.JSONDecodeError as e:
            logger.error("LLM讲解脚本JSON解析失败: %s", e)
            # 降级：返回默认脚本
            return {
                "title": f"{knowledge_point}讲解",
                "segments": [
                    {"narration": f"今天我们来学习{knowledge_point}。", "visual_description": f"显示标题：{knowledge_point}", "duration": 5},
                    {"narration": f"{knowledge_point}是一个非常重要的知识点。", "visual_description": "显示概念说明", "duration": 8},
                    {"narration": "让我们通过动画来理解它的工作原理。", "visual_description": "开始动画演示", "duration": 10},
                    {"narration": "以上就是关于这个知识点的讲解，希望大家能够理解。", "visual_description": "显示总结", "duration": 5},
                ],
            }
        except Exception as e:
            logger.error("LLM讲解脚本生成失败: %s", e)
            return {
                "title": f"{knowledge_point}讲解",
                "segments": [
                    {"narration": f"这是关于{knowledge_point}的讲解视频。", "visual_description": "显示标题", "duration": 10},
                ],
            }

    def _generate_manim_from_script_with_durations(
        self, knowledge_point: str, script: dict, style: str = "rigorous",
        actual_durations: list = None
    ) -> str:
        """用LLM生成Manim代码，传入实际TTS时长确保音画同步"""
        # 优先使用LLM生成（音画同步），失败时回退到模板
        if not actual_durations:
            # 没有实际时长，直接用模板或LLM生成
            template = get_manim_template(knowledge_point)
            if template:
                import re
                template_script = re.sub(r'#SEG_DUR_\d+#', '1.0', template["script"])
                return template_script
            return self._generate_manim_from_script(knowledge_point, script, style)

        # 尝试用LLM生成（音画同步的关键：每段self.wait精确匹配TTS时长）
        try:
            llm_script = self._generate_manim_with_llm_durations(knowledge_point, script, style, actual_durations)
            if llm_script:
                logger.info("LLM生成Manim脚本成功（音画同步）: %s", knowledge_point)
                return llm_script
        except Exception as e:
            logger.warning("LLM生成Manim脚本失败: %s，回退到模板", e)

        # 回退到模板，替换占位符为实际时长
        template = get_manim_template(knowledge_point)
        if template:
            logger.info("回退到预置Manim模板: %s（音画同步模式）", knowledge_point)
            template_script = template["script"]
            import re
            placeholders = re.findall(r'#SEG_DUR_(\d+)#', template_script)
            num_placeholders = len(placeholders)
            num_segments = len(actual_durations)
            logger.info("模板音画同步: %d段旁白, %d个占位符, 实际时长: %s",
                       num_segments, num_placeholders,
                       [f"{d:.1f}s" for d in actual_durations])
            for i in range(num_placeholders):
                if i < num_segments:
                    wait_time = max(actual_durations[i], 0.5)
                else:
                    wait_time = 1.0
                template_script = template_script.replace(
                    f'#SEG_DUR_{i}#', f'{wait_time:.1f}'
                )
            return template_script

        # 最终兜底：无模板时用LLM生成（无时长信息）
        return self._generate_manim_from_script(knowledge_point, script, style)

    def _generate_manim_with_llm_durations(
        self, knowledge_point: str, script: dict, style: str, actual_durations: list
    ) -> str:
        """用LLM根据实际TTS时长生成Manim脚本（音画同步）"""

        style_desc = {
            "rigorous": "严谨学术风格，注重原理推导和数学表达",
            "relaxed": "轻松活泼风格，用生活化比喻和幽默语言",
            "guided": "引导启发风格，通过提问引导学生思考",
            "whiteboard": "白板教学风格，像老师在黑板上边画边讲",
        }

        # 用实际TTS时长替代预估时长
        segments_desc = ""
        for i, seg in enumerate(script.get("segments", [])):
            real_dur = actual_durations[i] if i < len(actual_durations) else seg.get("duration", 5)
            segments_desc += f"\n段落{i+1}（{real_dur:.1f}秒 — TTS旁白实际时长，动画wait必须精确匹配）:\n"
            segments_desc += f"  旁白: {seg.get('narration', '')}\n"
            segments_desc += f"  视觉: {seg.get('visual_description', '')}\n"

        # ★ 生成合法的Scene类名（只包含ASCII字符，避免Windows文件系统错误）
        import re
        safe_class_name = re.sub(r'[^\w]', '', knowledge_point.replace(' ', '_'))
        # 如果全是中文或其他非ASCII字符，使用通用名称
        if not safe_class_name or not re.match(r'^[a-zA-Z_]', safe_class_name):
            safe_class_name = 'KnowledgePoint'
        class_name = safe_class_name + "Scene"

        prompt = f"""请根据以下讲解脚本，为知识点「{knowledge_point}」生成一个Manim动画脚本。

讲解风格：{style_desc.get(style, style_desc['rigorous'])}

讲解脚本（已标注每段TTS旁白的实际时长）：
{segments_desc}

核心原则：
- **画面只做图形动画演示，不要放大段解释性文字！** 旁白内容已通过字幕显示给观众。
- 画面只放：标题、关键术语标签（1-4个字）、图形结构（树、数组、箭头等）。
- 每段的动画步骤必须精确对应上述「视觉」描述，按描述的顺序逐个展示。

要求：
1. 使用Manim Community版本语法（from manim import *）
2. 白底黑字简笔画风格：self.camera.background_color = WHITE，所有文字和线条颜色用BLACK
3. 创建一个Scene类，类名必须严格为{class_name}（注意大小写必须完全一致，不要把缩写改成全大写）
4. 动画严格按上述每段的「视觉」描述顺序展示
5. **关键：每段结束时用self.wait(duration)，duration必须精确等于标注的TTS实际时长**
6. 结构：标题 → 每段对应的图形动画 → 总结（仅关键字）
7. 使用Square/Rectangle/Circle/Arrow/Line等图形对象
8. 用颜色高亮（**只使用以下Manim预定义颜色：BLACK, WHITE, RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE, PINK, TEAL, MAROON**）
   - YELLOW=比较/查找中
   - RED=不符合（需要旋转/交换）
   - GREEN=符合/完成
   - **禁止使用 DARK_GREEN、DARK_RED 等非标准颜色名称！**
9. 每段旁白对应的动画步骤用注释标明"段落N"
10. **画面文字只用作短标签：MarkupText("左子树", font="Microsoft YaHei", color=BLACK)，不超过5个字**
11. **纯英文术语用 Text()：Text("BST", color=BLACK)**
12. **禁止在画面放整句中文解释！解释性内容由字幕承载，画面只管图形动画**
13. 每段动画3-5个步骤，逐步构建图形结构
14. **【重要逻辑规则】循环中访问列表/数组元素时，必须确保元素已存在！**
    - 错误示例：for i in range(3): nodes.add(circle); if i < 2: arrow = Arrow(nodes[i+1])  # nodes[i+1]在第一次迭代时还不存在！
    - 正确做法：先创建所有元素，再在第二个循环中添加箭头连接；或使用临时变量保存下一个元素的位置
    - 规则：任何时候访问 list[i+1] 或 list[i-1] 时，必须确保该索引的元素已经被添加到列表中
15. **【重要布局规则】画面简洁，避免重叠！关键原则：少即是多**
    - **【核心规则】每段画面最多显示 3-5 个可见元素（图形+标签），不要堆砌过多内容！**
    - **【核心规则】元素间距必须 >= 1.0，使用 buff=1.0 或更大的值，不要用 buff=0.3**
    - **【核心规则】添加新元素前，必须先移除或淡出旧元素：self.play(FadeOut(old_elements))**
    - 画面坐标系：LEFT/RIGHT 水平方向（范围-6到6），UP/DOWN 垂直方向（范围-2.5到3）
    - 标题位置：UP * 2（固定值，不要用 .to_edge(UP) 或 UP * 3）
    - 主图形位置：DOWN * 0.5 到 UP * 1（中央区域）
    - 标签位置：图形旁边至少 1.0 距离：.next_to(obj, direction, buff=1.0)
    - 多个图形横向排列：LEFT * 4, LEFT * 2, ORIGIN, RIGHT * 2, RIGHT * 4（间距 2）
    - 多个图形纵向排列：UP * 1.5, DOWN * 0.5, DOWN * 2.5（间距 2）
    - **禁止在同一画面叠加多层图形！每段只展示一个核心概念**
    - **禁止动态添加元素而不移除旧元素！动画流程：FadeIn(新) → 展示 → FadeOut(旧) → FadeIn(下一组)**
    - **如果必须同时显示多个元素，总数量不超过 5 个，且必须均匀分布在画面中**
    - 垂直安全区域：UP * 2 到 DOWN * 3
    - 水平安全区域：LEFT * 5 到 RIGHT * 5
16. **【关键API规则】禁止把Python列表直接传给 .next_to() / .move_to() / .shift()！**
    - 错误示例：label.next_to(boxes, DOWN)  # boxes 是 list，会触发 ValueError: setting an array element with a sequence
    - 正确做法：label.next_to(Group(*boxes), DOWN)  # 用 Group 包裹列表
    - 或访问单个元素：label.next_to(boxes[-1], DOWN)
    - 任何 .next_to(var, ...) 调用，var 必须是单个 Mobject，不能是 list/tuple
17. **【关键API规则】禁止用 hasattr(obj, 'get_X') 做防御性检查访问Manim属性！**
    - Manim 的 Mobject.__getattr__ 会对任何 'get_*' 前缀返回 lambda，导致 hasattr 永远返回 True
    - 错误示例：text = obj.get_tex_string() if hasattr(obj, 'get_tex_string') else obj.text  # hasattr 返回 True，但调用时报 AttributeError: ... has no attribute 'tex_string'
    - 正确做法：直接用 obj.text 访问文本内容（Text/MarkupText/Tex 都有 .text 属性）
    - 规则：访问文本一律用 .text，不要写 hasattr 防御式三元表达式
18. **【关键API规则】Table 取单元格内容用 get_entries()，不要用 get_cell()！**
    - table.get_cell((row, col)) 返回的是边框 Rectangle（没有 .text 属性）
    - table.get_entries((row, col)) 返回的是单元格内容 mobject（Tex/Text，有 .text 属性）
    - 错误示例：cell = table.get_cell((1, 2)); text = cell.text  # AttributeError
    - 正确示例：cell = table.get_entries((1, 2)); text = cell.text
    - 注意：Table 行列索引从 1 开始（行 1 是表头）
    - 推荐做法：直接用源数据列表的内容判断，避免访问 mobject 属性。例如：
      for row_idx in range(2, 7):  # 数据行 2-6
          row_data = data[row_idx - 2]
          for col_idx in [2, 3, 4]:
              cell_text = row_data[col_idx - 1]  # 直接从源数据取
              cell = table.get_entries((row_idx, col_idx))
              if "n²" in cell_text: cell.set_fill(RED, 0.2)
19. **【关键变量规则】变量名必须完整且一致，禁止简写！**
    - 定义变量时使用完整描述性名称：compare_table, data_array, node_group, result_text
    - 引用变量时必须使用完整定义的名称，不能用缩写或部分名称
    - 错误示例：compare_table = Table(...); bubble_row = compare.get_entries(...)  # compare 未定义！应该是 compare_table
    - 错误示例：data_array = [...]; for item in data: ...  # data 未定义！应该是 data_array
    - 正确示例：compare_table = Table(...); bubble_row = compare_table.get_entries((2, 1))
    - 规则：任何变量引用前，必须回看该变量是否在之前完整定义过
    - 禁止凭记忆使用缩写：如果定义了 xxx_table，后续必须写 xxx_table，不能写 xxx
    - 禁止凭记忆使用前缀：如果定义了 xxx_data，后续必须写 xxx_data，不能写 xxx
20. **【关键动画规则】禁止使用 Create() / Write() / Uncreate()，必须用 FadeIn() / FadeOut()！**
    - Create/Write 对部分 Mobject（如 Table、Group）会抛 NotImplementedError
    - 全部使用 FadeIn(mobject) 和 FadeOut(mobject)，兼容所有类型
21. **【关键文字规则】禁止使用 Tex() / MathTex()，必须用 Text() 或 MarkupText()！**
    - 本系统未安装 LaTeX 编译器，Tex/MathTex 会触发 FileNotFoundError
    - 中文标签：MarkupText("冒泡排序", font="Microsoft YaHei", color=BLACK)
    - 英文/数学符号：Text("O(n²)", color=BLACK) — 直接用 Unicode 符号（² ³ √ ×）
    - 禁止写 Tex(r"$O(n^2)$") 或 MathTex("x^2")
22. **【关键等待规则】self.wait() 的 duration 必须大于 0！**
    - 错误示例：self.wait(duration - offset)  # 如果 offset > duration，结果为负数
    - 正确示例：self.wait(max(0.1, duration - offset)) 或直接用固定的正数
    - Manim 要求 wait duration > 0，负数或零会抛 ValueError
23. **【关键API规则】禁止使用 self.mobjects_from_animations！此API在Manim Community 0.19.0中不存在！**
    - 错误示例：for line in self.mobjects_from_animations:
    - 正确做法：for line in self.mobjects:  # 使用 self.mobjects 访问场景中的所有Mobject
    - self.mobjects_from_animations 会导致 AttributeError，必须用 self.mobjects 替代
24. **【关键文字规则】MarkupText 中禁止使用 Pango 特殊字符：→ ← ↑ ↓ ≤ ≥ × 等！**
    - MarkupText 使用 Pango XML 解析，这些字符会被误解析导致 ValueError
    - 错误示例：MarkupText("6<8 → 左")  # ← 和 → 导致 Pango 报错
    - 正确做法：MarkupText("6小于8, 走左边") 或 MarkupText("6&lt;8, 左")  # 用中文替代或XML转义
    - < 必须写成 &lt;，> 必须写成 &gt;，& 必须写成 &amp;
    - → 用 "变为" 或 "到" 替代；← 用 "来自" 替代
    - 不要在 MarkupText 的文本内容中使用任何箭头符号

请直接输出完整的Python脚本，不要其他解释。脚本必须可以独立运行。"""

        def _validate_script(code: str) -> bool:
            try:
                compile(code, "<manim_script>", "exec")
                return True
            except SyntaxError as e:
                logger.error("Manim脚本语法错误: %s (line %d)", e.msg, e.lineno)
                return False

        def _call_llm(p: str, tokens: int) -> str:
            r = llm_client.chat(
                messages=[{"role": "user", "content": p}],
                temperature=0.3,
                max_tokens=tokens,
            )
            if "```python" in r:
                r = r.split("```python")[1].split("```")[0]
            elif "```" in r:
                r = r.split("```")[1].split("```")[0]
            return r.strip()

        try:
            result = _call_llm(prompt, 8000)
            if _validate_script(result):
                return result
            logger.warning("Manim脚本语法不完整，重试（要求更简洁）")
            retry_prompt = prompt + "\n\n注意：上一次生成的脚本被截断了。请确保脚本完整可运行，可以适当精简每段的动画步骤，但必须覆盖所有段落。"
            result = _call_llm(retry_prompt, 8000)
            if _validate_script(result):
                return result
            logger.error("Manim脚本2次重试均失败，回退到原有方法")
            return self._generate_manim_from_script(knowledge_point, script, style)
        except Exception as e:
            logger.error("Manim脚本生成异常: %s", e)
            return self._generate_manim_from_script(knowledge_point, script, style)

    def _generate_manim_from_script(self, knowledge_point: str, script: dict, style: str = "rigorous") -> str:
        """第2步：用LLM根据讲解脚本生成Manim Python代码

        Args:
            knowledge_point: 知识点名称
            script: _generate_narration_script() 返回的讲解脚本
            style: 讲解风格

        Returns:
            Manim Python脚本代码
        """
        # 优先使用预置模板
        template = get_manim_template(knowledge_point)
        if template:
            logger.info("使用预置Manim模板: %s", knowledge_point)
            import re
            return re.sub(r'#SEG_DUR_\d+#', '1.0', template["script"])

        style_desc = {
            "rigorous": "严谨学术风格，注重原理推导和数学表达",
            "relaxed": "轻松活泼风格，用生活化比喻和幽默语言",
            "guided": "引导启发风格，通过提问引导学生思考",
            "whiteboard": "白板教学风格，像老师在黑板上边画边讲",
        }

        # 将脚本中的视觉描述整理给LLM
        segments_desc = ""
        for i, seg in enumerate(script.get("segments", [])):
            segments_desc += f"\n段落{i+1}（{seg.get('duration', 5)}秒）:\n"
            segments_desc += f"  旁白: {seg.get('narration', '')}\n"
            segments_desc += f"  视觉: {seg.get('visual_description', '')}\n"

        # ★ 生成合法的Scene类名（只包含ASCII字符）
        import re
        safe_class_name = re.sub(r'[^\w]', '', knowledge_point.replace(' ', '_'))
        if not safe_class_name or not re.match(r'^[a-zA-Z_]', safe_class_name):
            safe_class_name = 'KnowledgePoint'
        class_name = safe_class_name + "Scene"

        prompt = f"""请根据以下讲解脚本，为知识点「{knowledge_point}」生成一个Manim动画脚本。

讲解风格：{style_desc.get(style, style_desc['rigorous'])}

讲解脚本：
{segments_desc}

核心原则：
- **画面只做图形动画演示，不要放大段解释性文字！** 旁白内容已通过字幕显示给观众。
- 画面只放：标题、关键术语标签（1-4个字）、图形结构。
- 每段的动画步骤必须精确对应上述「视觉」描述，按顺序逐个展示。

要求：
1. 使用Manim Community版本语法（from manim import *）
2. 白底黑字简笔画风格：self.camera.background_color = WHITE，所有文字和线条颜色用BLACK
3. 创建一个Scene类，类名必须严格为{class_name}（注意大小写必须完全一致，不要把缩写改成全大写）
4. 动画严格按上述每段的「视觉」描述顺序展示
5. 每段结束时用self.wait(duration)，duration对应脚本中的时长
6. 结构：标题 → 每段对应的图形动画 → 总结（仅关键字）
7. 使用Square/Rectangle/Circle/Arrow/Line等图形对象
8. 用颜色高亮关键元素（**只使用以下Manim预定义颜色：BLACK, WHITE, RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE, PINK, TEAL, MAROON**）
   - YELLOW表示比较/查找中
   - RED表示不符合（需要旋转/交换）
   - GREEN表示符合/完成
   - **禁止使用 DARK_GREEN、DARK_RED 等非标准颜色名称！**
9. 每段旁白对应的动画步骤用注释标明"段落N"
10. **画面文字只用作短标签：MarkupText("左子树", font="Microsoft YaHei", color=BLACK)，不超过5个字**
11. **纯英文术语用 Text()：Text("BST", color=BLACK)**
12. **禁止在画面放整句中文解释！解释性内容由字幕承载，画面只管图形动画**
13. 每段动画3-5个步骤，逐步构建图形结构
14. **【关键API规则】禁止使用 self.mobjects_from_animations！此API在Manim Community 0.19.0中不存在！**
    - 错误示例：for line in self.mobjects_from_animations:
    - 正确做法：for line in self.mobjects:  # 使用 self.mobjects 访问场景中的所有Mobject
    - self.mobjects_from_animations 会导致 AttributeError，必须用 self.mobjects 替代
15. **【关键文字规则】MarkupText 中禁止使用 Pango 特殊字符：→ ← ↑ ↓ ≤ ≥ × 等！**
    - MarkupText 使用 Pango XML 解析，这些字符会被误解析导致 ValueError
    - 错误示例：MarkupText("6<8 → 左")  # ← 和 → 导致 Pango 报错
    - 正确做法：MarkupText("6小于8, 走左边") 或 MarkupText("6&lt;8, 左")
    - < 必须写成 &lt;，> 必须写成 &gt;，& 必须写成 &amp;
    - → 用 "变为" 或 "到" 替代；← 用 "来自" 替代

请直接输出完整的Python脚本，不要其他解释。脚本必须可以独立运行。
重要：脚本要完整覆盖所有段落。每段动画要有3-5个动画步骤，详细展示过程。"""

        def _validate_script(code: str) -> bool:
            """校验脚本语法是否完整（未被截断）"""
            try:
                compile(code, "<manim_script>", "exec")
                return True
            except SyntaxError as e:
                logger.error("Manim脚本语法错误: %s (line %d)", e.msg, e.lineno)
                return False

        def _call_llm(p: str, tokens: int) -> str:
            r = llm_client.chat(
                messages=[{"role": "user", "content": p}],
                temperature=0.3,
                max_tokens=tokens,
            )
            if "```python" in r:
                r = r.split("```python")[1].split("```")[0]
            elif "```" in r:
                r = r.split("```")[1].split("```")[0]
            return r.strip()

        try:
            # 第一次尝试：max_tokens=8000
            result = _call_llm(prompt, 8000)
            if _validate_script(result):
                return result

            # 第二次尝试：要求更简洁
            logger.warning("Manim脚本语法不完整，重试（要求更简洁）")
            retry_prompt = prompt + "\n\n注意：上一次生成的脚本被截断了。请确保脚本完整可运行，可以适当精简每段的动画步骤，但必须覆盖所有段落。优先保证脚本能完整运行。"
            result = _call_llm(retry_prompt, 8000)
            if _validate_script(result):
                return result

            # 第三次尝试：极简版本
            logger.warning("Manim脚本仍不完整，生成极简版本")
            simple_prompt = f"""为「{knowledge_point}」生成一个极简Manim脚本。类名{class_name}。白底黑字。只包含标题、3-4个核心概念展示、总结。不要复杂动画。中文用MarkupText("中文", font="Microsoft YaHei", color=BLACK)。纯英文专业术语用Text("BST", color=BLACK)。直接输出Python代码。"""
            result = _call_llm(simple_prompt, 6000)
            if _validate_script(result):
                return result

            logger.error("Manim脚本3次重试均失败，返回兜底脚本")
            # 返回一个最小可运行脚本
            return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
        self.camera.background_color = WHITE
        title = MarkupText("{knowledge_point}", font="Microsoft YaHei", color=BLACK, font_size=40).to_edge(UP)
        self.play(Write(title))
        self.wait(1)
        note = MarkupText("请安装Manim后渲染此脚本", font="Microsoft YaHei", color=BLACK, font_size=24).shift(DOWN)
        self.play(Write(note))
        self.wait(2)
'''
        except Exception as e:
            logger.error("LLM生成Manim脚本失败: %s", e)
            return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
        self.camera.background_color = WHITE
        title = MarkupText("{knowledge_point}", font="Microsoft YaHei", color=BLACK, font_size=40).to_edge(UP)
        self.play(Write(title))
        self.wait(1)
        note = MarkupText("请安装Manim后渲染此脚本", font="Microsoft YaHei", color=BLACK, font_size=24).shift(DOWN)
        self.play(Write(note))
        self.wait(2)
'''

    def _generate_tts_audio(self, text: str, voice: str = "zh-CN-YunxiNeural", speed: int = 50) -> str:
        """调用TTS生成音频，根据voice自动选择Edge TTS或讯飞TTS

        Args:
            text: 旁白文本
            voice: 发音人
                - "zh-CN-*"开头：使用Edge TTS（微软Azure神经网络，自然度高）
                - 其他：使用讯飞TTS
            speed: 语速 0-100（50=正常）

        Returns:
            音频文件路径
        """
        # 根据发音人选择TTS服务
        service = get_tts_service(voice)
        if not service.available:
            logger.error("[TTS FAILED] 服务不可用 | voice=%s, service_type=%s", voice, type(service).__name__)
            return ""

        audio_id = str(uuid.uuid4())[:8]
        audio_path = os.path.join(VIDEO_OUTPUT_DIR, f"tts_{audio_id}.mp3")

        try:
            result = service.save_audio(text, audio_path, voice, speed)
            if result and os.path.exists(result):
                file_size = os.path.getsize(result)
                logger.info("[TTS SUCCESS] 音频生成成功 | voice=%s, path=%s, size=%d bytes", voice, result, file_size)
                return result
            else:
                logger.error("[TTS FAILED] 音频生成失败 | voice=%s, text=%s", voice, text[:50])
                return ""
        except Exception as e:
            logger.error("[TTS FAILED] 音频生成异常 | voice=%s, error=%s", voice, str(e))
            return ""

    @staticmethod
    def _make_subtitle_clip(text: str, video_width: int, video_height: int, duration: float):
        """用 Pillow 生成字幕图片，返回 MoviePy ImageClip

        样式对标 Remotion Subtitle 组件，但使用不透明背景确保在白色Manim视频上清晰可见：
        - 深色不透明背景 + 圆角
        - 浅灰白色文字 #E8ECF4
        - 底部居中

        Args:
            text: 字幕文本
            video_width: 视频宽度（像素）
            video_height: 视频高度（像素）
            duration: 字幕显示时长（秒）

        Returns:
            MoviePy ImageClip 或 None
        """
        try:
            from PIL import Image, ImageDraw, ImageFont, ImageFilter
            import numpy as np
            from moviepy import ImageClip as _ImageClip

            # ★ 字体路径跨平台适配
            # Windows: C:/Windows/Fonts/msyh.ttc
            # Linux: fonts-noto-cjk 安装路径（Dockerfile 已安装）
            import platform
            if platform.system() == "Windows":
                font_path = "C:/Windows/Fonts/msyh.ttc"
            else:
                # 尝试多个 Linux 中文字体路径
                candidate_paths = [
                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
                ]
                font_path = ""
                for p in candidate_paths:
                    if os.path.exists(p):
                        font_path = p
                        break
            # 按视频分辨率缩放（Remotion 是 1920x1080）
            scale = video_width / 1920
            font_size = max(int(32 * scale), 16)
            pad_y = max(int(18 * scale), 8)
            pad_x = max(int(44 * scale), 16)
            radius = max(int(16 * scale), 6)
            bottom_offset = max(int(60 * scale), 20)

            try:
                font = ImageFont.truetype(font_path, font_size)
            except Exception:
                font = ImageFont.load_default()

            # 如果文字太长，自动换行
            max_width = int(video_width * 0.85)
            dummy_img = Image.new("RGBA", (1, 1))
            dummy_draw = ImageDraw.Draw(dummy_img)

            # 简单换行处理：按字符数估算
            chars_per_line = max(max_width // (font_size // 2), 10)
            if len(text) > chars_per_line:
                # 按中文字符换行
                lines = []
                current = ""
                for ch in text:
                    current += ch
                    if len(current) >= chars_per_line and ch in "，。、；：！？ ":
                        lines.append(current)
                        current = ""
                if current:
                    lines.append(current)
                display_text = "\n".join(lines)
            else:
                display_text = text

            # 测量文字大小（多行）
            bbox = dummy_draw.textbbox((0, 0), display_text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            # 字幕图片尺寸
            img_w = min(text_w + pad_x * 2, max_width)
            img_h = text_h + pad_y * 2

            # 创建画布（不透明深色背景）
            img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # 画不透明深色圆角背景（确保在白色视频上清晰可见）
            draw.rounded_rectangle(
                [(0, 0), (img_w - 1, img_h - 1)],
                radius=radius,
                fill=(15, 15, 25, 255),  # 深色不透明背景
            )

            # 画文字（#E8ECF4 = rgb(232, 236, 244)）
            text_x = (img_w - text_w) // 2
            text_y = pad_y
            draw.text((text_x, text_y), display_text, font=font, fill=(232, 236, 244, 255))

            # 转为 MoviePy ImageClip
            clip = _ImageClip(np.array(img), transparent=True)
            clip = clip.with_duration(duration)
            # 底部居中，距离底部 bottom_offset
            pos_x = 'center'
            pos_y = video_height - img_h - bottom_offset
            clip = clip.with_position((pos_x, pos_y))
            logger.info("字幕clip生成: text='%s' dur=%.1f size=%dx%d pos_y=%d",
                       text[:20], duration, img_w, img_h, pos_y)
            return clip

        except Exception as e:
            logger.error("Pillow字幕生成失败: %s", e, exc_info=True)
            return None

    def _compose_final_video(
        self,
        video_path: str,
        audio_segments: list[str],
        narrations: list[str],
        durations: list[float],
        task_id: str = "",
        knowledge_point: str = "",
        style: str = "rigorous",
    ) -> Optional[str]:
        """ffmpeg拼接视频+音频+字幕（不拉伸，视频内容已覆盖全部旁白）

        方案：LLM已按每段旁白生成对应动画，Manim视频时长已匹配。
        这里只做简单拼接：合并音频 + 添加字幕，用-shortest自动对齐。

        Args:
            video_path: Manim渲染的视频文件路径
            audio_segments: TTS音频文件路径列表
            narrations: 每段旁白文本列表
            durations: 每段时长列表（秒）
            task_id: 任务ID
            knowledge_point: 知识点名称
            style: 讲解风格

        Returns:
            最终视频文件路径，失败返回None
        """
        try:
            # ★ 优先使用系统 ffmpeg（Docker 容器已安装 ffmpeg apt 包）
            # 避免依赖 imageio_ffmpeg 下载的二进制（Linux 平台可能下载失败）
            ffmpeg_exe = shutil.which("ffmpeg")
            if not ffmpeg_exe:
                try:
                    from imageio_ffmpeg import get_ffmpeg_exe
                    ffmpeg_exe = get_ffmpeg_exe()
                except ImportError:
                    logger.error("[COMPOSE FAILED] ffmpeg 未安装且 imageio_ffmpeg 不可用")
                    return None
            logger.info("[COMPOSE] 使用 ffmpeg: %s", ffmpeg_exe)

            # Step 1: 合并音频
            merged_audio_path = os.path.join(VIDEO_OUTPUT_DIR, f"merged_{task_id}.mp3")
            if not self._merge_audio_files(audio_segments, merged_audio_path):
                logger.error("音频合并失败")
                return None

            # Step 2: 获取视频尺寸
            video_w, video_h = self._get_video_size(ffmpeg_exe, video_path)
            logger.info("视频尺寸: %dx%d", video_w, video_h)

            # Step 3: 生成SRT字幕文件（时间轴基于实际音频段时长）
            seg_starts = []
            seg_durations = []
            current_start = 0.0
            for i, audio_path in enumerate(audio_segments):
                if not os.path.exists(audio_path):
                    continue
                seg_dur = durations[i] if i < len(durations) else 5
                seg_starts.append(current_start)
                seg_durations.append(seg_dur)
                current_start += seg_dur
            srt_path = os.path.join(VIDEO_OUTPUT_DIR, f"subs_{task_id}.srt")
            self._generate_srt_file(srt_path, narrations, seg_starts, seg_durations)

            # Step 4: 获取音频时长，用于指定视频时长
            probe_cmd = [ffmpeg_exe, '-i', merged_audio_path, '-f', 'null', '-']
            probe_result = subprocess.run(probe_cmd, capture_output=True, encoding='utf-8', errors='ignore', timeout=60, creationflags=CREATE_NO_WINDOW)
            audio_duration = 0.0
            for line in probe_result.stderr.split('\n'):
                if 'Duration:' in line:
                    time_str = line.split('Duration:')[1].split(',')[0].strip()
                    parts = time_str.split(':')
                    audio_duration = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                    break
            logger.info("音频时长: %.2f秒", audio_duration)

            # Step 5: ffmpeg合成：视频 + 音频 + 字幕烧录，使用音频时长
            # Windows文件名净化：移除非法字符
            safe_knowledge_point = knowledge_point.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_').replace('（', '_').replace('）', '_')
            final_name = f"{safe_knowledge_point}_{style}_{task_id or str(uuid.uuid4())[:8]}.mp4"
            final_path = os.path.join(VIDEO_OUTPUT_DIR, final_name)

            scale = video_w / 1920
            font_size = max(int(20 * scale), 12)
            # MarginV: 根据视频分辨率动态计算底部边距（避开进度条）
            # 1080p: 60px, 720p: 40px, 480p: 20px
            margin_v = max(int(60 * scale), 20)

            # ★ 字体选择：Linux 用 Noto Sans CJK，Windows 用 Microsoft YaHei
            # Dockerfile 安装了 fonts-noto-cjk，但容器中没有 Microsoft YaHei
            # ffmpeg subtitles filter 需要 libass，FontName 必须是系统可用字体
            import platform
            if platform.system() == "Windows":
                subtitle_font = "Microsoft YaHei"
            else:
                # Linux: fonts-noto-cjk 安装的字体名
                subtitle_font = "Noto Sans CJK SC"

            force_style = (
                f"FontName={subtitle_font},"
                f"FontSize={font_size},"
                f"PrimaryColour=&H00000000,"
                f"BackColour=&H99FFFFFF,"
                f"Outline=0,Shadow=0,"
                f"BorderStyle=4,Alignment=2,"  # ffmpeg底部居中（行业标准，不遮挡画面）
                f"MarginV={margin_v},"
                f"MarginL=50,MarginR=50"  # 左右留白确保居中
            )

            # Windows路径需要特殊处理：转义冒号和反斜杠
            srt_escaped = srt_path.replace('\\', '/').replace(':', '\\:')
            
            # 获取视频时长，用于判断是否需要扩展
            video_duration = self._get_video_duration(ffmpeg_exe, video_path)
            logger.info("视频时长: %.2f秒, 音频时长: %.2f秒", video_duration, audio_duration)
            
            # 如果视频时长不足，使用tpad filter扩展视频（冻结最后一帧）
            if video_duration < audio_duration:
                pad_duration = audio_duration - video_duration
                video_filter = f"tpad=stop_mode=clone:stop_duration={pad_duration:.2f},subtitles='{srt_escaped}':force_style='{force_style}',fps=30"
                logger.info("视频时长不足，添加%.2f秒静止帧", pad_duration)
            else:
                video_filter = f"subtitles='{srt_escaped}':force_style='{force_style}',fps=30"

            # 使用 -vf 和 subtitles filter
            cmd = [
                ffmpeg_exe, '-y',
                '-i', video_path,
                '-i', merged_audio_path,
                '-vf', video_filter,
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
                '-c:a', 'aac', '-b:a', '128k',
                '-t', str(audio_duration),
                final_path,
            ]

            logger.info("ffmpeg合成: 视频+音频+字幕")
            result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='ignore', timeout=600, creationflags=CREATE_NO_WINDOW)
            final_result = None

            if result.returncode != 0:
                logger.warning("ffmpeg字幕合成失败: %s，回退到无字幕合成", result.stderr[-500:])
                # 回退：不加字幕，仅合并视频和音频，使用音频时长
                # 如果视频时长不足，添加静止帧
                if video_duration < audio_duration:
                    pad_duration = audio_duration - video_duration
                    vf_fallback = f"tpad=stop_mode=clone:stop_duration={pad_duration:.2f},fps=30"
                    cmd_fallback = [
                        ffmpeg_exe, '-y',
                        '-i', video_path,
                        '-i', merged_audio_path,
                        '-vf', vf_fallback,
                        '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
                        '-c:a', 'aac', '-b:a', '128k',
                        '-t', str(audio_duration),
                        final_path,
                    ]
                else:
                    cmd_fallback = [
                        ffmpeg_exe, '-y',
                        '-i', video_path,
                        '-i', merged_audio_path,
                        '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
                        '-c:a', 'aac', '-b:a', '128k',
                        '-t', str(audio_duration),
                        final_path,
                    ]
                logger.info("执行回退合成命令: %s", ' '.join(cmd_fallback))
                result2 = subprocess.run(cmd_fallback, capture_output=True, encoding='utf-8', errors='ignore', timeout=600, creationflags=CREATE_NO_WINDOW)
                if result2.returncode != 0:
                    logger.error("ffmpeg无字幕合成也失败: %s", result2.stderr[-500:])
                else:
                    final_result = final_path
                    logger.info("回退合成成功")
            else:
                final_result = final_path

            # 验证输出文件包含音频流
            if final_result and os.path.exists(final_path):
                probe = subprocess.run(
                    [ffmpeg_exe, '-i', final_path],
                    capture_output=True, encoding='utf-8', errors='ignore',
                    creationflags=CREATE_NO_WINDOW,
                )
                if 'Audio:' not in probe.stderr:
                    logger.error("输出视频缺少音频流")
                    final_result = None

            # 清理临时文件（无论成功或失败都清理SRT和合并音频）
            for f in [merged_audio_path, srt_path]:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception:
                    pass

            if final_result:
                logger.info("视频合成完成: %s", final_path)
            return final_result

        except subprocess.TimeoutExpired:
            logger.error("ffmpeg合成超时")
            return None
        except Exception as e:
            logger.error("视频合成异常: %s", e)
            return None

    @staticmethod
    def _get_video_size(ffmpeg_exe, video_path):
        """获取视频的宽高"""
        r = subprocess.run(
            [ffmpeg_exe, '-i', video_path],
            capture_output=True, encoding='utf-8', errors='ignore',
            creationflags=CREATE_NO_WINDOW,
        )
        # 从stderr中解析Stream信息
        m = re.search(r'(\d{3,4})x(\d{3,4})', r.stderr)
        if m:
            return int(m.group(1)), int(m.group(2))
        return 1920, 1080

    @staticmethod
    def _get_video_duration(ffmpeg_exe, video_path):
        """获取视频时长（秒）"""
        r = subprocess.run(
            [ffmpeg_exe, '-i', video_path],
            capture_output=True, encoding='utf-8', errors='ignore',
            creationflags=CREATE_NO_WINDOW,
        )
        # 从stderr中解析Duration信息
        for line in r.stderr.split('\n'):
            if 'Duration:' in line:
                time_str = line.split('Duration:')[1].split(',')[0].strip()
                parts = time_str.split(':')
                try:
                    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                except (ValueError, IndexError):
                    return 0.0
        return 0.0

    @staticmethod
    def _generate_srt_file(srt_path: str, narrations: list[str],
                           seg_starts: list[float], seg_durations: list[float]):
        """生成SRT字幕文件

        Args:
            srt_path: SRT文件输出路径
            narrations: 每段旁白文本
            seg_starts: 每段起始时间（秒）
            seg_durations: 每段持续时间（秒）
        """
        def format_time(seconds: float) -> str:
            """将秒数格式化为SRT时间格式 HH:MM:SS,mmm"""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, (narration, start, dur) in enumerate(zip(narrations, seg_starts, seg_durations)):
                end = start + dur
                f.write(f"{i+1}\n")
                f.write(f"{format_time(start)} --> {format_time(end)}\n")
                f.write(f"{narration}\n\n")
                logger.info("SRT段%d: %s --> %s | %s",
                           i+1, format_time(start), format_time(end), narration[:30])

        logger.info("SRT字幕文件已生成: %s (%d段)", srt_path, len(narrations))

        # 同时生成VTT字幕文件（用于HTML5 video软字幕）
        vtt_path = srt_path.replace('.srt', '.vtt')
        VideoService._generate_vtt_file(vtt_path, narrations, seg_starts, seg_durations)

    @staticmethod
    def _generate_vtt_file(vtt_path: str, narrations: list[str], seg_starts: list[float], seg_durations: list[float]):
        """生成VTT字幕文件（HTML5 video软字幕格式）"""
        def format_vtt_time(seconds: float) -> str:
            """将秒数格式化为VTT时间格式 HH:MM:SS.mmm"""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

        with open(vtt_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for i, (narration, start, dur) in enumerate(zip(narrations, seg_starts, seg_durations)):
                end = start + dur
                f.write(f"{format_vtt_time(start)} --> {format_vtt_time(end)}\n")
                f.write(f"{narration}\n\n")

        logger.info("VTT字幕文件已生成: %s (%d段)", vtt_path, len(narrations))

    @staticmethod
    def _burn_subtitles_with_ffmpeg(video_path: str, srt_path: str,
                                     output_path: str, width: int, height: int) -> bool:
        """用ffmpeg的subtitles滤镜烧录字幕到视频

        使用libass渲染字幕，样式对标Remotion的Subtitle组件：
        - 深色不透明背景 + 圆角效果
        - 浅灰白色文字 #E8ECF4
        - 底部居中

        Args:
            video_path: 输入视频路径（无字幕）
            srt_path: SRT字幕文件路径
            output_path: 输出视频路径
            width: 视频宽度
            height: 视频高度

        Returns:
            True成功，False失败
        """
        try:
            # ★ 优先使用系统 ffmpeg（Docker 容器已安装 ffmpeg apt 包）
            ffmpeg_exe = shutil.which("ffmpeg")
            if not ffmpeg_exe:
                try:
                    from imageio_ffmpeg import get_ffmpeg_exe
                    ffmpeg_exe = get_ffmpeg_exe()
                except ImportError:
                    logger.error("[SUBTITLE FAILED] ffmpeg 未安装且 imageio_ffmpeg 不可用")
                    return False
        except Exception:
            logger.error("[SUBTITLE FAILED] 获取 ffmpeg 失败")
            return False

        # 按视频分辨率缩放字幕样式（对标1920x1080的Remotion）
        scale = width / 1920
        font_size = max(int(20 * scale), 12)
        # MarginV: 根据视频分辨率动态计算底部边距（避开进度条）
        # 1080p: 60px, 720p: 40px, 480p: 20px
        margin_v = max(int(60 * scale), 20)

        # ASS颜色格式: &H + AA + BB + GG + RR (A=alpha, 00不透明, FF全透明)
        # 白板视频用黑字+半透明白底条（白字在黑底时适合代码视频，不适合白板教学）
        primary_color = "&H00000000"  # 黑色文字
        back_color = "&H99FFFFFF"     # 半透明白底，alpha=99≈0.6

        # ★ 字体跨平台适配（同 _compose_final_video）
        import platform
        if platform.system() == "Windows":
            subtitle_font = "Microsoft YaHei"
        else:
            subtitle_font = "Noto Sans CJK SC"

        # 构建force_style参数
        # BorderStyle=4: 不透明底框
        # Alignment=2: ffmpeg底部居中（行业标准，不遮挡画面内容）
        force_style = (
            f"FontName={subtitle_font},"
            f"FontSize={font_size},"
            f"PrimaryColour={primary_color},"
            f"BackColour={back_color},"
            f"Outline=0,"
            f"Shadow=0,"
            f"BorderStyle=4,"
            f"Alignment=2,"  # 底部居中
            f"MarginV={margin_v},"  # 动态计算底部边距
            f"MarginL=50,MarginR=50"  # 左右留白确保居中
        )

        # Windows路径需要转义反斜杠和冒号
        srt_path_escaped = srt_path.replace('\\', '/').replace(':', '\\:')

        # 构建ffmpeg命令
        cmd = [
            ffmpeg_exe,
            '-y',
            '-i', video_path,
            '-vf', f"subtitles='{srt_path_escaped}':force_style='{force_style}'",
            '-c:a', 'copy',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            output_path,
        ]

        logger.info("ffmpeg字幕烧录命令: %s", ' '.join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10分钟超时
                creationflags=CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                logger.info("ffmpeg字幕烧录成功: %s", output_path)
                return True
            else:
                logger.error("ffmpeg字幕烧录失败: returncode=%d", result.returncode)
                logger.error("stderr: %s", result.stderr[-500:] if result.stderr else "")
                return False
        except subprocess.TimeoutExpired:
            logger.error("ffmpeg字幕烧录超时")
            return False
        except Exception as e:
            logger.error("ffmpeg字幕烧录异常: %s", e)
            return False

    def _merge_audio_files(self, audio_segments: list[str], output_path: str) -> bool:
        """用ffmpeg合并多个音频文件为一个

        Args:
            audio_segments: 音频文件路径列表
            output_path: 合并后的输出路径

        Returns:
            成功返回True
        """
        if not self._ffmpeg_available or not audio_segments:
            return False

        try:
            # 创建concat列表文件
            concat_list_path = output_path + ".txt"
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for audio_path in audio_segments:
                    if os.path.exists(audio_path):
                        safe_path = audio_path.replace("'", "'\\''").replace("\\", "/")
                        f.write(f"file '{safe_path}'\n")

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c:a", "libmp3lame",
                output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='ignore', timeout=120, creationflags=CREATE_NO_WINDOW)

            # 清理列表文件
            try:
                os.remove(concat_list_path)
            except Exception:
                pass

            if result.returncode == 0 and os.path.exists(output_path):
                logger.info("音频合并成功: %s", output_path)
                return True
            else:
                logger.error("ffmpeg音频合并失败: %s", result.stderr[-300:])
                return False

        except Exception as e:
            logger.error("音频合并异常: %s", e)
            return False

    def _fallback_compose_with_ffmpeg(
        self,
        video_path: str,
        audio_segments: list[str],
        task_id: str,
        knowledge_point: str,
        style: str,
    ) -> Optional[str]:
        """ffmpeg降级：将多段音频拼接后与视频合并"""
        if not self._ffmpeg_available:
            logger.warning("ffmpeg未安装，无法合并视频音频")
            return None

        if not audio_segments:
            return None

        try:
            # 拼接所有音频文件
            concat_list_path = os.path.join(VIDEO_OUTPUT_DIR, f"concat_{task_id}.txt")
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for audio_path in audio_segments:
                    # ffmpeg concat需要转义路径中的特殊字符
                    safe_path = audio_path.replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")

            merged_audio_path = os.path.join(VIDEO_OUTPUT_DIR, f"merged_{task_id}.mp3")
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c:a", "libmp3lame",
                merged_audio_path,
            ]
            result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='ignore', timeout=60, creationflags=CREATE_NO_WINDOW)

            # 清理临时文件
            os.remove(concat_list_path)

            if result.returncode != 0:
                logger.error("ffmpeg音频拼接失败: %s", result.stderr[-200:])
                return None

            # 合并视频+音频
            # Windows文件名净化
            safe_knowledge_point = knowledge_point.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_').replace('（', '_').replace('）', '_')
            final_name = f"{safe_knowledge_point}_{style}_{task_id}.mp4"
            final_path = os.path.join(VIDEO_OUTPUT_DIR, final_name)
            return self.combine_video_audio(video_path, merged_audio_path, final_path)

        except Exception as e:
            logger.error("ffmpeg降级合并失败: %s", e)
            return None

    def get_cached_video(self, knowledge_point: str, style: str) -> Optional[dict]:
        """获取已缓存的视频（避免重复生成）"""
        cache_key = f"{knowledge_point}_{style}"
        cached = self._get_cache(cache_key)
        if cached and cached.get("status") == "completed":
            # 验证文件是否存在
            video_path = cached.get("video_path", "")
            if video_path and os.path.exists(video_path):
                return cached
            else:
                self._delete_cache(cache_key)
        return None

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """获取任务状态"""
        task = self._get_task(task_id)
        return task.to_dict() if task else None

    def start_video_generation(self, knowledge_point: str, style: str = "rigorous", voice: str = "", with_tts: bool = True) -> str:
        """异步启动视频生成，立即返回task_id

        使用threading.Thread在后台执行渲染，不阻塞调用方。
        通过 get_video_task_status() 查询进度。
        """
        task_id = str(uuid.uuid4())[:8]
        task = VideoGenerationTask(task_id, knowledge_point, style)
        task.status = "queued"
        task.progress = 0
        task.message = "排队中..."
        task.created_at = datetime.now().isoformat()
        self._save_task(task)

        thread = threading.Thread(
            target=self._render_in_background,
            args=(task_id, knowledge_point, style, voice, with_tts),
            daemon=True,
        )
        thread.start()

        return task_id

    def get_video_task_status(self, task_id: str) -> Optional[dict]:
        """查询视频生成任务状态（供API轮询使用）"""
        return self.get_task_status(task_id)

    def _render_in_background(self, task_id: str, knowledge_point: str, style: str, voice: str, with_tts: bool):
        """后台渲染线程 — 两步生成管线

        状态流转: queued → rendering → completed / failed
        """
        task = self._get_task(task_id)
        if not task:
            logger.error("[VIDEO FAILED] task_id=%s not found in storage", task_id)
            return

        logger.info("=" * 60)
        logger.info("[VIDEO START] task_id=%s, knowledge_point=%s, style=%s, with_tts=%s",
                    task_id, knowledge_point, style, with_tts)
        logger.info("=" * 60)

        try:
            # Step 1: LLM生成讲解脚本
            task.status = "rendering"
            task.progress = 10
            task.message = "正在生成讲解脚本..."
            self._save_task(task)

            script = self._generate_narration_script(knowledge_point, style)
            if not script or not script.get("segments"):
                logger.error("[VIDEO FAILED] Step 1: LLM脚本生成失败 | Reason: 空脚本或无segments")
                task.status = "failed"
                task.message = "LLM脚本生成失败：返回空内容"
                self._save_task(task)
                return
            task.script_content = json.dumps(script, ensure_ascii=False, indent=2)
            logger.info("[VIDEO SUCCESS] Step 1: LLM脚本生成完成 | segments=%d", len(script.get("segments", [])))

            # Step 2: 先生成TTS音频并测量实际时长
            task.progress = 25
            task.message = "正在生成TTS旁白..."
            self._save_task(task)

            audio_segments = []
            actual_durations = []
            tts_available = edge_tts_service.available or tts_service.available

            # === TTS 可用性诊断日志 ===
            logger.info("-" * 40)
            logger.info("[TTS CHECK] with_tts=%s", with_tts)
            logger.info("[TTS CHECK] edge_tts_service.available=%s", edge_tts_service.available)
            logger.info("[TTS CHECK] tts_service.available=%s", tts_service.available)
            logger.info("[TTS CHECK] tts_available=%s", tts_available)
            logger.info("-" * 40)

            if with_tts and tts_available:
                style_config = STYLE_CONFIG.get(style, STYLE_CONFIG["rigorous"])
                use_voice = voice if voice else style_config["voice"]
                segments = script.get("segments", [])
                logger.info("[TTS START] 开始生成 %d 段音频, voice=%s", len(segments), use_voice)

                for i, segment in enumerate(segments):
                    audio_path = self._generate_tts_audio(
                        text=segment["narration"],
                        voice=use_voice,
                        speed=style_config["speed"],
                    )
                    if audio_path and os.path.exists(audio_path):
                        audio_segments.append(audio_path)
                        try:
                            from moviepy import AudioFileClip
                            clip = AudioFileClip(audio_path)
                            real_dur = clip.duration
                            clip.close()
                        except Exception as e:
                            logger.warning("[TTS] 段%d无法读取时长: %s, 使用预估时长", i+1, e)
                            real_dur = segment.get("duration", 5)
                        actual_durations.append(real_dur)
                        logger.info("[TTS SUCCESS] 段%d: %s -> %.1fs, path=%s", i+1, segment["narration"][:20], real_dur, audio_path)
                    else:
                        actual_durations.append(segment.get("duration", 5))
                        logger.warning("[TTS FAILED] 段%d: 音频生成失败, text=%s", i+1, segment["narration"][:30])
                    task.progress = 25 + int(15 * (i + 1) / max(len(segments), 1))
                    self._save_task(task)

                if audio_segments:
                    logger.info("[TTS SUCCESS] 音频生成完成 | 共%d段, 总时长%.1fs", len(audio_segments), sum(actual_durations))
                else:
                    logger.warning("[TTS FAILED] 所有音频生成失败 | 将生成无声音频")
            elif not with_tts:
                logger.info("[TTS SKIP] with_tts=False, 跳过音频生成")
            else:
                logger.error("[TTS FAILED] TTS服务不可用 | edge_tts=%s, xunfei=%s",
                            edge_tts_service.available, tts_service.available)

            # Step 3: 用实际时长生成Manim代码
            task.progress = 45
            task.message = "正在生成Manim动画代码..."
            self._save_task(task)

            manim_code = self._generate_manim_from_script_with_durations(
                knowledge_point, script, style, actual_durations
            )
            logger.info("[MANIM] Step 3: Manim代码生成完成 | length=%d chars", len(manim_code) if manim_code else 0)

            # 确定Scene类名 - 优先使用模板注册的类名，避免大小写不匹配
            template = get_manim_template(knowledge_point)
            if template:
                scene_class = template["scene_class"]
            else:
                # ★ 生成合法的Scene类名（只包含ASCII字符）
                import re
                safe_class_name = re.sub(r'[^\w]', '', knowledge_point.replace(' ', '_'))
                if not safe_class_name or not re.match(r'^[a-zA-Z_]', safe_class_name):
                    safe_class_name = 'KnowledgePoint'
                scene_class = safe_class_name + "Scene"
            logger.info("[MANIM] Scene类名: %s", scene_class)

            # Step 4: 渲染Manim视频（动画时长已匹配音频，音画同步）
            task.progress = 55
            task.message = "正在渲染Manim视频..."
            self._save_task(task)
            logger.info("-" * 40)
            logger.info("[MANIM START] 开始渲染 | scene_class=%s", scene_class)

            render_result = self.render_video(manim_code, scene_class)

            if render_result.get("status") != "completed":
                error_msg = render_result.get("message", "视频渲染失败")
                logger.error("[MANIM FAILED] Step 4: 渲染失败 | Reason: %s", error_msg)
                task.status = render_result.get("status", "failed")
                task.message = error_msg
                task.script_content = render_result.get("script_content", "")
                task.progress = 55
                self._save_task(task)
                return

            video_path = render_result.get("video_path", "")
            logger.info("[MANIM SUCCESS] Step 4: 渲染完成 | video_path=%s", video_path)
            task.video_path = video_path

            # Step 5: 拼接视频+音频+SRT字幕（音字同步）
            task.progress = 80
            task.message = "正在拼接视频和音频..."
            self._save_task(task)

            final_path = None
            if audio_segments:
                logger.info("[COMPOSE] Step 5: 开始拼接 | video=%s, audio_segments=%d", video_path, len(audio_segments))
                narrations_for_video = [s["narration"] for s in script.get("segments", [])][:len(audio_segments)]
                final_path = self._compose_final_video(
                    video_path=video_path,
                    audio_segments=audio_segments,
                    narrations=narrations_for_video,
                    durations=actual_durations,
                    task_id=task_id,
                    knowledge_point=knowledge_point,
                    style=style,
                )
                if final_path:
                    logger.info("[COMPOSE SUCCESS] Step 5: 拼接完成 | final_path=%s", final_path)
                    task.video_path = final_path
                else:
                    logger.warning("[COMPOSE FAILED] Step 5: 拼接失败，使用原始Manim视频 | video_path=%s", video_path)
            else:
                logger.info("[COMPOSE SKIP] Step 5: 无音频，跳过拼接 | video_path=%s", video_path)

            # 检查视频文件完整性：文件必须存在且大小合理(>10KB)
            final_video_path = task.video_path if audio_segments and final_path else video_path
            if os.path.exists(final_video_path):
                file_size = os.path.getsize(final_video_path)
                if file_size < 10 * 1024:  # 小于 10KB 视为损坏
                    logger.error("[VIDEO FAILED] Step 6: 视频文件损坏 | path=%s, size=%d bytes (< 10KB)", final_video_path, file_size)
                    task.status = "failed"
                    task.message = f"视频文件损坏(大小: {file_size} bytes),请重新生成"
                    task.progress = 95
                    self._save_task(task)
                    return
                logger.info("[VIDEO SUCCESS] Step 6: 视频文件检查通过 | path=%s, size=%d bytes", final_video_path, file_size)
                task.video_url = f"/static/videos/{os.path.basename(final_video_path)}"
                task.subtitle_url = f"/static/videos/subs_{task_id}.vtt"
            else:
                logger.error("[VIDEO FAILED] Step 6: 视频文件不存在 | path=%s", final_video_path)
                task.status = "failed"
                task.message = "视频文件生成失败,文件不存在"
                task.progress = 95
                self._save_task(task)
                return

            task.status = "completed"
            task.progress = 100
            task.message = "视频生成完成"

            # === 最终成功日志 ===
            logger.info("=" * 60)
            logger.info("[VIDEO SUCCESS] 全流程完成!")
            logger.info("  - task_id: %s", task_id)
            logger.info("  - knowledge_point: %s", knowledge_point)
            logger.info("  - style: %s", style)
            logger.info("  - video_url: %s", task.video_url)
            logger.info("  - audio_segments: %d", len(audio_segments))
            logger.info("  - file_size: %s", os.path.getsize(final_video_path) if os.path.exists(final_video_path) else "N/A")
            logger.info("=" * 60)

            # 缓存
            cache_key = f"{knowledge_point}_{style}"
            self._save_cache(cache_key, task.to_dict())
            self._save_task(task)

        except Exception as e:
            import traceback
            logger.error("=" * 60)
            logger.error("[VIDEO FAILED] 未捕获异常 | task_id=%s", task_id)
            logger.error("  - Exception: %s", str(e))
            logger.error("  - Traceback:\n%s", traceback.format_exc())
            logger.error("=" * 60)
            task.status = "failed"
            task.message = f"视频生成失败: {str(e)}"
            self._save_task(task)

    def list_available_videos(self) -> list[dict]:
        """列出所有可用视频（缓存的+预制的）"""
        videos = []

        # 缓存的已生成视频（从Redis扫描）
        try:
            r = self._get_redis()
            for key in r.scan_iter("video:cache:*"):
                data = r.get(key)
                if data:
                    info = json.loads(data)
                    if info.get("status") == "completed":
                        videos.append({
                            "type": "generated",
                            "knowledge_point": info["knowledge_point"],
                            "style": info["style"],
                            "video_url": info["video_url"],
                            "task_id": info["task_id"],
                        })
        except Exception as e:
            logger.warning("Redis扫描缓存失败: %s", e)

        # 预制模板（可生成但尚未生成）
        for template_info in list_available_templates():
            kp = template_info["knowledge_point"]
            # 检查是否已有缓存
            has_cache = any(
                v["knowledge_point"] == kp and v.get("type") == "generated"
                for v in videos
            )
            if not has_cache:
                videos.append({
                    "type": "template",
                    "knowledge_point": kp,
                    "scene_class": template_info["scene_class"],
                    "narration_count": template_info["narration_count"],
                })

        return videos


# 全局单例
video_service = VideoService()
