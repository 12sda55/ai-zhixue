"""创新功能集成服务 - 对照 ai_architecture_plan.md 14个创新点

包含：
1. 学习效果仪表盘（创新14）- 雷达图+成就系统
2. 代码进化轨迹（创新9）- 记录迭代过程
3. 性能擂台（创新8）- 多规模性能曲线vs理论值
4. 代码小社区（创新13）- 分享+评分+AI点评
5. 遗忘曲线复习调度（创新3）- 最优时间点推送复习
"""

from __future__ import annotations

import logging
import math
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.profile import (
    StudentProfile, DifficultyLevel, CognitiveStyle, LearningPace, WeakPoint,
)
from app.schemas.knowledge_graph import (
    get_knowledge_node, get_topological_order, get_categories, KNOWLEDGE_GRAPH,
)

logger = logging.getLogger(__name__)


# ===== 数据模型 =====

class Achievement(BaseModel):
    """成就"""
    id: str
    name: str
    description: str
    icon: str = "🏆"
    unlocked: bool = False
    unlocked_at: Optional[str] = None
    progress: float = 0.0  # 0-1


class RadarData(BaseModel):
    """雷达图数据"""
    categories: list[str] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)


class DashboardData(BaseModel):
    """仪表盘数据"""
    overall_completion: float = 0.0
    total_study_hours: float = 0.0
    questions_answered: int = 0
    questions_correct: int = 0
    code_submissions: int = 0
    code_passed: int = 0
    weak_points_count: int = 0
    streak_days: int = 0
    radar: Optional[RadarData] = None
    achievements: list[Achievement] = Field(default_factory=list)
    recent_activities: list[dict] = Field(default_factory=list)


class CodeIteration(BaseModel):
    """代码迭代记录"""
    iteration: int
    code: str
    status: str  # syntax_error / runtime_error / logic_error / passed / optimized
    timestamp: str = ""
    error_message: str = ""
    test_results: list[dict] = Field(default_factory=list)


class CodeEvolution(BaseModel):
    """代码进化轨迹"""
    knowledge_point: str
    template_id: str = ""
    iterations: list[CodeIteration] = Field(default_factory=list)
    total_iterations: int = 0
    final_status: str = ""
    started_at: str = ""
    completed_at: str = ""


class PerformanceResult(BaseModel):
    """性能测试结果"""
    scale: int
    actual_time_ms: float
    theoretical_time_ms: float = 0.0
    deviation: float = 0.0  # 偏离百分比


class PerformanceArena(BaseModel):
    """性能擂台结果"""
    knowledge_point: str
    code: str
    complexity_class: str = ""  # O(n), O(n²), O(n log n) etc.
    results: list[PerformanceResult] = Field(default_factory=list)
    verdict: str = ""  # consistent / deviation / invalid


class SharedCode(BaseModel):
    """共享代码"""
    id: str = ""
    user_id: str = ""
    knowledge_point: str = ""
    title: str = ""
    code: str = ""
    rating: float = 0.0
    rating_count: int = 0
    tags: list[str] = Field(default_factory=list)
    ai_review: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ReviewSchedule(BaseModel):
    """复习调度"""
    knowledge_point: str
    name: str = ""
    next_review_at: str = ""
    urgency: str = "normal"  # urgent / soon / normal
    days_overdue: int = 0


# ===== 成就定义 =====

ACHIEVEMENTS = [
    Achievement(id="first_login", name="初来乍到", description="完成首次登录和冷启动", icon="🌟"),
    Achievement(id="first_question", name="初试锋芒", description="完成第一道练习题", icon="✏️"),
    Achievement(id="streak_3", name="三日之约", description="连续学习3天", icon="🔥"),
    Achievement(id="streak_7", name="一周坚持", description="连续学习7天", icon="💪"),
    Achievement(id="master_1", name="初窥门径", description="掌握1个知识点", icon="📖"),
    Achievement(id="master_5", name="小有所成", description="掌握5个知识点", icon="📚"),
    Achievement(id="master_10", name="学富五车", description="掌握10个知识点", icon="🎓"),
    Achievement(id="code_first", name="代码新手", description="首次提交代码", icon="💻"),
    Achievement(id="code_pass", name="代码达人", description="代码一次通过", icon="⚡"),
    Achievement(id="weak_cleared", name="攻克难关", description="消除一个薄弱环节", icon="🎯"),
    Achievement(id="question_50", name="题海战术", description="完成50道题", icon="📝"),
    Achievement(id="question_100", name="百题斩", description="完成100道题", icon="🏅"),
    Achievement(id="share_code", name="乐于分享", description="分享一段代码", icon="🤝"),
]


