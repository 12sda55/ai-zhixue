"""评估Agent - 对照规范 4.8

输入：用户画像 + 学习路径进度 + 历史答题记录
输出：结构化评估报告（掌握度趋势、薄弱点改善、目标差距）
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.llm import llm_client
from app.schemas.profile import StudentProfile
from app.schemas.knowledge_graph import get_knowledge_node, get_categories
from app.schemas.assessment import (
    AssessmentResult,
    LearningProgress,
    AssessmentWeakPoint,
    AdjustmentRecommendation
)
from app.models.profile import (
    ProfileSnapshotModel,
    AnswerRecordModel,
    ProfileKnowledgeMasteryModel,
    LearningPathNodeModel,
    LearningPathModel
)

logger = logging.getLogger(__name__)


class AssessmentService:
    """学习效果评估服务"""

    def generate_assessment(self, user_id: str, profile: Optional[StudentProfile] = None, db_session: Optional[Session] = None) -> dict:
        """生成学习效果评估报告

        Args:
            user_id: 用户ID
            profile: 学生画像
            db_session: 数据库会话

        Returns:
            {
                "user_id": str,
                "overall_score": float,  # 0-100
                "mastery_trend": list[dict],  # [{date, category, mastery}]
                "weak_points_improvement": list[dict],  # [{point, before, after, change}]
                "goal_gap_analysis": dict,  # {goal, current_progress, gap, recommendation}
                "recommendations": list[str],
                "kg_node_ids": list[str],
            }
        """
        # 1. 收集数据：画像快照 + 答题记录
        snapshots_data = self._get_snapshot_trends(db_session, user_id)
        answer_stats = self._get_answer_stats(db_session, user_id)
        weak_points_data = self._analyze_weak_points(profile, snapshots_data)

        # 2. 计算整体得分
        overall_score = self._calculate_overall_score(profile, answer_stats)

        # 3. 分析掌握度趋势
        mastery_trend = self._build_mastery_trend(snapshots_data)

        # 4. 薄弱点改善分析
        weak_points_improvement = weak_points_data

        # 5. 目标差距分析
        goal_gap = self._analyze_goal_gap(profile, overall_score)

        # 6. 生成推荐
        recommendations = self._generate_recommendations(profile, overall_score, weak_points_data, goal_gap)

        # 7. 收集关联知识点
        kg_node_ids = self._collect_kg_node_ids(profile)

        return {
            "user_id": user_id,
            "overall_score": overall_score,
            "mastery_trend": mastery_trend,
            "weak_points_improvement": weak_points_improvement,
            "goal_gap_analysis": goal_gap,
            "recommendations": recommendations,
            "kg_node_ids": kg_node_ids,
        }

    def _get_snapshot_trends(self, db: Optional[Session], user_id: str) -> list[dict]:
        """获取画像快照趋势数据"""
        if not db:
            return []
        try:
            records = (
                db.query(ProfileSnapshotModel)
                .filter(ProfileSnapshotModel.user_id == user_id)
                .order_by(ProfileSnapshotModel.created_at.desc())
                .limit(10)
                .all()
            )
            trends = []
            for r in records:
                try:
                    snap_profile = StudentProfile.model_validate_json(r.profile_json)
                    trends.append({
                        "date": r.created_at.strftime("%Y-%m-%d"),
                        "profile": snap_profile,
                        "reason": r.change_reason,
                    })
                except Exception:
                    continue
            return trends
        except Exception as e:
            logger.error(f"获取画像快照失败: {e}")
            return []

    def _get_answer_stats(self, db: Optional[Session], user_id: str) -> dict:
        """获取答题统计数据"""
        if not db:
            return {"total": 0, "correct": 0, "by_kp": {}}
        try:
            records = (
                db.query(AnswerRecordModel)
                .filter(AnswerRecordModel.user_id == user_id)
                .order_by(AnswerRecordModel.created_at.desc())
                .limit(100)
                .all()
            )
            total = len(records)
            correct = sum(1 for r in records if r.is_correct)
            by_kp: dict[str, dict] = {}
            for r in records:
                kp = r.knowledge_point
                if kp not in by_kp:
                    by_kp[kp] = {"total": 0, "correct": 0}
                by_kp[kp]["total"] += 1
                by_kp[kp]["correct"] += 1
            return {"total": total, "correct": correct, "by_kp": by_kp}
        except Exception as e:
            logger.error(f"获取答题统计失败: {e}")
            return {"total": 0, "correct": 0, "by_kp": {}}

    def _calculate_overall_score(self, profile: Optional[StudentProfile], answer_stats: dict) -> float:
        """计算整体得分（0-100）"""
        if not profile:
            return 0.0

        # 基于答题正确率
        accuracy = answer_stats["correct"] / answer_stats["total"] if answer_stats["total"] > 0 else 0.5

        # 基于画像中各知识点掌握度
        categories = get_categories()
        mastery_scores = []
        for cat, node_ids in categories.items():
            masteries = [profile.get_knowledge_mastery(nid) for nid in node_ids]
            avg = sum(masteries) / len(masteries) if masteries else 0
            mastery_scores.append(avg)

        avg_mastery = sum(mastery_scores) / len(mastery_scores) if mastery_scores else 0

        # 综合得分：掌握度占60%，正确率占40%
        score = avg_mastery * 60 + accuracy * 100 * 0.4
        return round(min(score, 100.0), 1)

    def _build_mastery_trend(self, snapshots_data: list[dict]) -> list[dict]:
        """构建掌握度趋势数据（用于前端雷达/趋势图）"""
        categories = get_categories()
        trend = []

        for snap in snapshots_data[:5]:  # 最近5个快照
            snap_profile = snap["profile"]
            date = snap["date"]
            for cat, node_ids in categories.items():
                masteries = [snap_profile.get_knowledge_mastery(nid) for nid in node_ids]
                avg = sum(masteries) / len(masteries) if masteries else 0
                trend.append({
                    "date": date,
                    "category": cat,
                    "mastery": round(avg, 3),
                })

        return trend

    def _analyze_weak_points(self, profile: Optional[StudentProfile], snapshots_data: list[dict]) -> list[dict]:
        """分析薄弱点改善情况"""
        if not profile or not profile.weak_points:
            return []

        improvements = []
        current_weak = {wp.knowledge_point: wp for wp in profile.weak_points}

        # 从快照中找历史薄弱点数据
        before_map: dict[str, float] = {}
        if len(snapshots_data) >= 2:
            oldest = snapshots_data[-1]["profile"]
            for wp in (oldest.weak_points or []):
                before_map[wp.knowledge_point] = oldest.get_knowledge_mastery(wp.knowledge_point)

        for kp, wp in current_weak.items():
            node_def = get_knowledge_node(kp)
            kp_name = node_def.name if node_def else kp
            current_mastery = profile.get_knowledge_mastery(kp)
            before_mastery = before_map.get(kp, current_mastery)
            change = round(current_mastery - before_mastery, 3)
            improvements.append({
                "point": kp_name,
                "knowledge_point_id": kp,
                "before": round(before_mastery, 3),
                "after": round(current_mastery, 3),
                "change": change,
            })

        return improvements

    def _analyze_goal_gap(self, profile: Optional[StudentProfile], overall_score: float) -> dict:
        """分析目标差距"""
        if not profile or not profile.learning_goals:
            return {
                "goal": "暂无学习目标",
                "current_progress": overall_score,
                "gap": 0,
                "recommendation": "建议先设定学习目标",
            }

        goal = ", ".join(profile.learning_goals)
        # 目标进度：基于整体得分估算
        target_score = 80.0  # 默认目标为80分
        gap = max(0, round(target_score - overall_score, 1))

        # 根据画像阶段调整目标
        stage = profile.stage.value if profile.stage else ""
        if stage in ("exam_prep", "advanced"):
            target_score = 90.0
            gap = max(0, round(target_score - overall_score, 1))

        recommendation = ""
        if gap > 30:
            recommendation = "距离目标差距较大，建议重点攻克薄弱环节，配合练习题巩固基础。"
        elif gap > 15:
            recommendation = "有一定差距，建议针对性练习薄弱知识点，逐步提升掌握度。"
        elif gap > 0:
            recommendation = "接近目标，保持当前学习节奏，注意查漏补缺。"
        else:
            recommendation = "已达到目标水平，可以挑战更高难度的内容。"

        return {
            "goal": goal,
            "current_progress": overall_score,
            "target_score": target_score,
            "gap": gap,
            "recommendation": recommendation,
        }

    def _generate_recommendations(
        self,
        profile: Optional[StudentProfile],
        overall_score: float,
        weak_points_data: list[dict],
        goal_gap: dict,
    ) -> list[str]:
        """生成学习建议"""
        recommendations = []

        if not profile:
            return ["建议先完成画像初始化，以便获得个性化评估。"]

        # 基于薄弱点
        worsening = [wp for wp in weak_points_data if wp["change"] < 0]
        if worsening:
            points = ", ".join(wp["point"] for wp in worsening[:3])
            recommendations.append(f"以下知识点掌握度下降，需要重点复习：{points}")

        improving = [wp for wp in weak_points_data if wp["change"] > 0]
        if improving:
            points = ", ".join(wp["point"] for wp in improving[:3])
            recommendations.append(f"以下知识点有进步，继续保持：{points}")

        # 基于整体得分
        if overall_score < 40:
            recommendations.append("整体掌握度较低，建议从基础知识点开始系统学习。")
        elif overall_score < 60:
            recommendations.append("基础已有一定积累，建议针对薄弱环节加强练习。")
        elif overall_score < 80:
            recommendations.append("掌握度良好，可以尝试更高难度的题目和进阶内容。")

        # 基于目标差距
        if goal_gap.get("gap", 0) > 15:
            recommendations.append(goal_gap.get("recommendation", ""))

        # 用LLM生成个性化建议
        if profile and recommendations:
            try:
                llm_recs = self._llm_generate_recommendations(profile, overall_score, weak_points_data, goal_gap)
                if llm_recs:
                    recommendations.extend(llm_recs)
            except Exception as e:
                logger.warning(f"LLM生成建议失败，使用规则建议: {e}")

        return recommendations[:8]  # 最多8条

    def _llm_generate_recommendations(
        self,
        profile: StudentProfile,
        overall_score: float,
        weak_points_data: list[dict],
        goal_gap: dict,
    ) -> list[str]:
        """用LLM生成个性化学习建议"""
        weak_summary = "\n".join(
            f"- {wp['point']}: 从{wp['before']}提升到{wp['after']}（变化{wp['change']:+.3f}）"
            for wp in weak_points_data[:5]
        )

        prompt = f"""基于以下学生学习数据，生成3条个性化学习建议（每条不超过50字）。

