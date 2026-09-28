"""冷启动画像构建服务 - 对照 ai_architecture_plan.md Phase 1.3

冷启动流程：
1. 结构化4问题（专业、阶段、目标、认知风格）→ 直接填充
2. 自由对话 → LLM抽取画像特征（学习节奏、偏好、薄弱自述等）
3. 根据专业背景设置初始mastery
"""

from __future__ import annotations
import json
import logging
from typing import Optional

from app.core.llm import llm_client
from app.schemas.profile import (
    StudentProfile, Major, Stage, CognitiveStyle,
    LearningPace, LearningPreference, DifficultyLevel,
)

logger = logging.getLogger(__name__)

# ===== 冷启动Prompt =====

COLD_START_EXTRACTION_PROMPT = """你是一个教育画像分析专家。根据学生与AI老师的对话，提取以下画像特征。

请严格按照以下JSON格式输出，不要输出其他内容：
{
    "major": "computer_science|related_major|non_cs|cross_exam",
    "stage": "preview|synchronous|review|exam_prep",
    "cognitive_style": "visual|verbal|practical",
    "learning_goals": ["目标1", "目标2"],
    "learning_pace": "trial_error|deep_think|steady",
    "learning_preference": "independent|social|mixed",
    "self_reported_weak": ["薄弱知识点1", "薄弱知识点2"],
    "self_reported_strong": ["已掌握知识点1", "已掌握知识点2"],
    "difficulty_level": "basic|intermediate|advanced"
}

专业背景判断规则：
- computer_science: 明确提到是计算机专业/软件工程等
- related_major: 数学、信息管理、电子等理工科
- non_cs: 文科、商科等非理工科
- cross_exam: 提到跨考、转专业考研

学习节奏判断规则：
- trial_error: 喜欢直接动手试，快速迭代
- deep_think: 喜欢先理解原理再动手
- steady: 按部就班，循序渐进

如果对话中无法判断某个字段，使用默认值：
- major: non_cs
- stage: synchronous
- cognitive_style: visual
- learning_pace: steady
- learning_preference: mixed
- difficulty_level: basic

对话内容：
{conversation}"""


class ColdStartService:
    """冷启动画像构建服务"""

    def build_from_structured(
        self,
        user_id: str,
        major: Major,
        stage: Stage,
        learning_goals: list[str],
        cognitive_style: CognitiveStyle,
    ) -> StudentProfile:
        """从结构化4问题构建画像（不调用LLM）

        Args:
            user_id: 用户ID
            major: 专业背景
            stage: 当前阶段
            learning_goals: 学习目标列表
            cognitive_style: 认知风格

        Returns:
            初始画像
        """
        profile = StudentProfile(
            user_id=user_id,
            major=major,
            stage=stage,
            cognitive_style=cognitive_style,
            learning_goals=learning_goals,
        )

        # 根据专业背景设置初始mastery
        self._set_initial_mastery(profile, major)

        return profile

    def build_from_conversation(
        self,
        user_id: str,
        conversation: str,
    ) -> StudentProfile:
        """从自由对话中用LLM抽取画像特征

        Args:
            user_id: 用户ID
            conversation: 对话文本

        Returns:
            初始画像
        """
        prompt = COLD_START_EXTRACTION_PROMPT.format(conversation=conversation)

        try:
            response = llm_client.chat(
                messages=[
                    {"role": "system", "content": "你是教育画像分析专家，只输出JSON格式。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            features = json.loads(response)
            profile = self._build_profile_from_features(user_id, features)
            logger.info(f"LLM冷启动画像构建成功: user_id={user_id}")
            return profile

        except json.JSONDecodeError as e:
            logger.error(f"LLM返回JSON解析失败: {e}, response={response}")
            # 降级：返回默认画像
            return StudentProfile(user_id=user_id)
        except Exception as e:
            logger.error(f"LLM冷启动画像构建失败: {e}")
            return StudentProfile(user_id=user_id)

    def _build_profile_from_features(self, user_id: str, features: dict) -> StudentProfile:
        """从LLM提取的特征构建画像"""
        # 安全地解析枚举值
        major = self._safe_enum(features.get("major", "non_cs"), Major, Major.NON_CS)
        stage = self._safe_enum(features.get("stage", "synchronous"), Stage, Stage.SYNCHRONOUS)
        cognitive_style = self._safe_enum(features.get("cognitive_style", "visual"), CognitiveStyle, CognitiveStyle.VISUAL)
        learning_pace = self._safe_enum(features.get("learning_pace", "steady"), LearningPace, LearningPace.STEADY)
        learning_preference = self._safe_enum(features.get("learning_preference", "mixed"), LearningPreference, LearningPreference.MIXED)
        difficulty_level = self._safe_enum(features.get("difficulty_level", "basic"), DifficultyLevel, DifficultyLevel.BASIC)

        profile = StudentProfile(
            user_id=user_id,
            major=major,
            stage=stage,
            cognitive_style=cognitive_style,
            learning_goals=features.get("learning_goals", []),
            learning_pace=learning_pace,
            learning_preference=learning_preference,
            difficulty_level=difficulty_level,
        )

        # 根据专业背景设置初始mastery
        self._set_initial_mastery(profile, major)

        # 处理自述薄弱
        for kp in features.get("self_reported_weak", []):
            profile.add_weak_point(kp, "冷启动自述薄弱")

        # 处理自述已掌握
        for kp in features.get("self_reported_strong", []):
            profile.set_knowledge_mastery(kp, 0.5)  # 自述掌握但需验证，给0.5

        return profile

    def _set_initial_mastery(self, profile: StudentProfile, major: Major) -> None:
        """根据专业背景设置初始mastery"""
        if major == Major.CS:
            # 计算机专业：基础知识点已有一定掌握
            for kp in ["array", "linked_list", "stack", "queue", "recursion", "complexity"]:
                profile.set_knowledge_mastery(kp, 0.4)
        elif major == Major.RELATED:
            # 相关专业：基础略懂
            for kp in ["array", "recursion", "complexity"]:
                profile.set_knowledge_mastery(kp, 0.2)
        # NON_CS和CROSS：默认0.0，从零开始

    @staticmethod
    def _safe_enum(value: str, enum_class, default):
        """安全地解析枚举值，无效值返回默认"""
        try:
            return enum_class(value)
        except (ValueError, KeyError):
            return default


# 全局单例
cold_start_service = ColdStartService()
