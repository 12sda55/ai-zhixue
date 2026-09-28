"""智能辅导Agent服务 - 对照 ai_architecture_plan.md Agent 8

核心功能：
1. 问题类型分类（概念性/理解性/调试性/应用性）
2. 自适应Socratic引导策略
3. 渐进式提示（5级从模糊到具体）
4. 安全阀（引导>5轮→直接给答案）
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.profile import (
    StudentProfile, CognitiveStyle, DifficultyLevel, LearningPace, Stage,
)
from app.schemas.knowledge_graph import get_knowledge_node

logger = logging.getLogger(__name__)


# ===== 数据模型 =====

class QuestionType(str, Enum):
    """问题类型"""
    CONCEPTUAL = "conceptual"     # 概念性：什么是XX？
    UNDERSTANDING = "understanding"  # 理解性：为什么XX？
    DEBUGGING = "debugging"       # 调试性：代码为什么报错？
    APPLICATION = "application"   # 应用性：怎么用XX实现YY？


class TutorResponse(BaseModel):
    """辅导响应"""
    response: str = ""
    question_type: str = ""
    guidance_round: int = 0
    hints: list[str] = Field(default_factory=list)
    should_continue: bool = True
    mode: str = "socratic"  # socratic / hint / explain


# ===== 问题分类关键词 =====

CLASSIFICATION_KEYWORDS = {
    QuestionType.CONCEPTUAL: [
        "什么是", "是什么", "介绍一下", "讲一下", "解释一下",
        "概念", "定义", "含义", "意思", "区别",
        "what is", "define", "concept",
    ],
    QuestionType.UNDERSTANDING: [
        "为什么", "怎么会", "怎么理解", "原理是什么", "为什么是",
        "为什么能", "凭什么", "如何证明", "怎么推导",
        "why", "how come", "reason", "principle",
    ],
    QuestionType.DEBUGGING: [
        "报错", "错误", "bug", "运行不了", "不对", "结果不对",
        "为什么报", "哪里错了", "出错了", "失败",
        "error", "bug", "wrong", "fail", "crash",
    ],
    QuestionType.APPLICATION: [
        "怎么实现", "如何实现", "怎么用", "怎么写", "如何写",
        "实现一个", "设计一个", "编写", "编码",
        "how to", "implement", "write code", "design",
    ],
}

# 直接告诉我的关键词
DIRECT_ANSWER_KEYWORDS = [
    "直接告诉我", "直接说答案", "别绕了", "直接给答案",
    "just tell me", "give me the answer", "直接说",
]


# ===== 辅导服务 =====

class TutorService:
    """智能辅导Agent服务"""

    def __init__(self):
        # 跟踪每个用户的引导轮次 {user_id+kp: round}
        self._guidance_rounds: dict[str, int] = {}

    def tutor(
        self,
        knowledge_point: str,
        question: str,
        mode: str = "socratic",
        profile: Optional[StudentProfile] = None,
    ) -> dict:
        """主辅导入口

        Args:
            knowledge_point: 知识点ID
            question: 学生问题
            mode: 辅导模式 socratic/hint/explain
            profile: 学生画像

        Returns:
            TutorResponse dict
        """
        # 1. 检查安全阀：学生是否要求直接给答案
        if self._wants_direct_answer(question):
            return self._direct_answer(knowledge_point, question, profile)

        # 2. 分类问题
        q_type = self.classify_question(question, knowledge_point)

        # 3. 获取/更新引导轮次
        round_key = f"{(profile.user_id if profile else 'anon')}_{knowledge_point}"
        current_round = self._guidance_rounds.get(round_key, 0) + 1
        self._guidance_rounds[round_key] = current_round

        # 4. 安全阀：超过5轮直接给答案
        if current_round > 5:
            response = self._direct_answer(knowledge_point, question, profile)
            self._guidance_rounds[round_key] = 0  # 重置
            return {
                "response": response["response"],
                "question_type": q_type.value,
                "guidance_round": current_round,
                "hints": [],
                "should_continue": False,
                "mode": "explain",
            }

        # 5. 根据模式和问题类型生成响应
        if mode == "explain":
            result = self._explain_mode(knowledge_point, question, q_type, profile)
        elif mode == "hint":
            hints = self.generate_progressive_hints(knowledge_point, question, q_type, profile)
            result = {
                "response": hints[0] if hints else "请再具体描述一下你的问题",
                "hints": hints,
            }
        else:
            # socratic模式
            result = self._socratic_mode(knowledge_point, question, q_type, profile, current_round)

        return {
            "response": result.get("response", ""),
            "question_type": q_type.value,
            "guidance_round": current_round,
            "hints": result.get("hints", []),
            "should_continue": current_round < 5,
            "mode": mode,
        }

    def classify_question(self, question: str, knowledge_point: str = "") -> QuestionType:
        """分类问题类型

        优先使用关键词匹配（快速可靠），LLM作为可选增强。
        """
        q_lower = question.lower()

        # 按优先级匹配关键词
        # 调试性优先（因为"为什么报错"同时匹配理解和调试）
        for q_type in [QuestionType.DEBUGGING, QuestionType.APPLICATION,
                       QuestionType.UNDERSTANDING, QuestionType.CONCEPTUAL]:
            keywords = CLASSIFICATION_KEYWORDS[q_type]
            for kw in keywords:
                if kw in q_lower:
                    return q_type

        # 默认概念性
        return QuestionType.CONCEPTUAL

    def generate_progressive_hints(
        self,
        knowledge_point: str,
        question: str,
        question_type: Optional[QuestionType] = None,
        profile: Optional[StudentProfile] = None,
    ) -> list[str]:
        """生成渐进式提示（5级：从模糊到具体）

        Level 1: 非常模糊的方向
        Level 2: 更具体的方向
        Level 3: 关键洞察
        Level 4: 接近答案
        Level 5: 直接答案
        """
        if question_type is None:
            question_type = self.classify_question(question, knowledge_point)

        node_def = get_knowledge_node(knowledge_point)
        kp_name = node_def.name if node_def else knowledge_point

        hints = self._build_hints(knowledge_point, kp_name, question_type, question)

        # 根据画像调整提示详细程度
        if profile:
            if profile.difficulty_level == DifficultyLevel.ADVANCED:
                # 进阶者：跳过前2个模糊提示
                hints = hints[2:]
            elif profile.difficulty_level == DifficultyLevel.BASIC:
                # 基础者：保留全部提示
                pass

        return hints

    def check_safety_valve(self, user_id: str, knowledge_point: str, question: str = "") -> dict:
        """检查安全阀

        Returns:
            {"should_switch": bool, "reason": str}
        """
        # 学生要求直接给答案
        if question and self._wants_direct_answer(question):
            return {"should_switch": True, "reason": "学生要求直接给答案"}

        # 引导轮次超过5
        round_key = f"{user_id}_{knowledge_point}"
        rounds = self._guidance_rounds.get(round_key, 0)
        if rounds >= 5:
            return {"should_switch": True, "reason": f"已引导{rounds}轮，超过安全阈值"}

        return {"should_switch": False, "reason": ""}

    def reset_guidance(self, user_id: str, knowledge_point: str) -> None:
        """重置引导轮次（切换知识点或新对话时）"""
        round_key = f"{user_id}_{knowledge_point}"
        self._guidance_rounds.pop(round_key, None)

    # ===== 内部方法 =====

    def _wants_direct_answer(self, question: str) -> bool:
        """检查学生是否要求直接给答案"""
        q_lower = question.lower()
        return any(kw in q_lower for kw in DIRECT_ANSWER_KEYWORDS)

    def _direct_answer(self, kp: str, question: str, profile: Optional[StudentProfile]) -> dict:
        """直接给出答案"""
        node_def = get_knowledge_node(kp)
        kp_name = node_def.name if node_def else kp

        # 尝试用LLM生成直接答案
        try:
            from app.core.llm import llm_client
            prompt = f"""请直接回答关于「{kp_name}」的问题：{question}