# ===== 服务实现 =====

class InnovationService:
    """创新功能集成服务"""

    def __init__(self):
        pass
    # ===== 1. 学习效果仪表盘 =====

    def get_dashboard(self, profile: StudentProfile) -> DashboardData:
        """获取学习效果仪表盘数据"""
        # 雷达图数据
        radar = self._build_radar(profile)

        # 成就系统
        achievements = self._check_achievements(profile)

        # 统计数据
        mastery_count = sum(
            1 for kp in get_topological_order()
            if profile.get_knowledge_mastery(kp) >= 0.7
        )

        # 近期活动
        activities = self._get_recent_activities(profile.user_id, limit=10)

        return DashboardData(
            overall_completion=mastery_count / len(get_topological_order()) if get_topological_order() else 0,
            total_study_hours=mastery_count * 2.5,  # 估算
            questions_answered=getattr(profile, "_questions_answered", 0),
            questions_correct=getattr(profile, "_questions_correct", 0),
            code_submissions=getattr(profile, "_code_submissions", 0),
            code_passed=getattr(profile, "_code_passed", 0),
            weak_points_count=len(profile.weak_points),
            streak_days=getattr(profile, "_streak_days", 1),
            radar=radar,
            achievements=achievements,
            recent_activities=list(reversed(activities)),
        )

    def _build_radar(self, profile: StudentProfile) -> RadarData:
        """构建雷达图数据"""
        categories = get_categories()
        cat_names = []
        values = []

        for cat_name, kp_ids in categories.items():
            cat_names.append(cat_name)
            masteries = [profile.get_knowledge_mastery(kp) for kp in kp_ids]
            avg = sum(masteries) / len(masteries) if masteries else 0
            values.append(round(avg, 2))

        return RadarData(categories=cat_names, values=values)

    def _check_achievements(self, profile: StudentProfile) -> list[Achievement]:
        """检查成就解锁状态"""
        result = []
        mastery_count = sum(
            1 for kp in get_topological_order()
            if profile.get_knowledge_mastery(kp) >= 0.7
        )

        for ach in ACHIEVEMENTS:
            unlocked = False
            progress = 0.0

            if ach.id == "first_login":
                unlocked = profile.conversation_count > 0
                progress = 1.0 if unlocked else 0.0
            elif ach.id == "master_1":
                unlocked = mastery_count >= 1
                progress = min(mastery_count / 1, 1.0)
            elif ach.id == "master_5":
                unlocked = mastery_count >= 5
                progress = min(mastery_count / 5, 1.0)
            elif ach.id == "master_10":
                unlocked = mastery_count >= 10
                progress = min(mastery_count / 10, 1.0)
            elif ach.id == "weak_cleared":
                unlocked = len(profile.weak_points) < 5  # 曾经有薄弱但减少了
                progress = 0.5
            elif ach.id == "streak_3":
                unlocked = getattr(profile, "_streak_days", 0) >= 3
                progress = min(getattr(profile, "_streak_days", 0) / 3, 1.0)
            elif ach.id == "streak_7":
                unlocked = getattr(profile, "_streak_days", 0) >= 7
                progress = min(getattr(profile, "_streak_days", 0) / 7, 1.0)
            else:
                progress = 0.0

            result.append(Achievement(
                id=ach.id,
                name=ach.name,
                description=ach.description,
                icon=ach.icon,
                unlocked=unlocked,
                progress=round(progress, 2),
            ))

        return result

    # ===== 2. 代码进化轨迹 =====

    def record_code_iteration(
        self,
        user_id: str,
        knowledge_point: str,
        code: str,
        status: str,
        template_id: str = "",
        error_message: str = "",
        test_results: list[dict] = None,
        db=None,
    ) -> CodeEvolution:
        """记录代码迭代 - 写入MySQL"""
        import json as _json
        from app.core.database import SessionLocal

        if db is None:
            db = SessionLocal()

        try:
            from app.models.profile import CodeEvolutionModel
            # 获取当前迭代数
            existing = db.query(CodeEvolutionModel).filter(
                CodeEvolutionModel.user_id == user_id,
                CodeEvolutionModel.knowledge_point == knowledge_point,
                CodeEvolutionModel.template_id == template_id,
            ).all()
            iteration_num = len(existing) + 1

            model = CodeEvolutionModel(
                user_id=user_id,
                knowledge_point=knowledge_point,
                template_id=template_id,
                iteration=iteration_num,
                code=code,
                status=status,
                error_message=error_message,
                test_results_json=_json.dumps(test_results or [], ensure_ascii=False),
            )
            db.add(model)
            db.commit()
        except Exception as e:
            logger.warning("MySQL代码迭代写入失败: %s", e)
            db.rollback()

        # 记录活动
        self._add_activity(user_id, f"提交代码({knowledge_point}): {status}", "code")

        # 从MySQL读取完整的进化轨迹返回
        return self.get_code_evolution(user_id, knowledge_point, template_id, db=db)

    def get_code_evolution(self, user_id: str, knowledge_point: str, template_id: str = "", db=None) -> Optional[CodeEvolution]:
        """获取代码进化轨迹 - 查询MySQL"""
        import json as _json
        from app.core.database import SessionLocal

        if db is None:
            db = SessionLocal()

        try:
            from app.models.profile import CodeEvolutionModel

            models = db.query(CodeEvolutionModel).filter(
                CodeEvolutionModel.user_id == user_id,
                CodeEvolutionModel.knowledge_point == knowledge_point,
                CodeEvolutionModel.template_id == template_id,
            ).order_by(CodeEvolutionModel.iteration).all()

            if models:
                iterations = [
                    CodeIteration(
                        iteration=m.iteration,
                        code=m.code,
                        status=m.status,
                        timestamp=m.created_at.isoformat() if m.created_at else "",
                        error_message=m.error_message,
                        test_results=_json.loads(m.test_results_json) if m.test_results_json else [],
                    )
                    for m in models
                ]
                return CodeEvolution(
                    knowledge_point=knowledge_point,
                    template_id=template_id,
                    iterations=iterations,
                    total_iterations=len(iterations),
                    final_status=models[-1].status if models else "",
                    started_at=models[0].created_at.isoformat() if models else "",
                    completed_at=models[-1].created_at.isoformat() if models and models[-1].status in ("passed", "optimized") else "",
                )
        except Exception as e:
            logger.warning("MySQL代码进化查询失败: %s", e)

        return None

    # ===== 3. 性能擂台 =====

    def run_performance_arena(
        self,
        code: str,
        knowledge_point: str,
        complexity_class: str = "",
    ) -> PerformanceArena:
        """运行性能擂台

        对照设计文档创新8：多规模数据+性能曲线vs理论值
        """
        scales = [100, 1000, 10000, 100000]
        results = []

        for scale in scales:
            # 实际执行时间（使用本地subprocess）
            actual_time = self._measure_performance(code, scale)

            # 理论时间（基于复杂度类估算，以最小规模为基准）
            if results:
                baseline = results[0]
                if complexity_class == "O(n)":
                    theoretical = baseline.actual_time_ms * (scale / baseline.scale)
                elif complexity_class == "O(n²)":
                    theoretical = baseline.actual_time_ms * (scale / baseline.scale) ** 2
                elif complexity_class in ("O(n log n)", "O(nlogn)"):
                    ratio = (scale * math.log2(scale)) / (baseline.scale * math.log2(baseline.scale))
                    theoretical = baseline.actual_time_ms * ratio
                else:
                    theoretical = 0
            else:
                theoretical = actual_time  # 第一个点作为基准

            deviation = abs(actual_time - theoretical) / theoretical * 100 if theoretical > 0 else 0

            results.append(PerformanceResult(
                scale=scale,
                actual_time_ms=round(actual_time, 2),
                theoretical_time_ms=round(theoretical, 2),
                deviation=round(deviation, 1),
            ))

        # 判定
        avg_deviation = sum(r.deviation for r in results[1:]) / max(len(results) - 1, 1)
        if avg_deviation < 20:
            verdict = "consistent"
        elif avg_deviation < 50:
            verdict = "deviation"
        else:
            verdict = "invalid"

        return PerformanceArena(
            knowledge_point=knowledge_point,
            code=code,
            complexity_class=complexity_class,
            results=results,
            verdict=verdict,
        )

    def _measure_performance(self, code: str, scale: int) -> float:
        """测量代码在特定规模下的执行时间"""
        try:
            from app.services.code_service import code_sandbox
            # 生成测试输入
            test_input = f"n = {scale}"
            full_code = f"{test_input}\n{code}"

            start = time.time()
            result = code_sandbox.execute(code=full_code, test_cases=[])
            elapsed = (time.time() - start) * 1000  # ms

            if result.success:
                return min(elapsed, 5000)  # 上限5秒
            return 5000  # 超时或错误
        except Exception:
            return 5000

    # ===== 4. 代码小社区 =====

    def share_code(
        self,
        user_id: str,
        knowledge_point: str,
        title: str,
        code: str,
        tags: list[str] = None,
        db=None,
    ) -> SharedCode:
        """分享代码 - 写入MySQL"""
        import json as _json
        from app.core.database import SessionLocal

        if db is None:
            db = SessionLocal()

        code_id = str(uuid.uuid4())[:8]

        shared = SharedCode(
            id=code_id,
            user_id=user_id,
            knowledge_point=knowledge_point,
            title=title,
            code=code,
            tags=tags or [],
        )

        # AI自动点评
        shared.ai_review = self._ai_review_code(code, knowledge_point)

        # MySQL写入
        try:
            from app.models.profile import SharedCodeModel
            model = SharedCodeModel(
                id=code_id,
                user_id=user_id,
                knowledge_point=knowledge_point,
                title=title,
                code=code,
                tags_json=_json.dumps(tags or [], ensure_ascii=False),
                ai_review=shared.ai_review,
            )
            db.add(model)
            db.commit()
        except Exception as e:
            logger.warning("MySQL共享代码写入失败: %s", e)
            db.rollback()

        # 记录活动
        self._add_activity(user_id, f"分享了代码: {title}", "share")

        return shared

    def get_shared_codes(self, knowledge_point: str = None, sort_by: str = "rating", db=None) -> list[SharedCode]:
        """获取共享代码列表 - 查询MySQL"""
        import json as _json
        from app.core.database import SessionLocal

        if db is None:
            db = SessionLocal()

        try:
            from app.models.profile import SharedCodeModel
            query = db.query(SharedCodeModel)
            if knowledge_point:
                query = query.filter(SharedCodeModel.knowledge_point == knowledge_point)

            if sort_by == "rating":
                query = query.order_by(SharedCodeModel.rating.desc())
            elif sort_by == "newest":
                query = query.order_by(SharedCodeModel.created_at.desc())

            models = query.all()
            return [
                SharedCode(
                    id=m.id,
                    user_id=m.user_id,
                    knowledge_point=m.knowledge_point,
                    title=m.title,
                    code=m.code,
                    rating=m.rating,
                    rating_count=m.rating_count,
                    tags=_json.loads(m.tags_json) if m.tags_json else [],
                    ai_review=m.ai_review,
                    created_at=m.created_at.isoformat() if m.created_at else "",
                )
                for m in models
            ]
        except Exception as e:
            logger.warning("MySQL共享代码查询失败: %s", e)

        return []

    def rate_shared_code(self, code_id: str, rating: int, tags: list[str] = None, user_id: str = "", db=None) -> Optional[SharedCode]:
        """评分共享代码 - 写入MySQL"""
        import json as _json
        from app.core.database import SessionLocal

        if db is None:
            db = SessionLocal()

        rating = max(1, min(5, rating))

        try:
            from app.models.profile import SharedCodeModel, SharedCodeRatingModel
            code_model = db.query(SharedCodeModel).filter(SharedCodeModel.id == code_id).first()
            if not code_model:
                return None

            rating_model = SharedCodeRatingModel(
                code_id=code_id,
                user_id=user_id,
                rating=rating,
                tags_json=_json.dumps(tags or [], ensure_ascii=False),
            )
            db.add(rating_model)

            # 更新平均评分
            all_ratings = db.query(SharedCodeRatingModel).filter(SharedCodeRatingModel.code_id == code_id).all()
            avg = sum(r.rating for r in all_ratings) / len(all_ratings)
            code_model.rating = round(avg, 1)
            code_model.rating_count = len(all_ratings)

            if tags:
                existing_tags = set(_json.loads(code_model.tags_json)) if code_model.tags_json else set()
                code_model.tags_json = _json.dumps(list(existing_tags | set(tags)), ensure_ascii=False)

            db.commit()

            return SharedCode(
                id=code_id,
                user_id=code_model.user_id,
                knowledge_point=code_model.knowledge_point,
                title=code_model.title,
                code=code_model.code,
                rating=code_model.rating,
                rating_count=code_model.rating_count,
                tags=_json.loads(code_model.tags_json) if code_model.tags_json else [],
                ai_review=code_model.ai_review,
                created_at=code_model.created_at.isoformat() if code_model.created_at else "",
            )
        except Exception as e:
            logger.warning("MySQL共享代码评分失败: %s", e)
            db.rollback()

        return None

    def _ai_review_code(self, code: str, knowledge_point: str) -> str:
        """AI自动点评代码"""
        try:
            from app.core.llm import llm_client
            node_def = get_knowledge_node(knowledge_point)
            kp_name = node_def.name if node_def else knowledge_point

            prompt = f"""请对以下{kp_name}相关代码进行简短点评（100字以内）：
- 代码风格
- 算法正确性
- 可读性
- 一句话改进建议

代码：
```
{code[:500]}
```"""
            return llm_client.chat(messages=[{"role": "user", "content": prompt}], temperature=0.3)
        except Exception:
            return "代码已提交，暂无AI点评。"

    # ===== 5. 遗忘曲线复习调度 =====

    def get_review_schedule(self, profile: StudentProfile) -> list[ReviewSchedule]:
        """获取复习调度 - 对照设计文档创新3

        遗忘曲线模型：刚学完→1天→3天→7天→14天
        """
        schedule = []
        now = datetime.now()

        # 遗忘曲线间隔（天）
        review_intervals = [1, 3, 7, 14]

        for kp_id in get_topological_order():
            mastery = profile.get_knowledge_mastery(kp_id)
            if mastery < 0.3:
                continue  # 未学过的不需要复习

            node = profile._find_knowledge_node(kp_id)
            if not node or not node.last_reviewed:
                continue

            days_since = (now - node.last_reviewed).days

            # 确定下次复习时间
            next_interval = None
            for interval in review_intervals:
                if days_since < interval:
                    next_interval = interval
                    break

            if next_interval is None and days_since >= 14:
                # 超过14天，需要复习
                next_interval = 14

            if next_interval is not None:
                next_review = node.last_reviewed + timedelta(days=next_interval)
                days_overdue = (now - next_review).days

                node_def = get_knowledge_node(kp_id)
                name = node_def.name if node_def else kp_id

                urgency = "normal"
                if days_overdue > 3:
                    urgency = "urgent"
                elif days_overdue > 0:
                    urgency = "soon"

                schedule.append(ReviewSchedule(
                    knowledge_point=kp_id,
                    name=name,
                    next_review_at=next_review.isoformat(),
                    urgency=urgency,
                    days_overdue=max(days_overdue, 0),
                ))

        # 按紧急程度排序
        urgency_order = {"urgent": 0, "soon": 1, "normal": 2}
        schedule.sort(key=lambda s: (urgency_order.get(s.urgency, 2), -s.days_overdue))

        return schedule

    # ===== 辅助方法 =====

    def _add_activity(self, user_id: str, description: str, activity_type: str, db=None) -> None:
        """记录学习活动 - 写入MySQL"""
        from app.core.database import SessionLocal

        if db is None:
            db = SessionLocal()

        try:
            from app.models.profile import LearningActivityModel
            model = LearningActivityModel(
                user_id=user_id,
                description=description,
                activity_type=activity_type,
            )
            db.add(model)
            db.commit()
        except Exception as e:
            logger.warning("MySQL活动记录写入失败: %s", e)
            db.rollback()

    def _get_recent_activities(self, user_id: str, limit: int = 10) -> list[dict]:
        """从MySQL获取近期活动"""
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            from app.models.profile import LearningActivityModel
            models = db.query(LearningActivityModel).filter(
                LearningActivityModel.user_id == user_id,
            ).order_by(LearningActivityModel.created_at.desc()).limit(limit).all()

            return [
                {
                    "description": m.description,
                    "type": m.activity_type,
                    "timestamp": m.created_at.isoformat() if m.created_at else "",
                }
                for m in models
            ]
        except Exception as e:
            logger.warning("MySQL活动记录查询失败: %s", e)
            return []
        finally:
            db.close()


# 全局单例
innovation_service = InnovationService()
