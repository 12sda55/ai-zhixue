"""画像规则引擎 - 严格对照 ai_architecture_plan.md 的11条P0规则

P0核心规则：
1. 答题正确 → 知识基础 +delta×难度系数
2. 答题错误 → 知识基础 -delta×难度系数
3. 连续正确N题 → 知识基础 +delta，标记巩固，从薄弱移除，可提升难度
4. 连续错误N题 → 知识基础 -delta，立即加入薄弱，可降低难度
5. 自述薄弱 → 知识基础 -delta，立即加入薄弱
6. 自述已掌握 → 知识基础 设为指定值
7. 表达困惑 → 知识基础 -delta，累计N次加入薄弱
8. N天未复习 → 知识基础 -decay_rate%
9. 1-N次迭代通过 → 知识基础 +delta
10. N+次迭代通过 → 知识基础 +delta，疑似薄弱
11. 性能偏离理论值 → 知识基础 -delta，加入薄弱

规则优先级：自述信息 > 行为数据 > 隐式推断
所有参数可通过 rule_params.json 配置
"""

from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.profile import (
    StudentProfile, DifficultyLevel, WeakPoint, ProfileChangeEvent
)

logger = logging.getLogger(__name__)

# ===== 事件定义 =====

class EventType(str, Enum):
    """学习行为事件类型"""
    # 答题类
    ANSWER_CORRECT = "answer_correct"
    ANSWER_WRONG = "answer_wrong"
    CONSECUTIVE_CORRECT_3 = "consecutive_correct_3"
    CONSECUTIVE_WRONG_2 = "consecutive_wrong_2"
    # 对话类
    SELF_REPORT_WEAK = "self_report_weak"
    SELF_REPORT_MASTERED = "self_report_mastered"
    EXPRESS_CONFUSION = "express_confusion"
    # 代码实操类
    CODE_PASS_1_2_ITERATIONS = "code_pass_1_2_iterations"
    CODE_PASS_6_PLUS_ITERATIONS = "code_pass_6_plus_iterations"
    CODE_PERFORMANCE_DEVIATION = "code_performance_deviation"
    # 别名（API层使用）
    CODE_PASS_QUICK = "code_pass_1_2_iterations"
    CODE_PASS_SLOW = "code_pass_6_plus_iterations"
    # 定时类
    FORGETTING_CURVE_DECAY = "forgetting_curve_decay"


class LearningEvent(BaseModel):
    """学习行为事件"""
    event_type: EventType
    user_id: str
    knowledge_point: str
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    data: dict = Field(default_factory=dict)  # 额外数据
    timestamp: datetime = Field(default_factory=datetime.now)


# ===== 规则引擎 =====

