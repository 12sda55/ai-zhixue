"""教学视频 Skills 系统

借鉴 OpenMAIC 的 WidgetType 设计，为 AI Tutor 定义教学视频的技能类型。
每种 Skill 对应一种教学场景，拥有专属的 prompt 模板和生成策略。

Skill 类型：
- concept_explanation: 概念讲解（适合基础概念、定义类知识点）
- algorithm_demo: 算法演示（适合排序、搜索等算法类知识点）
- data_structure_visual: 数据结构可视化（适合树、图、链表等结构类知识点）
- comparison: 对比分析（适合算法对比、结构对比）
- step_by_step: 步骤演示（适合操作流程、构建过程）
"""

import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class VideoSkill(str, Enum):
    """教学视频技能类型"""
    CONCEPT_EXPLANATION = "concept-explanation"
    ALGORITHM_DEMO = "algorithm-demo"
    DATA_STRUCTURE_VISUAL = "data-structure-visual"
    COMPARISON = "comparison"
    STEP_BY_STEP = "step-by-step"


# 知识点分类 → Skill 映射规则
CATEGORY_SKILL_MAP = {
    # 排序类 → 算法演示
    "排序": VideoSkill.ALGORITHM_DEMO,
    # 查找类 → 算法演示
    "查找": VideoSkill.ALGORITHM_DEMO,
    # 树结构 → 数据结构可视化
    "树结构": VideoSkill.DATA_STRUCTURE_VISUAL,
    # 图结构 → 数据结构可视化
    "图结构": VideoSkill.DATA_STRUCTURE_VISUAL,
    # 线性结构 → 数据结构可视化
    "线性结构": VideoSkill.DATA_STRUCTURE_VISUAL,
    # 哈希 → 数据结构可视化
    "哈希": VideoSkill.DATA_STRUCTURE_VISUAL,
    # 基础 → 概念讲解
    "基础": VideoSkill.CONCEPT_EXPLANATION,
}

# 特定知识点 ID → Skill 精确映射（优先级高于分类映射）
KP_SKILL_MAP = {
    # 排序算法
    "bubble_sort": VideoSkill.ALGORITHM_DEMO,
    "selection_sort": VideoSkill.ALGORITHM_DEMO,
    "insertion_sort": VideoSkill.ALGORITHM_DEMO,
    "quick_sort": VideoSkill.ALGORITHM_DEMO,
    "merge_sort": VideoSkill.ALGORITHM_DEMO,
    "heap_sort": VideoSkill.ALGORITHM_DEMO,
    "radix_sort": VideoSkill.ALGORITHM_DEMO,
    # 查找算法
    "binary_search": VideoSkill.ALGORITHM_DEMO,
    "sequential_search": VideoSkill.ALGORITHM_DEMO,
    "hash_search": VideoSkill.ALGORITHM_DEMO,
    # 数据结构
    "linked_list": VideoSkill.DATA_STRUCTURE_VISUAL,
    "stack": VideoSkill.DATA_STRUCTURE_VISUAL,
    "queue": VideoSkill.DATA_STRUCTURE_VISUAL,
    "binary_tree": VideoSkill.DATA_STRUCTURE_VISUAL,
    "bst": VideoSkill.DATA_STRUCTURE_VISUAL,
    "avl": VideoSkill.DATA_STRUCTURE_VISUAL,
    "red_black_tree": VideoSkill.DATA_STRUCTURE_VISUAL,
    "hash_table": VideoSkill.DATA_STRUCTURE_VISUAL,
    "graph_basics": VideoSkill.DATA_STRUCTURE_VISUAL,
    "graph_traversal": VideoSkill.DATA_STRUCTURE_VISUAL,
    # 对比类
    "sort_comparison": VideoSkill.COMPARISON,
    "tree_comparison": VideoSkill.COMPARISON,
    # 基础概念
    "time_complexity": VideoSkill.CONCEPT_EXPLANATION,
    "space_complexity": VideoSkill.CONCEPT_EXPLANATION,
    "recursion": VideoSkill.STEP_BY_STEP,
    "divide_conquer": VideoSkill.CONCEPT_EXPLANATION,
    "greedy": VideoSkill.ALGORITHM_DEMO,
    "dp": VideoSkill.STEP_BY_STEP,
}