学生画像：
- 专业：{profile.major.value}
- 阶段：{profile.stage.value}
- 认知风格：{profile.cognitive_style.value}
- 学习目标：{', '.join(profile.learning_goals or [])}

整体得分：{overall_score}/100
目标差距：{goal_gap.get('gap', 0)}分

薄弱点变化：
{weak_summary}

请返回JSON格式：
{{"recommendations": ["建议1", "建议2", "建议3"]}}"""

        result_text = llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        result = json.loads(result_text.strip())
        return result.get("recommendations", [])

    def _collect_kg_node_ids(self, profile: Optional[StudentProfile]) -> list[str]:
        """收集关联的知识图谱节点ID"""
        if not profile:
            return []

        node_ids = []
        if profile.weak_points:
            node_ids.extend(wp.knowledge_point for wp in profile.weak_points)
        return list(set(node_ids))

    def generate_assessment_result(
        self,
        user_id: str,
        profile: Optional[StudentProfile] = None,
        db_session: Optional[Session] = None
    ) -> AssessmentResult:
        """生成完整的评估结果（AssessmentResult对象）

        包含：
        - 学习时长统计
        - 学习效率评估
        - 各知识点学习进度
        - 薄弱点识别
        - 路径动态调整建议
        """
        # 1. 收集基础数据
        snapshots_data = self._get_snapshot_trends(db_session, user_id)
        answer_stats = self._get_answer_stats(db_session, user_id)

        # 2. 计算学习时长和效率（新增）
        total_learning_duration = self._calculate_total_learning_duration(db_session, user_id)
        learning_efficiency = self._calculate_learning_efficiency(
            db_session, user_id, total_learning_duration
        )

        # 3. 生成各知识点学习进度（新增）
        learning_progress_list = self._build_learning_progress_list(
            db_session, user_id, profile, answer_stats
        )

        # 4. 薄弱点识别（增强）
        weak_points_list = self._identify_weak_points_enhanced(
            db_session, user_id, profile, answer_stats
        )

        # 5. 路径动态调整建议（新增）
        adjustment_recommendations = self._generate_path_adjustments(
            db_session, user_id, profile, weak_points_list
        )

        # 6. 计算整体掌握度
        overall_score = self._calculate_overall_score(profile, answer_stats)

        # 7. 生成评估报告摘要
        assessment_summary = self._generate_assessment_summary(
            overall_score, learning_efficiency, weak_points_list, adjustment_recommendations
        )

        return AssessmentResult(
            user_id=user_id,
            assessment_time=datetime.now(),
            overall_mastery=overall_score,
            learning_efficiency=learning_efficiency,
            total_learning_duration=total_learning_duration,
            learning_progress=learning_progress_list,
            weak_points=weak_points_list,
            adjustment_recommendations=adjustment_recommendations,
            assessment_summary=assessment_summary,
            assessment_detail={
                "answer_stats": answer_stats,
                "snapshots_count": len(snapshots_data),
            }
        )

    def _calculate_total_learning_duration(
        self, db: Optional[Session], user_id: str
    ) -> float:
        """计算总学习时长（分钟）

        数据来源：ProfileKnowledgeMasteryModel.times_learned * 每次平均时长
        """
        if not db:
            return 0.0

        try:
            # 统计所有知识点的学习次数总和
            total_times_learned = (
                db.query(func.sum(ProfileKnowledgeMasteryModel.times_learned))
                .filter(ProfileKnowledgeMasteryModel.user_id == user_id)
                .scalar() or 0
            )

            # 假设每次学习平均30分钟（可根据实际数据调整）
            avg_duration_per_session = 30.0
            total_duration = total_times_learned * avg_duration_per_session

            return round(total_duration, 1)
        except Exception as e:
            logger.error(f"计算学习时长失败: {e}")
            return 0.0

    def _calculate_learning_efficiency(
        self, db: Optional[Session], user_id: str, total_duration: float
    ) -> float:
        """计算学习效率（分/小时）

        计算公式：掌握度增量 / 学习时长（小时）
        """
        if total_duration == 0:
            return 0.0

        try:
            # 获取最近两个画像快照，计算掌握度增量
            if not db:
                return 1.5  # 默认值

            recent_snapshots = (
                db.query(ProfileSnapshotModel)
                .filter(ProfileSnapshotModel.user_id == user_id)
                .order_by(ProfileSnapshotModel.created_at.desc())
                .limit(2)
                .all()
            )

            if len(recent_snapshots) < 2:
                return 1.5  # 数据不足，返回默认值

            # 计算掌握度增量
            try:
                latest_profile = StudentProfile.model_validate_json(recent_snapshots[0].profile_json)
                earlier_profile = StudentProfile.model_validate_json(recent_snapshots[1].profile_json)

                categories = get_categories()
                latest_mastery_sum = 0.0
                earlier_mastery_sum = 0.0

                for cat, node_ids in categories.items():
                    for nid in node_ids:
                        latest_mastery_sum += latest_profile.get_knowledge_mastery(nid)
                        earlier_mastery_sum += earlier_profile.get_knowledge_mastery(nid)

                mastery_increment = latest_mastery_sum - earlier_mastery_sum
                hours = total_duration / 60.0

                efficiency = mastery_increment / hours if hours > 0 else 0.0
                return round(max(0.0, min(efficiency, 5.0)), 2)  # 限制在0-5之间
            except Exception:
                return 1.5
        except Exception as e:
            logger.error(f"计算学习效率失败: {e}")
            return 1.5

    def _build_learning_progress_list(
        self, db: Optional[Session], user_id: str,
        profile: Optional[StudentProfile], answer_stats: dict
    ) -> List[LearningProgress]:
        """构建各知识点学习进度列表"""
        progress_list = []

        if not db or not profile:
            return progress_list

        try:
            # 获取所有知识点的掌握度数据
            mastery_records = (
                db.query(ProfileKnowledgeMasteryModel)
                .filter(ProfileKnowledgeMasteryModel.user_id == user_id)
                .all()
            )

            mastery_map = {r.node_id: r for r in mastery_records}

            # 遍历所有知识点
            categories = get_categories()
            for cat, node_ids in categories.items():
                for node_id in node_ids:
                    mastery_record = mastery_map.get(node_id)
                    node_def = get_knowledge_node(node_id)

                    # 计算答题正确率
                    kp_answer_stats = answer_stats.get("by_kp", {}).get(node_id, {})
                    correctness_rate = (
                        kp_answer_stats.get("correct", 0) / kp_answer_stats.get("total", 1) * 100
                        if kp_answer_stats.get("total", 0) > 0
                        else 0.0
                    )

                    # 计算学习时长
                    times_learned = mastery_record.times_learned if mastery_record else 0
                    learning_duration = times_learned * 30.0  # 每次30分钟

                    # 获取掌握度
                    mastery_level = profile.get_knowledge_mastery(node_id) * 100

                    progress_list.append(LearningProgress(
                        knowledge_point_id=node_id,
                        learning_duration=round(learning_duration, 1),
                        correctness_rate=round(correctness_rate, 1),
                        learning_frequency=times_learned,
                        resource_usage={},  # 可扩展
                        last_learning_time=mastery_record.last_learned_at if mastery_record else None,
                        mastery_level=round(mastery_level, 1)
                    ))
        except Exception as e:
            logger.error(f"构建学习进度列表失败: {e}")

        return progress_list

    def _identify_weak_points_enhanced(
        self, db: Optional[Session], user_id: str,
        profile: Optional[StudentProfile], answer_stats: dict
    ) -> List[AssessmentWeakPoint]:
        """增强的薄弱点识别

        根据正确率和掌握度综合识别薄弱点
        """
        weak_points_list = []

        if not profile:
            return weak_points_list

        try:
            categories = get_categories()
            for cat, node_ids in categories.items():
                for node_id in node_ids:
                    # 获取知识点名称
                    node_def = get_knowledge_node(node_id)
                    kp_name = node_def.name if node_def else node_id

                    # 获取正确率
                    kp_answer_stats = answer_stats.get("by_kp", {}).get(node_id, {})
                    correctness_rate = (
                        kp_answer_stats.get("correct", 0) / kp_answer_stats.get("total", 1) * 100
                        if kp_answer_stats.get("total", 0) > 0
                        else profile.get_knowledge_mastery(node_id) * 100
                    )

                    # 获取掌握度
                    mastery_level = profile.get_knowledge_mastery(node_id) * 100

                    # 综合评分：掌握度（越低越薄弱）
                    weakness_level = mastery_level

                    # 识别薄弱点（掌握度 < 60 或 正确率 < 60）
                    if mastery_level < 60 or correctness_rate < 60:
                        # 分类：严重薄弱点（<40）、薄弱点（40-50）、一般薄弱点（50-60）
                        if mastery_level < 40:
                            category = "严重薄弱点"
                        elif mastery_level < 50:
                            category = "薄弱点"
                        else:
                            category = "一般薄弱点"

                        # 建议补强时长（根据薄弱程度）
                        recommended_duration = (60 - mastery_level) * 2  # 每低于1分，增加2分钟

                        weak_points_list.append(AssessmentWeakPoint(
                            knowledge_point_id=node_id,
                            knowledge_point_name=kp_name,
                            weakness_level=round(weakness_level, 1),
                            correctness_rate=round(correctness_rate, 1),
                            weakness_category=category,
                            recommended_duration=round(recommended_duration, 1)
                        ))
        except Exception as e:
            logger.error(f"识别薄弱点失败: {e}")

        # 按薄弱程度排序（越薄弱排前面）
        weak_points_list.sort(key=lambda x: x.weakness_level)
        return weak_points_list[:10]  # 最多返回10个薄弱点

    def _generate_path_adjustments(
        self, db: Optional[Session], user_id: str,
        profile: Optional[StudentProfile], weak_points: List[AssessmentWeakPoint]
    ) -> List[AdjustmentRecommendation]:
        """生成路径动态调整建议

        根据薄弱点自动生成调整建议
        """
        recommendations = []

        if not weak_points:
            return recommendations

        try:
            # 获取当前学习路径
            if db:
                current_path = (
                    db.query(LearningPathModel)
                    .filter(
                        LearningPathModel.user_id == user_id,
                        LearningPathModel.status == "active"
                    )
                    .first()
                )

                if current_path:
                    # 检查路径是否包含薄弱点
                    path_nodes = (
                        db.query(LearningPathNodeModel)
                        .filter(LearningPathNodeModel.path_id == current_path.id)
                        .all()
                    )

                    path_node_ids = {n.node_id for n in path_nodes}

                    # 生成调整建议
                    for i, wp in enumerate(weak_points[:5]):  # 处理前5个薄弱点
                        if wp.knowledge_point_id not in path_node_ids:
                            # 薄弱点不在当前路径中，建议插入
                            recommendations.append(AdjustmentRecommendation(
                                adjustment_type="路径调整",
                                adjustment_content=f"插入薄弱点学习节点：{wp.knowledge_point_name}",
                                adjustment_reason=f"{wp.weakness_category}（掌握度{wp.weakness_level}分，正确率{wp.correctness_rate}%）",
                                adjustment_priority="高" if wp.weakness_level < 40 else "中",
                                adjusted_content={
                                    "node_id": wp.knowledge_point_id,
                                    "recommended_duration": wp.recommended_duration,
                                    "insert_position": i + 1
                                }
                            ))
                        else:
                            # 薄弱点已在路径中，建议增加时长
                            recommendations.append(AdjustmentRecommendation(
                                adjustment_type="时长调整",
                                adjustment_content=f"增加薄弱点学习时长：{wp.knowledge_point_name}",
                                adjustment_reason=f"{wp.weakness_category}，建议增加{wp.recommended_duration}分钟",
                                adjustment_priority="中",
                                adjusted_content={
                                    "node_id": wp.knowledge_point_id,
                                    "additional_duration": wp.recommended_duration
                                }
                            ))

            # 如果没有当前路径，生成新建路径建议
            if not recommendations and weak_points:
                recommendations.append(AdjustmentRecommendation(
                    adjustment_type="路径新建",
                    adjustment_content="生成针对性学习路径",
                    adjustment_reason=f"检测到{len(weak_points)}个薄弱点，需要新建学习路径",
                    adjustment_priority="高",
                    adjusted_content={
                        "weak_point_ids": [wp.knowledge_point_id for wp in weak_points[:5]]
                    }
                ))
        except Exception as e:
            logger.error(f"生成路径调整建议失败: {e}")

        return recommendations

    def _generate_assessment_summary(
        self, overall_mastery: float, learning_efficiency: float,
        weak_points: List[AssessmentWeakPoint], adjustments: List[AdjustmentRecommendation]
    ) -> str:
        """生成评估报告摘要"""
        summary_parts = []

        # 整体掌握度评价
        if overall_mastery >= 80:
            summary_parts.append(f"整体掌握度优秀（{overall_mastery}分），学习效果良好。")
        elif overall_mastery >= 60:
            summary_parts.append(f"整体掌握度良好（{overall_mastery}分），继续保持学习节奏。")
        elif overall_mastery >= 40:
            summary_parts.append(f"整体掌握度中等（{overall_mastery}分），建议加强薄弱环节。")
        else:
            summary_parts.append(f"整体掌握度较低（{overall_mastery}分），需要系统学习基础知识。")

        # 学习效率评价
        if learning_efficiency >= 2.0:
            summary_parts.append(f"学习效率高（{learning_efficiency}分/小时），学习方法有效。")
        elif learning_efficiency >= 1.0:
            summary_parts.append(f"学习效率正常（{learning_efficiency}分/小时）。")
        else:
            summary_parts.append(f"学习效率偏低（{learning_efficiency}分/小时），建议调整学习方法。")

        # 薄弱点情况
        if len(weak_points) > 0:
            serious_count = sum(1 for wp in weak_points if wp.weakness_category == "严重薄弱点")
            if serious_count > 0:
                summary_parts.append(f"检测到{serious_count}个严重薄弱点，需要重点补强。")
            else:
                summary_parts.append(f"检测到{len(weak_points)}个薄弱点，建议针对性学习。")
        else:
            summary_parts.append("未检测到明显薄弱点，知识点掌握均衡。")

        # 调整建议
        if len(adjustments) > 0:
            summary_parts.append(f"已生成{len(adjustments)}条学习路径调整建议。")

        return " ".join(summary_parts)

    def update_learning_progress(
        self, db: Session, user_id: str, knowledge_point_id: str,
        learning_duration_increment: float, answer_result: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> bool:
        """更新学习进度（用于学习过程跟踪）

        Args:
            db: 数据库会话
            user_id: 用户ID
            knowledge_point_id: 知识点ID
            learning_duration_increment: 学习时长增量（分钟）
            answer_result: 答题结果（"正确"/"错误"/None）
            resource_type: 资源类型

        Returns:
            是否成功更新
        """
        try:
            # 更新知识掌握度记录
            mastery_record = (
                db.query(ProfileKnowledgeMasteryModel)
                .filter(
                    ProfileKnowledgeMasteryModel.user_id == user_id,
                    ProfileKnowledgeMasteryModel.node_id == knowledge_point_id
                )
                .first()
            )

            if not mastery_record:
                # 创建新记录
                mastery_record = ProfileKnowledgeMasteryModel(
                    user_id=user_id,
                    node_id=knowledge_point_id,
                    mastery=0.0,
                    times_learned=0,
                    last_learned_at=datetime.now()
                )
                db.add(mastery_record)

            # 更新学习次数和时长
            mastery_record.times_learned += 1
            mastery_record.last_learned_at = datetime.now()

            # 如果答题正确，增加掌握度
            if answer_result == "正确":
                mastery_record.mastery = min(1.0, mastery_record.mastery + 0.05)

            db.commit()
            return True
        except Exception as e:
            logger.error(f"更新学习进度失败: {e}")
            db.rollback()
            return False


# 全局单例
assessment_service = AssessmentService()