class ProfileRuleEngine:
    """画像规则引擎 - 处理11条P0规则，参数可配置"""

    def __init__(self, config_path: Optional[str] = None):
        """初始化规则引擎，加载配置参数

        Args:
            config_path: 配置文件路径，默认为同目录下的 rule_params.json
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "rule_params.json")

        self._params = self._load_config(config_path)
        self._rules = self._params.get("rules", {})
        self._diff_multiplier = self._build_difficulty_map(
            self._params.get("difficulty_multiplier", {}),
            {"basic": 0.8, "intermediate": 1.0, "advanced": 1.2}
        )
        self._diff_multiplier_wrong = self._build_difficulty_map(
            self._params.get("difficulty_multiplier_wrong", {}),
            {"basic": 1.2, "intermediate": 1.0, "advanced": 0.8}
        )
        self._event_priority = self._params.get("event_priority", {})

    def _load_config(self, config_path: str) -> dict:
        """加载JSON配置文件"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                params = json.load(f)
            logger.info(f"规则参数配置已加载: {config_path}")
            return params
        except FileNotFoundError:
            logger.warning(f"规则参数配置文件不存在: {config_path}，使用默认值")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"规则参数配置文件格式错误: {e}，使用默认值")
            return {}

    def _build_difficulty_map(self, config: dict, defaults: dict) -> dict:
        """构建难度系数映射，配置优先，缺省用默认值"""
        result = {}
        for level_name, default_val in defaults.items():
            level_enum = DifficultyLevel(level_name)
            result[level_enum] = config.get(level_name, default_val)
        return result

    def _rule_param(self, rule_name: str, param: str, default):
        """获取规则参数，缺省用默认值"""
        rule_cfg = self._rules.get(rule_name, {})
        return rule_cfg.get(param, default)

    def get_event_priority(self, event_type: EventType) -> int:
        """获取事件优先级（自述3 > 行为2 > 隐式1）"""
        return self._event_priority.get(event_type.value, 1)

    def process_event(self, event: LearningEvent, profile: StudentProfile) -> list[ProfileChangeEvent]:
        """处理一个学习事件，返回画像变更列表"""
        changes = []
        handler = self._get_handler(event.event_type)
        if handler:
            changes = handler(event, profile)

        # 边界检查：所有mastery在0-1之间
        self._validate_mastery(profile)

        # 更新时间戳
        profile.updated_at = datetime.now()

        return changes

    def process_events_sorted(self, events: list[LearningEvent], profile: StudentProfile) -> list[ProfileChangeEvent]:
        """按优先级排序后批量处理事件（自述 > 行为 > 隐式推断）

        高优先级事件先处理，确保自述信息对画像的影响不被后续低优先级事件覆盖。
        例如：用户自述已掌握，但答题错误 → 自述优先，错误只做标记不覆盖。
        """
        # 按优先级降序排序（高优先级先处理）
        sorted_events = sorted(
            events,
            key=lambda e: self.get_event_priority(e.event_type),
            reverse=True
        )

        all_changes = []
        for event in sorted_events:
            changes = self.process_event(event, profile)
            all_changes.extend(changes)

        return all_changes

    def _get_handler(self, event_type: EventType):
        """根据事件类型获取处理函数"""
        handlers = {
            EventType.ANSWER_CORRECT: self._rule_answer_correct,
            EventType.ANSWER_WRONG: self._rule_answer_wrong,
            EventType.CONSECUTIVE_CORRECT_3: self._rule_consecutive_correct,
            EventType.CONSECUTIVE_WRONG_2: self._rule_consecutive_wrong,
            EventType.SELF_REPORT_WEAK: self._rule_self_report_weak,
            EventType.SELF_REPORT_MASTERED: self._rule_self_report_mastered,
            EventType.EXPRESS_CONFUSION: self._rule_express_confusion,
            EventType.FORGETTING_CURVE_DECAY: self._rule_forgetting_decay,
            EventType.CODE_PASS_1_2_ITERATIONS: self._rule_code_pass_quick,
            EventType.CODE_PASS_6_PLUS_ITERATIONS: self._rule_code_pass_slow,
            EventType.CODE_PERFORMANCE_DEVIATION: self._rule_code_performance_deviation,
        }
        return handlers.get(event_type)

    # ===== 规则1：答题正确 → +delta×难度系数 =====
    def _rule_answer_correct(self, event: LearningEvent, profile: StudentProfile) -> list[ProfileChangeEvent]:
        delta = self._rule_param("answer_correct", "delta", 0.08)
        old_mastery = profile.get_knowledge_mastery(event.knowledge_point)
        actual_delta = delta * self._diff_multiplier[event.difficulty]
        new_mastery = old_mastery + actual_delta
        profile.set_knowledge_mastery(event.knowledge_point, new_mastery)
        return [ProfileChangeEvent(
            user_id=event.user_id, dimension="knowledge_base",
            field=event.knowledge_point, old_value=old_mastery,
            new_value=round(new_mastery, 4), reason="答题正确"
        )]

    # ===== 规则2：答题错误 → -delta×难度系数 =====
    def _rule_answer_wrong(self, event: LearningEvent, profile: StudentProfile) -> list[ProfileChangeEvent]:
        delta = self._rule_param("answer_wrong", "delta", 0.12)
        error_threshold = self._rule_param("answer_wrong", "error_count_threshold", 2)
        changes = []
        old_mastery = profile.get_knowledge_mastery(event.knowledge_point)
        actual_delta = delta * self._diff_multiplier_wrong[event.difficulty]
        new_mastery = old_mastery - actual_delta
        profile.set_knowledge_mastery(event.knowledge_point, new_mastery)
        changes.append(ProfileChangeEvent(
            user_id=event.user_id, dimension="knowledge_base",
            field=event.knowledge_point, old_value=old_mastery,
            new_value=round(new_mastery, 4), reason="答题错误"
        ))

        # 累计N次错误→加入薄弱环节
        error_count = event.data.get("total_error_count", 1)
        if error_count >= error_threshold:
            profile.add_weak_point(event.knowledge_point, f"答题错误{error_count}次")
            changes.append(ProfileChangeEvent(
                user_id=event.user_id, dimension="weak_points",
                field=event.knowledge_point, old_value=None,
                new_value="added", reason=f"答题错误累计{error_count}次"
            ))

        return changes

    # ===== 规则3：连续正确N题 → +delta，标记巩固，从薄弱移除 =====
    def _rule_consecutive_correct(self, event: LearningEvent, profile: StudentProfile) -> list[ProfileChangeEvent]:
        delta = self._rule_param("consecutive_correct", "delta", 0.15)
        threshold = self._rule_param("consecutive_correct", "threshold", 3)
        changes = []
        old_mastery = profile.get_knowledge_mastery(event.knowledge_point)
        new_mastery = old_mastery + delta
        profile.set_knowledge_mastery(event.knowledge_point, new_mastery)
        changes.append(ProfileChangeEvent(
            user_id=event.user_id, dimension="knowledge_base",
            field=event.knowledge_point, old_value=old_mastery,
            new_value=round(new_mastery, 4), reason=f"连续正确{threshold}题，标记巩固"
        ))

        # 从薄弱环节移除
        if any(wp.knowledge_point == event.knowledge_point for wp in profile.weak_points):
            profile.remove_weak_point(event.knowledge_point)
            changes.append(ProfileChangeEvent(
                user_id=event.user_id, dimension="weak_points",
                field=event.knowledge_point, old_value="in_weak",
                new_value="removed", reason=f"连续正确{threshold}题，从薄弱移除"
            ))

        # 可提升难度
        if profile.difficulty_level == DifficultyLevel.BASIC:
            profile.difficulty_level = DifficultyLevel.INTERMEDIATE
            changes.append(ProfileChangeEvent(
                user_id=event.user_id, dimension="difficulty_level",
                field="difficulty_level", old_value="basic",
                new_value="intermediate", reason=f"连续正确{threshold}题，提升难度"
            ))
        elif profile.difficulty_level == DifficultyLevel.INTERMEDIATE:
            profile.difficulty_level = DifficultyLevel.ADVANCED
            changes.append(ProfileChangeEvent(
                user_id=event.user_id, dimension="difficulty_level",
                field="difficulty_level", old_value="intermediate",
                new_value="advanced", reason=f"连续正确{threshold}题，提升难度"
            ))

        return changes

    # ===== 规则4：连续错误N题 → -delta，立即加入薄弱 =====
    def _rule_consecutive_wrong(self, event: LearningEvent, profile: StudentProfile) -> list[ProfileChangeEvent]:
        delta = self._rule_param("consecutive_wrong", "delta", 0.2)
        threshold = self._rule_param("consecutive_wrong", "threshold", 2)
        changes = []
        old_mastery = profile.get_knowledge_mastery(event.knowledge_point)
        new_mastery = old_mastery - delta
        profile.set_knowledge_mastery(event.knowledge_point, new_mastery)
        changes.append(ProfileChangeEvent(
            user_id=event.user_id, dimension="knowledge_base",
            field=event.knowledge_point, old_value=old_mastery,
            new_value=round(new_mastery, 4), reason=f"连续错误{threshold}题"
        ))

        # 立即加入薄弱环节
        profile.add_weak_point(event.knowledge_point, f"连续错误{threshold}题")
        changes.append(ProfileChangeEvent(
            user_id=event.user_id, dimension="weak_points",
            field=event.knowledge_point, old_value=None,
            new_value="added", reason=f"连续错误{threshold}题，立即加入薄弱"
        ))

        # 可降低难度
        if profile.difficulty_level == DifficultyLevel.ADVANCED:
            profile.difficulty_level = DifficultyLevel.INTERMEDIATE
            changes.append(ProfileChangeEvent(
                user_id=event.user_id, dimension="difficulty_level",
                field="difficulty_level", old_value="advanced",
                new_value="intermediate", reason=f"连续错误{threshold}题，降低难度"
            ))
        elif profile.difficulty_level == DifficultyLevel.INTERMEDIATE:
            profile.difficulty_level = DifficultyLevel.BASIC
            changes.append(ProfileChangeEvent(
                user_id=event.user_id, dimension="difficulty_level",
                field="difficulty_level", old_value="intermediate",
                new_value="basic", reason=f"连续错误{threshold}题，降低难度"
            ))

        return changes

    # ===== 规则5：自述薄弱 → -delta，立即加入薄弱 =====
    def _rule_self_report_weak(self, event: LearningEvent, profile: StudentProfile) -> list[ProfileChangeEvent]:
        delta = self._rule_param("self_report_weak", "delta", 0.1)
        changes = []
        old_mastery = profile.get_knowledge_mastery(event.knowledge_point)
        new_mastery = old_mastery - delta
        profile.set_knowledge_mastery(event.knowledge_point, new_mastery)
        changes.append(ProfileChangeEvent(
            user_id=event.user_id, dimension="knowledge_base",
            field=event.knowledge_point, old_value=old_mastery,
            new_value=round(new_mastery, 4), reason="自述薄弱"
        ))

        profile.add_weak_point(event.knowledge_point, "学生自述薄弱")
        changes.append(ProfileChangeEvent(
            user_id=event.user_id, dimension="weak_points",
            field=event.knowledge_point, old_value=None,
            new_value="added", reason="学生自述薄弱"
        ))

        return changes

    # ===== 规则6：自述已掌握 → 设为指定值 =====
    def _rule_self_report_mastered(self, event: LearningEvent, profile: StudentProfile) -> list[ProfileChangeEvent]:
        mastery_set = self._rule_param("self_report_mastered", "mastery_set", 0.7)
        old_mastery = profile.get_knowledge_mastery(event.knowledge_point)
        profile.set_knowledge_mastery(event.knowledge_point, mastery_set)
        return [ProfileChangeEvent(
            user_id=event.user_id, dimension="knowledge_base",
            field=event.knowledge_point, old_value=old_mastery,
            new_value=mastery_set, reason="自述已掌握（需验证）"
        )]

    # ===== 规则7：表达困惑 → -delta，累计N次加入薄弱 =====
    def _rule_express_confusion(self, event: LearningEvent, profile: StudentProfile) -> list[ProfileChangeEvent]:
        delta = self._rule_param("express_confusion", "delta", 0.1)
        confusion_threshold = self._rule_param("express_confusion", "confusion_count_threshold", 2)
        changes = []
        old_mastery = profile.get_knowledge_mastery(event.knowledge_point)
        new_mastery = old_mastery - delta
        profile.set_knowledge_mastery(event.knowledge_point, new_mastery)
        changes.append(ProfileChangeEvent(
            user_id=event.user_id, dimension="knowledge_base",
            field=event.knowledge_point, old_value=old_mastery,
            new_value=round(new_mastery, 4), reason="表达困惑"
        ))

        confusion_count = event.data.get("total_confusion_count", 1)
        if confusion_count >= confusion_threshold:
            profile.add_weak_point(event.knowledge_point, f"表达困惑{confusion_count}次")
            changes.append(ProfileChangeEvent(
                user_id=event.user_id, dimension="weak_points",
                field=event.knowledge_point, old_value=None,
                new_value="added", reason=f"表达困惑累计{confusion_count}次"
            ))

        return changes

    # ===== 规则8：N天未复习 → -decay_rate% =====
    def _rule_forgetting_decay(self, event: LearningEvent, profile: StudentProfile) -> list[ProfileChangeEvent]:
        days = self._rule_param("forgetting_decay", "days_threshold", 7)
        decay_rate = self._rule_param("forgetting_decay", "decay_rate", 0.05)
        old_mastery = profile.get_knowledge_mastery(event.knowledge_point)
        new_mastery = old_mastery * (1 - decay_rate)
        profile.set_knowledge_mastery(event.knowledge_point, new_mastery)
        return [ProfileChangeEvent(
            user_id=event.user_id, dimension="knowledge_base",
            field=event.knowledge_point, old_value=old_mastery,
            new_value=round(new_mastery, 4), reason=f"{days}天未复习，遗忘曲线衰减"
        )]

    # ===== 规则9：1-N次迭代通过 → +delta =====
    def _rule_code_pass_quick(self, event: LearningEvent, profile: StudentProfile) -> list[ProfileChangeEvent]:
        delta = self._rule_param("code_pass_quick", "delta", 0.12)
        max_iter = self._rule_param("code_pass_quick", "max_iterations", 2)
        old_mastery = profile.get_knowledge_mastery(event.knowledge_point)
        new_mastery = old_mastery + delta
        profile.set_knowledge_mastery(event.knowledge_point, new_mastery)
        return [ProfileChangeEvent(
            user_id=event.user_id, dimension="knowledge_base",
            field=event.knowledge_point, old_value=old_mastery,
            new_value=round(new_mastery, 4), reason=f"代码实操1-{max_iter}次迭代通过"
        )]

    # ===== 规则10：N+次迭代通过 → +delta，疑似薄弱 =====
    def _rule_code_pass_slow(self, event: LearningEvent, profile: StudentProfile) -> list[ProfileChangeEvent]:
        delta = self._rule_param("code_pass_slow", "delta", 0.03)
        min_iter = self._rule_param("code_pass_slow", "min_iterations", 6)
        changes = []
        old_mastery = profile.get_knowledge_mastery(event.knowledge_point)
        new_mastery = old_mastery + delta
        profile.set_knowledge_mastery(event.knowledge_point, new_mastery)
        changes.append(ProfileChangeEvent(
            user_id=event.user_id, dimension="knowledge_base",
            field=event.knowledge_point, old_value=old_mastery,
            new_value=round(new_mastery, 4), reason=f"代码实操{min_iter}+次迭代通过"
        ))

        # 疑似薄弱
        profile.add_weak_point(event.knowledge_point, f"代码实操{min_iter}+次迭代才通过")
        changes.append(ProfileChangeEvent(
            user_id=event.user_id, dimension="weak_points",
            field=event.knowledge_point, old_value=None,
            new_value="added", reason=f"代码实操{min_iter}+次迭代，疑似薄弱"
        ))

        return changes

    # ===== 规则11：性能偏离理论值 → -delta，加入薄弱 =====
    def _rule_code_performance_deviation(self, event: LearningEvent, profile: StudentProfile) -> list[ProfileChangeEvent]:
        delta = self._rule_param("code_performance_deviation", "delta", 0.1)
        changes = []
        old_mastery = profile.get_knowledge_mastery(event.knowledge_point)
        new_mastery = old_mastery - delta
        profile.set_knowledge_mastery(event.knowledge_point, new_mastery)
        changes.append(ProfileChangeEvent(
            user_id=event.user_id, dimension="knowledge_base",
            field=event.knowledge_point, old_value=old_mastery,
            new_value=round(new_mastery, 4), reason="代码性能偏离理论值"
        ))

        profile.add_weak_point(event.knowledge_point, "代码性能偏离理论值")
        changes.append(ProfileChangeEvent(
            user_id=event.user_id, dimension="weak_points",
            field=event.knowledge_point, old_value=None,
            new_value="added", reason="代码性能偏离理论值"
        ))

        return changes

    # ===== 工具方法 =====

    def _validate_mastery(self, profile: StudentProfile) -> None:
        """边界检查：所有mastery在0-1之间"""
        for node_id, node in profile.knowledge_tree.items():
            self._clamp_node_mastery(node)

    def _clamp_node_mastery(self, node) -> None:
        """递归检查并修正mastery值"""
        node.mastery = max(0.0, min(1.0, node.mastery))
        for child in node.children.values():
            self._clamp_node_mastery(child)

    def check_forgetting_decay(self, profile: StudentProfile) -> list[ProfileChangeEvent]:
        """检查所有知识点的遗忘衰减（定时任务调用），递归检查子节点"""
        days = self._rule_param("forgetting_decay", "days_threshold", 7)
        changes = []
        now = datetime.now()
        threshold_time = now - timedelta(days=days)

        def _check_node(prefix: str, node) -> None:
            """递归检查节点及其子节点"""
            # 检查当前节点
            if node.last_reviewed and node.last_reviewed < threshold_time:
                if node.mastery > 0:
                    kp = f"{prefix}" if prefix else ""
                    if kp:
                        event = LearningEvent(
                            event_type=EventType.FORGETTING_CURVE_DECAY,
                            user_id=profile.user_id,
                            knowledge_point=kp,
                        )
                        changes.extend(self.process_event(event, profile))
            # 递归检查子节点
            for child_name, child_node in node.children.items():
                child_path = f"{prefix}.{child_name}" if prefix else child_name
                _check_node(child_path, child_node)

        for node_id, node in profile.knowledge_tree.items():
            _check_node(node_id, node)

        return changes