# Skill → Prompt 模板 ID 映射
SKILL_TEMPLATE_MAP = {
    VideoSkill.CONCEPT_EXPLANATION: "concept-explanation",
    VideoSkill.ALGORITHM_DEMO: "algorithm-demo",
    VideoSkill.DATA_STRUCTURE_VISUAL: "data-structure-visual",
    VideoSkill.COMPARISON: "comparison",
    VideoSkill.STEP_BY_STEP: "step-by-step",
}

# Skill → 推荐视频时长（按 Provider 区分）
# Manim/Remotion: 1-3分钟完整教学视频
# Seedance: 5-10秒短视频片段
SKILL_DURATION_MAP = {
    VideoSkill.CONCEPT_EXPLANATION: 60,   # Manim: 1分钟概念讲解
    VideoSkill.ALGORITHM_DEMO: 90,        # Manim: 1.5分钟算法演示
    VideoSkill.DATA_STRUCTURE_VISUAL: 90, # Manim: 1.5分钟结构可视化
    VideoSkill.COMPARISON: 90,            # Manim: 1.5分钟对比分析
    VideoSkill.STEP_BY_STEP: 120,         # Manim: 2分钟步骤演示
}

# Seedance 短视频时长（最大10s）
SEEDANCE_DURATION_MAP = {
    VideoSkill.CONCEPT_EXPLANATION: 5,
    VideoSkill.ALGORITHM_DEMO: 10,
    VideoSkill.DATA_STRUCTURE_VISUAL: 10,
    VideoSkill.COMPARISON: 10,
    VideoSkill.STEP_BY_STEP: 10,
}

# 风格提示词
STYLE_HINTS = {
    "rigorous": "academic, professional, clean diagrams, white background, precise terminology, formal layout",
    "relaxed": "friendly, colorful, animated, engaging, cartoon-style, warm tones",
    "guided": "step-by-step, highlighted, clear progression, question-driven, discovery learning",
    "whiteboard": "hand-drawn style, whiteboard animation, sketch, chalk-on-board aesthetic",
}


def infer_skill(kp_id: str, category: str = "") -> VideoSkill:
    """根据知识点 ID 和分类推断最适合的 Skill 类型

    优先级：KP_SKILL_MAP 精确匹配 > CATEGORY_SKILL_MAP 分类匹配 > 默认
    """
    # 1. 精确匹配
    if kp_id in KP_SKILL_MAP:
        return KP_SKILL_MAP[kp_id]

    # 2. 分类匹配
    if category in CATEGORY_SKILL_MAP:
        return CATEGORY_SKILL_MAP[category]

    # 3. 关键词推断（借鉴 OpenMAIC 的 inferWidgetType）
    kp_lower = kp_id.lower()
    if any(kw in kp_lower for kw in ["sort", "search", "find", "排", "查"]):
        return VideoSkill.ALGORITHM_DEMO
    if any(kw in kp_lower for kw in ["tree", "graph", "list", "stack", "queue", "hash", "树", "图", "链"]):
        return VideoSkill.DATA_STRUCTURE_VISUAL
    if any(kw in kp_lower for kw in ["compare", "vs", "对比"]):
        return VideoSkill.COMPARISON
    if any(kw in kp_lower for kw in ["step", "process", "build", "步", "流程"]):
        return VideoSkill.STEP_BY_STEP

    # 4. 默认
    return VideoSkill.CONCEPT_EXPLANATION


def get_skill_template_id(skill: VideoSkill) -> str:
    """获取 Skill 对应的 prompt 模板 ID"""
    return SKILL_TEMPLATE_MAP.get(skill, "concept-explanation")


def get_skill_recommended_duration(skill: VideoSkill, provider: str = "manim") -> int:
    """获取 Skill 推荐的视频时长（秒）

    Args:
        skill: 视频技能类型
        provider: 提供者（manim/seedance），不同提供者推荐时长不同
    """
    if provider == "seedance":
        return SEEDANCE_DURATION_MAP.get(skill, 10)
    return SKILL_DURATION_MAP.get(skill, 60)


def get_style_hint(style: str) -> str:
    """获取风格提示词"""
    return STYLE_HINTS.get(style, STYLE_HINTS["relaxed"])
