"""路径规划Agent服务 - 对照 ai_architecture_plan.md Agent 7

核心功能：
1. 知识依赖图拓扑排序 + 个性化路径生成
2. 多路径对比（稳扎稳打/重点突破/实践驱动）
3. 路径模拟未来（2周/1月/2月预期效果）
4. 学习伙伴匹配（9维画像余弦相似度）
5. 学习方式推荐（画像驱动）
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.knowledge_graph import (
    KNOWLEDGE_GRAPH,
    KnowledgeNodeDef,
    get_knowledge_node,
    get_dependencies,
    get_all_dependents,
    get_topological_order,
    get_categories,
)
from app.schemas.profile import StudentProfile, Major, Stage, CognitiveStyle, LearningPace, DifficultyLevel

logger = logging.getLogger(__name__)


# ===== 数据模型 =====

class PathStrategy(str, Enum):
    """路径策略"""
    STEADY = "steady"           # 稳扎稳打：按依赖顺序逐步推进
    FOCUSED = "focused"         # 重点突破：先攻克核心知识点
    PRACTICE = "practice"       # 实践驱动：从编程题入手回补理论


class NodeStatus(str, Enum):
    """路径节点状态"""
    MASTERED = "mastered"       # 已掌握 mastery >= 0.7
    LEARNING = "learning"      # 学习中 0.3 <= mastery < 0.7
    TODO = "todo"              # 待学习 mastery < 0.3
    WEAK = "weak"              # 薄弱环节
    REVIEW = "review"          # 需复习（遗忘曲线触发）


class PathNode(BaseModel):
    """路径中的知识点节点"""
    id: str
    name: str
    category: str
    status: NodeStatus = NodeStatus.TODO
    mastery: float = 0.0
    dependencies: list[str] = Field(default_factory=list)
    optional: bool = False
    order: int = 0                     # 在路径中的顺序
    estimated_hours: float = 2.0       # 预估学习时长（小时）
    recommended_method: str = ""       # 推荐学习方式


class LearningPath(BaseModel):
    """学习路径"""
    strategy: PathStrategy
    nodes: list[PathNode] = Field(default_factory=list)
    total_nodes: int = 0
    mastered_count: int = 0
    learning_count: int = 0
    todo_count: int = 0
    weak_count: int = 0
    review_count: int = 0
    estimated_total_hours: float = 0.0
    completion_rate: float = 0.0       # 完成率 0-1


class PathSimulation(BaseModel):
    """路径模拟结果"""
    period: str                        # "2周" / "1月" / "2月"
    expected_mastery_gain: float = 0.0 # 预期掌握度提升
    expected_weak_cleared: int = 0     # 预期消除薄弱点数
    expected_questions: int = 0        # 预期做题数
    expected_code_exercises: int = 0   # 预期代码实操数
    risk_points: list[str] = Field(default_factory=list)  # 风险提示


class PartnerMatch(BaseModel):
    """学习伙伴匹配结果"""
    user_id: str
    similarity: float = 0.0           # 余弦相似度 0-1
    similar_points: list[str] = Field(default_factory=list)   # 相似点
    complementary_points: list[str] = Field(default_factory=list)  # 互补点


class MethodRecommendation(BaseModel):
    """学习方式推荐"""
    knowledge_point: str
    name: str
    primary_method: str               # 首选方式：document/animation/exercise/code_fill
    secondary_methods: list[str] = Field(default_factory=list)
    reason: str = ""


# ===== 知识点预估学习时长 =====

ESTIMATED_HOURS = {
    # 线性结构
    "array": 1.5, "linked_list": 2.0, "stack": 1.5, "queue": 1.5,
    "deque": 1.0, "string": 1.5,
    # 哈希
    "hash_table": 2.5,
    # 树结构
    "binary_tree": 3.0, "bst": 3.0, "avl": 3.5, "red_black_tree": 4.0,
    "heap": 2.0, "b_tree": 3.0,
    # 图结构
    "graph_basics": 2.0, "graph_traversal": 3.0, "topological_sort": 2.5,
    "shortest_path": 3.5, "mst": 3.0,
    # 排序
    "bubble_sort": 1.0, "selection_sort": 1.0, "insertion_sort": 1.0,
    "shell_sort": 1.5, "quick_sort": 2.5, "merge_sort": 2.5,
    "heap_sort": 2.0, "radix_sort": 1.5,
    # 查找
    "sequential_search": 0.5, "binary_search": 1.5, "bst_search": 1.5,
    # 基础
    "recursion": 2.0, "complexity": 2.0,
}


# ===== 核心路径规划服务 =====

class PathService:
    """路径规划Agent服务"""

    def get_node_status(self, kp_id: str, profile: StudentProfile) -> NodeStatus:
        """根据画像判断知识点状态"""
        mastery = profile.get_knowledge_mastery(kp_id)

        # 检查是否在薄弱环节
        is_weak = any(wp.knowledge_point == kp_id for wp in profile.weak_points)
        if is_weak:
            return NodeStatus.WEAK

        # 检查是否需要复习（遗忘曲线：7天未复习且mastery > 0.3）
        from app.schemas.profile import KnowledgeNode
        node = profile._find_knowledge_node(kp_id)
        if node and node.last_reviewed and node.mastery >= 0.3:
            days_since = (datetime.now() - node.last_reviewed).days
            if days_since >= 7:
                return NodeStatus.REVIEW

        # 根据掌握度判断
        if mastery >= 0.7:
            return NodeStatus.MASTERED
        elif mastery >= 0.3:
            return NodeStatus.LEARNING
        else:
            return NodeStatus.TODO

    def build_path_nodes(self, profile: StudentProfile, strategy: PathStrategy) -> list[PathNode]:
        """构建路径节点列表"""
        nodes = []
        topo_order = get_topological_order()

        for idx, kp_id in enumerate(topo_order):
            node_def = get_knowledge_node(kp_id)
            if not node_def:
                continue

            status = self.get_node_status(kp_id, profile)
            mastery = profile.get_knowledge_mastery(kp_id)

            path_node = PathNode(
                id=kp_id,
                name=node_def.name,
                category=node_def.category,
                status=status,
                mastery=round(mastery, 2),
                dependencies=node_def.dependencies,
                optional=node_def.optional,
                order=idx,
                estimated_hours=ESTIMATED_HOURS.get(kp_id, 2.0),
                recommended_method=self._recommend_method(kp_id, profile),
            )
            nodes.append(path_node)

        # 根据策略调整顺序
        if strategy == PathStrategy.FOCUSED:
            nodes = self._reorder_focused(nodes, profile)
        elif strategy == PathStrategy.PRACTICE:
            nodes = self._reorder_practice(nodes, profile)
        # STEADY: 保持拓扑排序原序

        # 重新编号
        for idx, node in enumerate(nodes):
            node.order = idx

        return nodes

    def generate_path(self, profile: StudentProfile, strategy: PathStrategy = PathStrategy.STEADY) -> LearningPath:
        """生成个性化学习路径

        对照 ai_architecture_plan.md Agent 7：
        - Step1: 确定起点（mastery最低且依赖已满足的知识点）和终点
        - Step2: 在依赖图上标记状态
        - Step3: 生成个性化路径，画像各维度影响路径
        """
        nodes = self.build_path_nodes(profile, strategy)

        # 统计
        mastered = sum(1 for n in nodes if n.status == NodeStatus.MASTERED)
        learning = sum(1 for n in nodes if n.status == NodeStatus.LEARNING)
        todo = sum(1 for n in nodes if n.status == NodeStatus.TODO)
        weak = sum(1 for n in nodes if n.status == NodeStatus.WEAK)
        review = sum(1 for n in nodes if n.status == NodeStatus.REVIEW)

        total_hours = sum(n.estimated_hours for n in nodes if n.status != NodeStatus.MASTERED)
        completion = mastered / len(nodes) if nodes else 0.0

        return LearningPath(
            strategy=strategy,
            nodes=nodes,
            total_nodes=len(nodes),
            mastered_count=mastered,
            learning_count=learning,
            todo_count=todo,
            weak_count=weak,
            review_count=review,
            estimated_total_hours=round(total_hours, 1),
            completion_rate=round(completion, 2),
        )

    def generate_multi_path(self, profile: StudentProfile) -> dict[str, LearningPath]:
        """生成多路径对比 - 对照设计文档创新9

        三条策略路径：
        - 稳扎稳打：按依赖顺序逐步推进，适合稳步型
        - 重点突破：先攻克核心知识点，适合备考型
        - 实践驱动：从编程题入手回补理论，适合试错型
        """
        return {
            "steady": self.generate_path(profile, PathStrategy.STEADY),
            "focused": self.generate_path(profile, PathStrategy.FOCUSED),
            "practice": self.generate_path(profile, PathStrategy.PRACTICE),
        }

    def recommend_strategy(self, profile: StudentProfile) -> PathStrategy:
        """根据画像推荐路径策略"""
        # 备考阶段 → 重点突破
        if profile.stage == Stage.EXAM_PREP:
            return PathStrategy.FOCUSED

        # 试错型 → 实践驱动
        if profile.learning_pace == LearningPace.TRIAL_ERROR:
            return PathStrategy.PRACTICE

        # 实践型认知风格 → 实践驱动
        if profile.cognitive_style == CognitiveStyle.PRACTICAL:
            return PathStrategy.PRACTICE

        # 深思型/稳步型 → 稳扎稳打
        if profile.learning_pace in (LearningPace.DEEP_THINK, LearningPace.STEADY):
            return PathStrategy.STEADY

        # 默认稳扎稳打
        return PathStrategy.STEADY

    def simulate_future(self, profile: StudentProfile, path: LearningPath) -> list[PathSimulation]:
        """路径模拟未来 - 对照设计文档创新8

        预览2周/1月/2月后的预期效果
        """
        simulations = []

        # 计算基础学习速率（根据画像调整）
        base_rate = self._estimate_learning_rate(profile)

        # 待学习节点（非已掌握）
        pending_nodes = [n for n in path.nodes if n.status != NodeStatus.MASTERED]
        weak_nodes = [n for n in path.nodes if n.status == NodeStatus.WEAK]

        for period_label, days in [("2周", 14), ("1月", 30), ("2月", 60)]:
            available_hours = days * base_rate["hours_per_day"]
            # 预估能学完的知识点数
            accumulated_hours = 0.0
            nodes_learnable = 0
            for node in pending_nodes:
                accumulated_hours += node.estimated_hours
                if accumulated_hours <= available_hours:
                    nodes_learnable += 1
                else:
                    break

            # 预期掌握度提升
            mastery_gain = min(nodes_learnable / max(len(pending_nodes), 1), 1.0) * 0.5
            # 薄弱环节消除数
            weak_cleared = min(nodes_learnable, len(weak_nodes))
            # 预期做题数（每个知识点约5题）
            expected_questions = nodes_learnable * 5
            # 预期代码实操数（约40%的知识点需要实操）
            expected_code = int(nodes_learnable * 0.4)

            # 风险提示
            risks = []
            if weak_nodes:
                hardest_weak = max(weak_nodes, key=lambda n: n.estimated_hours)
                risks.append(f"薄弱点「{hardest_weak.name}」可能需要额外{hardest_weak.estimated_hours:.0f}小时")
            if profile.stage == Stage.EXAM_PREP and days < 30:
                risks.append("备考时间较紧，建议重点突破策略")
            if profile.difficulty_level == DifficultyLevel.BASIC and nodes_learnable < len(pending_nodes) * 0.5:
                risks.append("当前基础较弱，建议稳扎稳打，不要跳过前置知识")

            simulations.append(PathSimulation(
                period=period_label,
                expected_mastery_gain=round(mastery_gain, 2),
                expected_weak_cleared=weak_cleared,
                expected_questions=expected_questions,
                expected_code_exercises=expected_code,
                risk_points=risks,
            ))

        return simulations

    def match_partners(self, user_profile: StudentProfile, all_profiles: list[StudentProfile], limit: int = 5) -> list[PartnerMatch]:
        """学习伙伴匹配 - 对照设计文档创新10

        基于9维画像余弦相似度推荐学习伙伴
        """
        user_vec = self._profile_to_vector(user_profile)
        matches = []

        for other in all_profiles:
            if other.user_id == user_profile.user_id:
                continue

            other_vec = self._profile_to_vector(other)
            similarity = self._cosine_similarity(user_vec, other_vec)

            # 找相似点和互补点
            similar, complementary = self._find_similar_complementary(user_profile, other)

            matches.append(PartnerMatch(
                user_id=other.user_id,
                similarity=round(similarity, 3),
                similar_points=similar,
                complementary_points=complementary,
            ))

        # 按相似度排序
        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches[:limit]

    def recommend_next_step(self, profile: StudentProfile) -> Optional[PathNode]:
        """推荐下一步学习内容

        优先级：薄弱环节 > 待学习（依赖已满足）> 需复习 > 学习中
        """
        path = self.generate_path(profile, self.recommend_strategy(profile))

        # 优先1：薄弱环节
        weak_nodes = [n for n in path.nodes if n.status == NodeStatus.WEAK]
        if weak_nodes:
            # 选依赖已满足的薄弱点
            for node in weak_nodes:
                if self._dependencies_met(node, path.nodes):
                    return node

        # 优先2：待学习（依赖已满足）
        todo_nodes = [n for n in path.nodes if n.status == NodeStatus.TODO]
        for node in todo_nodes:
            if self._dependencies_met(node, path.nodes):
                return node

        # 优先3：需复习
        review_nodes = [n for n in path.nodes if n.status == NodeStatus.REVIEW]
        if review_nodes:
            return review_nodes[0]

        # 优先4：学习中
        learning_nodes = [n for n in path.nodes if n.status == NodeStatus.LEARNING]
        if learning_nodes:
            return learning_nodes[0]

        # 全部掌握
        return None

    def get_progress(self, profile: StudentProfile) -> dict:
        """获取学习进度概览"""
        path = self.generate_path(profile)
        categories = get_categories()

        # 按分类统计
        category_progress = {}
        for cat_name, kp_ids in categories.items():
            masteries = [profile.get_knowledge_mastery(kp) for kp in kp_ids]
            avg_mastery = sum(masteries) / len(masteries) if masteries else 0
            mastered_count = sum(1 for m in masteries if m >= 0.7)
            category_progress[cat_name] = {
                "total": len(kp_ids),
                "mastered": mastered_count,
                "avg_mastery": round(avg_mastery, 2),
            }

        return {
            "overall_completion": path.completion_rate,
            "total_nodes": path.total_nodes,
            "mastered_count": path.mastered_count,
            "learning_count": path.learning_count,
            "todo_count": path.todo_count,
            "weak_count": path.weak_count,
            "review_count": path.review_count,
            "estimated_remaining_hours": path.estimated_total_hours,
            "category_progress": category_progress,
        }

    def get_method_recommendations(self, profile: StudentProfile) -> list[MethodRecommendation]:
        """学习方式推荐 - 根据画像推荐每个知识点怎么学"""
        recommendations = []
        path = self.generate_path(profile)

        for node in path.nodes:
            if node.status == NodeStatus.MASTERED:
                continue

            method = self._recommend_method(node.id, profile)
            node_def = get_knowledge_node(node.id)
            name = node_def.name if node_def else node.id

            rec = MethodRecommendation(
                knowledge_point=node.id,
                name=name,
                primary_method=method,
                secondary_methods=self._secondary_methods(method, profile),
                reason=self._method_reason(method, profile),
            )
            recommendations.append(rec)

        return recommendations

    # ===== 内部方法 =====

    def _reorder_focused(self, nodes: list[PathNode], profile: StudentProfile) -> list[PathNode]:
        """重点突破策略重排：薄弱点优先，核心知识点优先"""
        # 核心知识点（被依赖最多的）
        core_kps = set()
        for node_def in KNOWLEDGE_GRAPH:
            dependents = get_all_dependents(node_def.id)
            if len(dependents) >= 3:
                core_kps.add(node_def.id)

        def sort_key(n: PathNode) -> tuple:
            # 薄弱最优先
            if n.status == NodeStatus.WEAK:
                return (0, -n.mastery)
            # 核心知识点次优先
            if n.id in core_kps and n.status != NodeStatus.MASTERED:
                return (1, -n.mastery)
            # 已掌握最后
            if n.status == NodeStatus.MASTERED:
                return (3, 0)
            # 其他
            return (2, -n.mastery)

        # 先按拓扑排序确保依赖关系，再按优先级分组
        mastered_ids = {n.id for n in nodes if n.status == NodeStatus.MASTERED}
        remaining = [n for n in nodes if n.status != NodeStatus.MASTERED]
        mastered = [n for n in nodes if n.status == NodeStatus.MASTERED]

        # 对非掌握节点按优先级排序，但保持依赖约束
        remaining.sort(key=sort_key)

        # 确保依赖在前：如果节点依赖的节点还没出现，把它移到后面
        result = list(mastered)
        placed = set(mastered_ids)
        for node in remaining:
            unmet = [d for d in node.dependencies if d not in placed]
            if unmet:
                # 把未满足的依赖先放入
                for dep_id in unmet:
                    dep_node = next((n for n in remaining if n.id == dep_id), None)
                    if dep_node and dep_node.id not in placed:
                        result.append(dep_node)
                        placed.add(dep_node.id)
            if node.id not in placed:
                result.append(node)
                placed.add(node.id)

        return result

    def _reorder_practice(self, nodes: list[PathNode], profile: StudentProfile) -> list[PathNode]:
        """实践驱动策略重排：有代码模板的优先，编程题驱动"""
        # 有代码模板的知识点
        from app.knowledge.code_templates import CODE_TEMPLATES
        code_kps = set(CODE_TEMPLATES.keys())

        def sort_key(n: PathNode) -> tuple:
            if n.status == NodeStatus.MASTERED:
                return (3, 0)
            # 有代码模板的优先
            if n.id in code_kps:
                if n.status == NodeStatus.WEAK:
                    return (0, -n.mastery)
                return (1, -n.mastery)
            return (2, -n.mastery)

        mastered_ids = {n.id for n in nodes if n.status == NodeStatus.MASTERED}
        remaining = [n for n in nodes if n.status != NodeStatus.MASTERED]
        mastered = [n for n in nodes if n.status == NodeStatus.MASTERED]

        remaining.sort(key=sort_key)

        result = list(mastered)
        placed = set(mastered_ids)
        for node in remaining:
            unmet = [d for d in node.dependencies if d not in placed]
            for dep_id in unmet:
                dep_node = next((n for n in remaining if n.id == dep_id), None)
                if dep_node and dep_node.id not in placed:
                    result.append(dep_node)
                    placed.add(dep_node.id)
            if node.id not in placed:
                result.append(node)
                placed.add(node.id)

        return result

    def _recommend_method(self, kp_id: str, profile: StudentProfile) -> str:
        """推荐学习方式

        对照设计文档：
        - 深思型→先文档
        - 视觉型→先动画
        - 试错型→先做题
        - 实践型→先代码填空
        """
        if profile.cognitive_style == CognitiveStyle.PRACTICAL:
            return "code_fill"
        elif profile.cognitive_style == CognitiveStyle.VISUAL:
            return "animation"
        elif profile.learning_pace == LearningPace.TRIAL_ERROR:
            return "exercise"
        elif profile.learning_pace == LearningPace.DEEP_THINK:
            return "document"
        else:
            return "document"

    def _secondary_methods(self, primary: str, profile: StudentProfile) -> list[str]:
        """次要学习方式"""
        all_methods = ["document", "animation", "exercise", "code_fill"]
        secondary = [m for m in all_methods if m != primary]
        return secondary[:2]

    def _method_reason(self, method: str, profile: StudentProfile) -> str:
        """推荐理由"""
        reasons = {
            "document": "详细文档讲解适合你深入理解原理",
            "animation": "可视化动画演示帮助你直观理解",
            "exercise": "通过做题快速发现知识盲点",
            "code_fill": "代码填空挑战帮助你动手实践",
        }
        return reasons.get(method, "推荐的学习方式")

    def _dependencies_met(self, node: PathNode, all_nodes: list[PathNode]) -> bool:
        """检查节点的依赖是否已满足（已掌握或学习中）"""
        node_map = {n.id: n for n in all_nodes}
        for dep_id in node.dependencies:
            dep_node = node_map.get(dep_id)
            if dep_node and dep_node.status not in (NodeStatus.MASTERED, NodeStatus.LEARNING):
                return False
        return True

    def _estimate_learning_rate(self, profile: StudentProfile) -> dict:
        """估算学习速率"""
        # 基础：每天2小时
        hours_per_day = 2.0

        # 专业背景加成
        if profile.major in (Major.CS, Major.RELATED):
            hours_per_day *= 1.2  # 有基础学得快

        # 难度偏好调整
        if profile.difficulty_level == DifficultyLevel.ADVANCED:
            hours_per_day *= 1.1
        elif profile.difficulty_level == DifficultyLevel.BASIC:
            hours_per_day *= 0.9

        # 阶段调整
        if profile.stage == Stage.EXAM_PREP:
            hours_per_day *= 1.3  # 备考投入更多

        return {"hours_per_day": round(hours_per_day, 1)}

    def _profile_to_vector(self, profile: StudentProfile) -> list[float]:
        """将9维画像转为数值向量（用于余弦相似度计算）"""
        vec = []

        # 维度1: 专业背景 → 0-1
        major_map = {Major.CS: 1.0, Major.RELATED: 0.7, Major.NON_CS: 0.3, Major.CROSS: 0.5}
        vec.append(major_map.get(profile.major, 0.5))

        # 维度2: 当前阶段 → 0-1
        stage_map = {Stage.PREVIEW: 0.25, Stage.SYNCHRONOUS: 0.5, Stage.REVIEW: 0.75, Stage.EXAM_PREP: 1.0}
        vec.append(stage_map.get(profile.stage, 0.5))

        # 维度3: 知识基础平均掌握度
        topo = get_topological_order()
        masteries = [profile.get_knowledge_mastery(kp) for kp in topo]
        vec.append(sum(masteries) / len(masteries) if masteries else 0.0)

        # 维度4: 认知风格 → 0-1
        style_map = {CognitiveStyle.VISUAL: 0.33, CognitiveStyle.VERBAL: 0.66, CognitiveStyle.PRACTICAL: 1.0}
        vec.append(style_map.get(profile.cognitive_style, 0.5))

        # 维度5: 薄弱环节数量（归一化）
        vec.append(min(len(profile.weak_points) / 10.0, 1.0))

        # 维度6: 学习目标数量（归一化）
        vec.append(min(len(profile.learning_goals) / 5.0, 1.0))

        # 维度7: 学习节奏 → 0-1
        pace_map = {LearningPace.TRIAL_ERROR: 0.33, LearningPace.DEEP_THINK: 0.66, LearningPace.STEADY: 1.0}
        vec.append(pace_map.get(profile.learning_pace, 0.5))

        # 维度8: 学习偏好 → 0-1 (暂用0.5)
        vec.append(0.5)

        # 维度9: 难度偏好 → 0-1
        diff_map = {DifficultyLevel.BASIC: 0.33, DifficultyLevel.INTERMEDIATE: 0.66, DifficultyLevel.ADVANCED: 1.0}
        vec.append(diff_map.get(profile.difficulty_level, 0.5))

        return vec

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2) or not vec1:
            return 0.0

        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    def _find_similar_complementary(self, p1: StudentProfile, p2: StudentProfile) -> tuple[list[str], list[str]]:
        """找两个画像的相似点和互补点"""
        similar = []
        complementary = []

        # 专业背景
        if p1.major == p2.major:
            similar.append(f"同为{p1.major.value}专业")
        else:
            complementary.append(f"专业不同，可互相分享视角")

        # 阶段
        if p1.stage == p2.stage:
            similar.append(f"同处{p1.stage.value}阶段")

        # 认知风格
        if p1.cognitive_style == p2.cognitive_style:
            similar.append(f"同为{p1.cognitive_style.value}型学习者")

        # 知识点掌握对比
        topo = get_topological_order()
        p1_strong = [kp for kp in topo if p1.get_knowledge_mastery(kp) >= 0.7]
        p2_strong = [kp for kp in topo if p2.get_knowledge_mastery(kp) >= 0.7]

        p1_only = set(p1_strong) - set(p2_strong)
        p2_only = set(p2_strong) - set(p1_strong)

        for kp in list(p2_only)[:3]:
            node_def = get_knowledge_node(kp)
            if node_def:
                complementary.append(f"他已掌握{node_def.name}，你还在学")

        for kp in list(p1_only)[:3]:
            node_def = get_knowledge_node(kp)
            if node_def:
                complementary.append(f"你已掌握{node_def.name}，可以帮他")

        # 薄弱环节重叠
        p1_weak = {wp.knowledge_point for wp in p1.weak_points}
        p2_weak = {wp.knowledge_point for wp in p2.weak_points}
        common_weak = p1_weak & p2_weak
        if common_weak:
            names = []
            for kp in list(common_weak)[:3]:
                node_def = get_knowledge_node(kp)
                names.append(node_def.name if node_def else kp)
            similar.append(f"共同薄弱点：{', '.join(names)}")

        return similar, complementary


# 全局单例
path_service = PathService()