要求：
1. 直接给出答案，不要反问
2. 用中文回答
3. 如果涉及代码，给出完整示例
4. 控制在300字以内
"""
            answer = llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return {"response": answer, "mode": "explain"}
        except Exception as e:
            logger.warning(f"LLM直接回答失败: {e}")
            return {"response": f"关于{kp_name}，建议你查看相关文档或教材获取详细解答。", "mode": "explain"}

    def _socratic_mode(
        self,
        kp: str,
        question: str,
        q_type: QuestionType,
        profile: Optional[StudentProfile],
        round_num: int,
    ) -> dict:
        """Socratic引导模式"""
        node_def = get_knowledge_node(kp)
        kp_name = node_def.name if node_def else kp

        # 根据问题类型选择引导策略
        if q_type == QuestionType.CONCEPTUAL:
            response = self._guide_conceptual(kp_name, question, profile, round_num)
        elif q_type == QuestionType.UNDERSTANDING:
            response = self._guide_understanding(kp_name, question, profile, round_num)
        elif q_type == QuestionType.DEBUGGING:
            response = self._guide_debugging(kp_name, question, profile, round_num)
        else:  # APPLICATION
            response = self._guide_application(kp_name, question, profile, round_num)

        # 生成渐进提示
        hints = self.generate_progressive_hints(kp, question, q_type, profile)

        return {"response": response, "hints": hints[:3]}  # 只给前3个提示，保留后2个

    def _explain_mode(self, kp: str, question: str, q_type: QuestionType,
                      profile: Optional[StudentProfile]) -> dict:
        """直接讲解模式"""
        return self._direct_answer(kp, question, profile)

    def _guide_conceptual(self, kp_name: str, question: str,
                          profile: Optional[StudentProfile], round_num: int) -> str:
        """概念性问题引导：直接回答+类比"""
        # 概念性问题不需要太多引导，直接给出清晰解释
        try:
            from app.core.llm import llm_client
            style_hint = ""
            if profile:
                if profile.cognitive_style == CognitiveStyle.VISUAL:
                    style_hint = "请用图示或比喻来解释，帮助学生直观理解。"
                elif profile.cognitive_style == CognitiveStyle.PRACTICAL:
                    style_hint = "请结合实际代码示例来解释。"
                elif profile.major.value in ("non_cs", "cross_exam"):
                    style_hint = "请用生活中的类比来解释，避免过多专业术语。"

            prompt = f"""请清晰解释关于「{kp_name}」的概念问题：{question}

