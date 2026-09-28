"""画像数据模型 - 严格对照 ai_architecture_plan.md 的9维度定义

9维度：
1. 专业背景（静态）
2. 当前阶段（低频）
3. 知识基础（高频，树形JSON）
4. 认知风格（低频，首次显式询问）
5. 薄弱环节（高频）
6. 学习目标（低频）
7. 学习节奏（中频，试错型/深思型/稳步型）
8. 学习偏好（中频，独立型/社交型/混合型）
9. 难度偏好（中频，基础/进阶/挑战）
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ===== 枚举类型 =====

class Major(str, Enum):
    """专业背景"""
    CS = "computer_science"       # 计算机科学
    RELATED = "related_major"     # 相关专业（数学、信息等）
    NON_CS = "non_cs"            # 非计算机
    CROSS = "cross_exam"         # 跨考


class Stage(str, Enum):
    """当前阶段"""
    PREVIEW = "preview"           # 预习
    SYNCHRONOUS = "synchronous"   # 同步学习
    REVIEW = "review"             # 复习
    EXAM_PREP = "exam_prep"       # 备考


class CognitiveStyle(str, Enum):
    """认知风格"""
    VISUAL = "visual"       # 视觉型
    VERBAL = "verbal"       # 文字型
    PRACTICAL = "practical" # 实践型


class LearningPace(str, Enum):
    """学习节奏"""
    TRIAL_ERROR = "trial_error"  # 试错型
    DEEP_THINK = "deep_think"    # 深思型
    STEADY = "steady"            # 稳步型


class LearningPreference(str, Enum):
    """学习偏好"""
    INDEPENDENT = "independent"  # 独立型
    SOCIAL = "social"            # 社交型
    MIXED = "mixed"              # 混合型


class DifficultyLevel(str, Enum):
    """难度偏好"""
    BASIC = "basic"           # 基础
    INTERMEDIATE = "intermediate"  # 进阶
    ADVANCED = "advanced"     # 挑战


# ===== 知识基础树形结构 =====

class KnowledgeNode(BaseModel):
    """知识点节点 - 树形结构，表达掌握度和依赖关系"""
    mastery: float = Field(default=0.0, ge=0.0, le=1.0, description="掌握度 0-1")
    last_reviewed: Optional[datetime] = None
    children: dict[str, KnowledgeNode] = Field(default_factory=dict, description="子知识点")


# ===== 薄弱环节 =====

class WeakPoint(BaseModel):
    """薄弱环节条目"""
    knowledge_point: str
    reason: str = ""                # 原因：连续错误/自述/代码实操等
    error_count: int = 0            # 累计错误次数
    detected_at: datetime = Field(default_factory=datetime.now)
    last_failed_at: Optional[datetime] = None


# ===== 完整画像 =====

class StudentProfile(BaseModel):
    """学生画像 - 9维度，对照 ai_architecture_plan.md"""

    user_id: str

    # 维度1：专业背景（静态）
    major: Major = Major.NON_CS

    # 维度2：当前阶段（低频）
    stage: Stage = Stage.SYNCHRONOUS

    # 维度3：知识基础（高频，树形JSON）
    knowledge_tree: dict[str, KnowledgeNode] = Field(default_factory=dict)

    # 维度4：认知风格（低频）
    cognitive_style: CognitiveStyle = CognitiveStyle.VISUAL

    # 维度5：薄弱环节（高频）
    weak_points: list[WeakPoint] = Field(default_factory=list)

    # 维度6：学习目标（低频）
    learning_goals: list[str] = Field(default_factory=list)

    # 维度7：学习节奏（中频）
    learning_pace: LearningPace = LearningPace.STEADY

    # 维度8：学习偏好（中频）
    learning_preference: LearningPreference = LearningPreference.MIXED

    # 维度9：难度偏好（中频）
    difficulty_level: DifficultyLevel = DifficultyLevel.BASIC

    # 元数据
    conversation_count: int = 0       # 对话轮次（用于渐进型引导判断）
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def get_knowledge_mastery(self, knowledge_point: str) -> float:
        """获取指定知识点的掌握度"""
        node = self._find_knowledge_node(knowledge_point)
        return node.mastery if node else 0.0

    def set_knowledge_mastery(self, knowledge_point: str, mastery: float) -> None:
        """设置指定知识点的掌握度，不存在则自动创建（含依赖链）"""
        mastery = max(0.0, min(1.0, mastery))  # 边界检查
        node = self._find_knowledge_node(knowledge_point)
        if node:
            node.mastery = mastery
            node.last_reviewed = datetime.now()
        else:
            # 自动创建不存在的知识点节点（同时创建依赖链上的前置节点）
            self._ensure_dependency_chain(knowledge_point)
            self._create_knowledge_node(knowledge_point, mastery)

    def _ensure_dependency_chain(self, knowledge_point: str) -> None:
        """确保知识点依赖链上的前置节点都已创建

        当学生学习bst时，自动创建binary_tree、tree等前置节点。
        前置节点初始mastery=0.0，不设置last_reviewed（表示从未学过）。
        """
        from app.schemas.knowledge_graph import get_dependencies
        deps = get_dependencies(knowledge_point)
        for dep_id in deps:
            if self._find_knowledge_node(dep_id) is None:
                self._create_knowledge_node(dep_id, 0.0)

    def _create_knowledge_node(self, knowledge_point: str, mastery: float = 0.0) -> None:
        """创建知识点节点（支持多级路径，如 tree.bst）"""
        parts = knowledge_point.split(".")
        current = self.knowledge_tree
        for i, part in enumerate(parts):
            if part in current:
                node = current[part]
                current = node.children
            else:
                # 创建新节点
                is_leaf = (i == len(parts) - 1)
                new_node = KnowledgeNode(
                    mastery=mastery if is_leaf else 0.0,
                    last_reviewed=datetime.now() if is_leaf else None,
                )
                current[part] = new_node
                current = new_node.children

    def add_weak_point(self, knowledge_point: str, reason: str) -> None:
        """添加薄弱环节（避免重复）"""
        existing = [wp for wp in self.weak_points if wp.knowledge_point == knowledge_point]
        if not existing:
            self.weak_points.append(WeakPoint(
                knowledge_point=knowledge_point,
                reason=reason,
                error_count=1,
            ))
        else:
            existing[0].error_count += 1
            existing[0].last_failed_at = datetime.now()

    def remove_weak_point(self, knowledge_point: str) -> None:
        """移除薄弱环节"""
        self.weak_points = [wp for wp in self.weak_points if wp.knowledge_point != knowledge_point]

    def is_new_user(self) -> bool:
        """是否新用户（前5轮对话）"""
        return self.conversation_count < 5

    def _find_knowledge_node(self, knowledge_point: str) -> Optional[KnowledgeNode]:
        """在知识树中查找知识点节点（支持多级路径，如 tree.bst）"""
        parts = knowledge_point.split(".")
        current = self.knowledge_tree
        node = None
        for part in parts:
            if part in current:
                node = current[part]
                current = node.children
            else:
                return None
        return node


# ===== 画像变更事件 =====

class ProfileChangeEvent(BaseModel):
    """画像变更事件 - 广播给其他Agent"""
    user_id: str
    dimension: str              # 变更的维度名称
    field: str                  # 变更的字段
    old_value: object = None
    new_value: object = None
    reason: str = ""            # 变更原因（如"答题错误"）
    timestamp: datetime = Field(default_factory=datetime.now)
