"""上下文管理 - 摘要压缩 + 对话历史管理

对照 ai_architecture_plan.md：
- 渐进型记忆管理：早期对话生成摘要，保留摘要 + 近期对话
- 触发时机：对话token超4000时对前半部分生成摘要
- 重点保留画像相关信息（薄弱点、偏好、目标）
"""

from __future__ import annotations
import json
import logging
from typing import Optional

from app.core.llm import llm_client

logger = logging.getLogger(__name__)

# ===== 摘要压缩Prompt =====

SUMMARY_PROMPT = """请将以下对话历史压缩为简洁的摘要，重点保留：
1. 学生提到的薄弱知识点
2. 学生的学习目标和偏好
3. 关键的学习行为（答题正确/错误、代码实操结果等）
4. 画像变更信息

忽略寒暄和重复内容，保留关键信息。

对话历史：
{conversation}

请输出JSON格式：
{{
    "summary": "压缩后的摘要文本",
    "weak_points_mentioned": ["提到的薄弱知识点"],
    "goals_mentioned": ["提到的学习目标"],
    "key_behaviors": ["关键学习行为"]
}}"""


# 估算token数（中文约1.5字/token）
def estimate_tokens(text: str) -> int:
    """估算文本的token数"""
    return int(len(text) * 1.5)


class ContextManager:
    """上下文管理器 - 摘要压缩"""

    MAX_TOKENS = 4000  # 对话历史最大token数
    RECENT_TURNS = 6   # 保留最近6轮对话

    def compress_conversation(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """压缩对话历史

        Args:
            messages: 对话消息列表 [{"role": str, "content": str}]

        Returns:
            (summary, recent_messages) 摘要 + 最近的对话
        """
        if not messages:
            return "", []

        # 估算总token数
        total_text = " ".join(m.get("content", "") for m in messages)
        total_tokens = estimate_tokens(total_text)

        if total_tokens <= self.MAX_TOKENS:
            # 不需要压缩
            return "", messages

        # 分割：前半部分压缩，后半部分保留
        split_idx = len(messages) // 2
        old_messages = messages[:split_idx]
        recent_messages = messages[split_idx:]

        # 确保至少保留最近6轮
        if len(recent_messages) < self.RECENT_TURNS * 2:
            remaining = self.RECENT_TURNS * 2 - len(recent_messages)
            old_messages = messages[:split_idx + remaining]
            recent_messages = messages[split_idx + remaining:]

        # 压缩前半部分
        summary = self._generate_summary(old_messages)

        return summary, recent_messages

    def _generate_summary(self, messages: list[dict]) -> str:
        """用LLM生成对话摘要"""
        conversation_text = ""
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            conversation_text += f"{role}: {content}\n"

        try:
            response = llm_client.chat(
                messages=[
                    {"role": "system", "content": "你是对话摘要专家，只输出JSON格式。"},
                    {"role": "user", "content": SUMMARY_PROMPT.format(conversation=conversation_text)},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            result = json.loads(response)
            summary = result.get("summary", "")

            # 附加关键信息
            extras = []
            if result.get("weak_points_mentioned"):
                extras.append(f"薄弱知识点: {', '.join(result['weak_points_mentioned'])}")
            if result.get("goals_mentioned"):
                extras.append(f"学习目标: {', '.join(result['goals_mentioned'])}")
            if result.get("key_behaviors"):
                extras.append(f"关键行为: {', '.join(result['key_behaviors'])}")

            if extras:
                summary += "\n\n" + "\n".join(extras)

            return summary

        except Exception as e:
            logger.error(f"对话摘要生成失败: {e}")
            # 降级：简单截取
            return "早期对话摘要（自动生成失败）：" + conversation_text[:500]

    def build_context_messages(
        self,
        summary: str,
        recent_messages: list[dict],
        profile_summary: str = "",
    ) -> list[dict]:
        """构建LLM上下文消息列表

        Args:
            summary: 早期对话摘要
            recent_messages: 最近的对话消息
            profile_summary: 画像摘要

        Returns:
            完整的上下文消息列表
        """
        context = []

        # 系统消息中包含画像和摘要
        system_parts = []
        if profile_summary:
            system_parts.append(f"当前学生画像：\n{profile_summary}")
        if summary:
            system_parts.append(f"早期对话摘要：\n{summary}")

        if system_parts:
            context.append({
                "role": "system",
                "content": "\n\n".join(system_parts),
            })

        # 添加最近对话
        for msg in recent_messages:
            context.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        return context


# 全局单例
context_manager = ContextManager()