要求：
1. 直接给出清晰的概念解释
2. 用一个生活中的类比帮助理解
3. {style_hint}
4. 用中文，200字以内
"""
            return llm_client.chat(messages=[{"role": "user", "content": prompt}], temperature=0.3)
        except Exception:
            return f"关于{kp_name}，这是一个重要的基础概念。你可以先查看文档中的详细讲解，然后尝试做几道概念题来巩固理解。"

    def _guide_understanding(self, kp_name: str, question: str,
                             profile: Optional[StudentProfile], round_num: int) -> str:
        """理解性问题引导：Socratic多步引导"""
        # 根据画像调整引导深度
        step_count = 3  # 默认3步引导
        if profile:
            if profile.difficulty_level == DifficultyLevel.BASIC:
                step_count = 5
            elif profile.difficulty_level == DifficultyLevel.ADVANCED:
                step_count = 2
            if any(wp.knowledge_point in question.lower() for wp in (profile.weak_points or [])):
                step_count += 1  # 薄弱点更耐心

        try:
            from app.core.llm import llm_client
            prompt = f"""学生问了一个关于「{kp_name}」的理解性问题：{question}

请用Socratic引导法回答，不要直接给答案，而是通过提问引导学生自己思考。
要求：
1. 提出{step_count}个循序渐进的引导问题
2. 每个问题指向理解的关键步骤
3. 不要直接给出结论
4. 用中文，150字以内
"""
            return llm_client.chat(messages=[{"role": "user", "content": prompt}], temperature=0.4)
        except Exception:
            return f"让我们一步步来理解这个问题。关于{kp_name}，你能先回忆一下它的基本定义吗？然后我们再深入分析。"

    def _guide_debugging(self, kp_name: str, question: str,
                         profile: Optional[StudentProfile], round_num: int) -> str:
        """调试性问题引导：提示方向不直接改代码"""
        try:
            from app.core.llm import llm_client
            prompt = f"""学生在{kp_name}相关代码中遇到了问题：{question}

