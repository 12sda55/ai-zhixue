"""视频生成 Prompt 模板系统

借鉴 OpenMAIC 的 prompt 模板设计：
- 模板文件系统：每个场景类型一个目录，包含 system.md + user.md
- Snippet 复用：通用片段可被多个模板引用
- 条件块：{{#if condition}}...{{/if}} 根据条件裁剪内容
- 变量插值：{{variableName}} 替换为实际值

处理顺序：Snippet 拼接 → 条件块裁剪 → 变量插值
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "prompt_templates"
SNIPPETS_DIR = TEMPLATES_DIR / "_snippets"


def _load_file(path: Path) -> str:
    """加载模板文件内容"""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _process_snippets(text: str) -> str:
    """处理 {{snippet:name}} 引用，替换为对应文件内容"""
    def replace_snippet(match: re.Match) -> str:
        snippet_name = match.group(1)
        snippet_path = SNIPPETS_DIR / f"{snippet_name}.md"
        content = _load_file(snippet_path)
        if not content:
            logger.warning("Snippet not found: %s", snippet_name)
            return match.group(0)
        return content

    return re.sub(r"\{\{snippet:([\w-]+)\}\}", replace_snippet, text)


def _process_conditional_blocks(text: str, variables: dict) -> str:
    """处理 {{#if condition}}...{{/if}} 条件块

    condition 为 truthy 时保留内容，否则移除
    """

    def replace_block(match: re.Match) -> str:
        condition_name = match.group(1)
        content = match.group(2)
        if variables.get(condition_name):
            return content
        return ""

    # 支持多行条件块
    return re.sub(
        r"\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}",
        replace_block,
        text,
        flags=re.DOTALL,
    )


def _interpolate_variables(text: str, variables: dict) -> str:
    """处理 {{variableName}} 变量插值"""
    def replace_var(match: re.Match) -> str:
        var_name = match.group(1)
        if var_name in variables:
            return str(variables[var_name])
        return match.group(0)  # 未找到变量，原样保留

    return re.sub(r"\{\{(\w+)\}\}", replace_var, text)


def build_prompt(template_id: str, variables: Optional[dict] = None) -> str:
    """构建完整的 prompt

    Args:
        template_id: 模板ID，对应 prompt_templates/ 下的目录名
        variables: 模板变量

    Returns:
        处理后的完整 prompt 文本
    """
    variables = variables or {}
    template_dir = TEMPLATES_DIR / template_id

    # 优先使用 user.md，不存在则使用 system.md
    user_path = template_dir / "user.md"
    system_path = template_dir / "system.md"

    text = _load_file(user_path) or _load_file(system_path)
    if not text:
        logger.warning("Template not found: %s", template_id)
        return ""

    # 按顺序处理：Snippet → 条件块 → 变量插值
    text = _process_snippets(text)
    text = _process_conditional_blocks(text, variables)
    text = _interpolate_variables(text, variables)

    return text.strip()


def list_templates() -> list[str]:
    """列出所有可用的模板ID"""
    if not TEMPLATES_DIR.exists():
        return []
    return [
        d.name
        for d in TEMPLATES_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_")
    ]