请给出调试方向提示，不要直接修改代码。
要求：
1. 指出可能出错的方向（如"检查边界条件"、"看看循环终止条件"）
2. 提供一个检查思路，不是修复代码
3. 用中文，100字以内
"""
            return llm_client.chat(messages=[{"role": "user", "content": prompt}], temperature=0.3)
        except Exception:
            return f"遇到代码问题时，建议你：1)检查边界条件 2)确认循环终止条件 3)打印中间变量查看状态。先试试看？"

    def _guide_application(self, kp_name: str, question: str,
                           profile: Optional[StudentProfile], round_num: int) -> str:
        """应用性问题引导：提示方向让学生自己想"""
        try:
            from app.core.llm import llm_client
            pace_hint = ""
            if profile and profile.learning_pace == LearningPace.TRIAL_ERROR:
                pace_hint = "先让学生自己尝试，给出大方向即可。"
            else:
                pace_hint = "给出实现思路的关键步骤提示。"

            prompt = f"""学生问了一个关于「{kp_name}」的应用问题：{question}

请给出实现方向提示，不要直接写代码。
要求：
1. 提示关键的实现思路或算法选择
2. {pace_hint}
3. 用中文，100字以内
"""
            return llm_client.chat(messages=[{"role": "user", "content": prompt}], temperature=0.3)
        except Exception:
            return f"关于{kp_name}的应用，你可以先想想需要哪些数据结构，然后考虑核心操作的时间复杂度要求。"

    def _build_hints(self, kp: str, kp_name: str, q_type: QuestionType, question: str) -> list[str]:
        """构建5级渐进提示"""
        if q_type == QuestionType.CONCEPTUAL:
            return [
                f"想想{kp_name}在日常生活中有什么类似的例子？",
                f"{kp_name}的核心特征是什么？和相似概念有什么区别？",
                f"关键点：{kp_name}的本质是数据的组织方式，关注它的操作和性质",
                f"具体来说，{kp_name}允许的主要操作决定了它的应用场景",
                self._hint_answer_conceptual(kp_name),
            ]
        elif q_type == QuestionType.UNDERSTANDING:
            return [
                "先回顾一下基本定义，你已知什么？",
                f"想想{kp_name}的每个操作步骤，为什么需要这一步？",
                f"关键洞察：关注最坏情况和平均情况的区别",
                f"试着用一个小例子手动模拟一遍过程",
                self._hint_answer_understanding(kp_name),
            ]
        elif q_type == QuestionType.DEBUGGING:
            return [
                "检查一下边界条件：空输入、单元素、极端值",
                "看看循环/递归的终止条件是否正确",
                "打印中间变量，对比你期望的值和实际值",
                "常见错误：off-by-one、空指针、类型不匹配",
                self._hint_answer_debugging(kp_name),
            ]
        else:  # APPLICATION
            return [
                f"先确定需要什么数据结构来存储{kp_name}的数据",
                f"想想核心操作的时间复杂度要求，选择合适的实现方式",
                f"从最简单的实现开始，先保证正确性再优化",
                f"参考已有的代码模板，理解框架后填入你的逻辑",
                self._hint_answer_application(kp_name),
            ]

    def _hint_answer_conceptual(self, kp_name: str) -> str:
        """概念性问题的最终答案提示"""
        return f"答案：{kp_name}的定义和核心性质请查看文档中的详细讲解。"

    def _hint_answer_understanding(self, kp_name: str) -> str:
        """理解性问题的最终答案提示"""
        return f"答案：{kp_name}的原理分析请查看文档中的深度讲解部分。"

    def _hint_answer_debugging(self, kp_name: str) -> str:
        """调试性问题的最终答案提示"""
        return f"答案：请使用AI代码解析功能，它会帮你逐行分析代码并指出问题。"

    def _hint_answer_application(self, kp_name: str) -> str:
        """应用性问题的最终答案提示"""
        return f"答案：请查看代码模板中的参考实现，理解后自己编写。"


# 全局单例
tutor_service = TutorService()
