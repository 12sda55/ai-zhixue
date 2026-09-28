"""学习进度引擎 — 今日计划、用户回归欢迎、遗忘衰减应用"""

from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class TodayPlan:
    """今日学习计划"""
    new_topic: Optional[Dict] = None       # 下一个未完成节点
    review_topics: List[Dict] = None       # 遗忘曲线需复习的节点
    resources: Dict = None                 # 资源包
    has_path: bool = False                 # 是否有学习路径

    def __post_init__(self):
        if self.review_topics is None:
            self.review_topics = []
        if self.resources is None:
            self.resources = {}


@dataclass
class WelcomeMessage:
    """用户回归欢迎消息"""
    text: str
    last_topic: str = ""
    days_gone: int = 0
    needs_review: bool = False
    review_topics: List[str] = None

    def __post_init__(self):
        if self.review_topics is None:
            self.review_topics = []


class ProgressEngine:
    """学习进度引擎"""

    def get_today_plan(self, user_id: str) -> TodayPlan:
        """获取今日学习计划"""
        db = SessionLocal()
        try:
            from app.models.profile import (
                LearningPathModel, LearningPathNodeModel,
                ProfileKnowledgeMasteryModel
            )

            plan = TodayPlan()

            # 1. 查找活跃的学习路径
            active_path = db.query(LearningPathModel).filter(
                LearningPathModel.user_id == user_id,
                LearningPathModel.status == "active"
            ).first()

            if not active_path:
                return plan  # has_path=False

            plan.has_path = True

            # 2. 找下一个未完成节点
            next_node = db.query(LearningPathNodeModel).filter(
                LearningPathNodeModel.path_id == active_path.id,
                LearningPathNodeModel.status == "pending"
            ).order_by(LearningPathNodeModel.sort_order).first()

            if next_node:
                from app.core.knowledge_cache import knowledge_cache
                node_info = knowledge_cache.get_node(next_node.node_id)
                plan.new_topic = {
                    "node_id": next_node.node_id,
                    "name": node_info.get("name", next_node.node_id) if node_info else next_node.node_id,
                    "phase_name": next_node.phase_name,
                    "day_number": next_node.day_number,
                    "path_node_id": next_node.id
                }

            # 3. 找需要复习的节点（遗忘曲线）
            three_days_ago = datetime.now() - timedelta(days=3)
            weak_nodes = db.query(ProfileKnowledgeMasteryModel).filter(
                ProfileKnowledgeMasteryModel.user_id == user_id,
                ProfileKnowledgeMasteryModel.last_reviewed_at < three_days_ago,
                ProfileKnowledgeMasteryModel.mastery > 0.0
            ).all()

            for wn in weak_nodes:
                from app.core.knowledge_cache import knowledge_cache
                node_info = knowledge_cache.get_node(wn.node_id)
                plan.review_topics.append({
                    "node_id": wn.node_id,
                    "name": node_info.get("name", wn.node_id) if node_info else wn.node_id,
                    "mastery": wn.mastery,
                    "strength": wn.strength
                })

            return plan
        finally:
            db.close()

    def on_user_return(self, user_id: str) -> Optional[WelcomeMessage]:
        """用户回归欢迎消息"""
        db = SessionLocal()
        try:
            from app.models.profile import (
                ProfileModel, ProfileKnowledgeMasteryModel,
                LearningActivityModel
            )

            # 获取画像
            profile_model = db.query(ProfileModel).filter(
                ProfileModel.user_id == user_id
            ).first()

            if not profile_model:
                return None  # 新用户，不是回归

            # 获取上次学习时间
            last_activity = db.query(LearningActivityModel).filter(
                LearningActivityModel.user_id == user_id
            ).order_by(LearningActivityModel.created_at.desc()).first()

            if not last_activity:
                return None

            days_gone = (datetime.now() - last_activity.created_at).days

            # 获取最近学习的知识点
            import json
            profile = json.loads(profile_model.profile_json) if isinstance(profile_model.profile_json, str) else {}
            last_topic = ""
            knowledge_tree = profile.get("knowledge_tree", {})
            for kp, data in knowledge_tree.items():
                if data.get("last_learned"):
                    last_topic = kp

            msg = WelcomeMessage(
                text=f"欢迎回来！",
                last_topic=last_topic,
                days_gone=days_gone
            )

            # 3天以上需要复习
            if days_gone >= 3:
                msg.needs_review = True
                # 应用遗忘衰减
                decayed = self.apply_forgetting_decay(user_id)
                msg.review_topics = decayed
                msg.text = f"欢迎回来！你{days_gone}天前学到了{last_topic}，根据遗忘曲线可能需要复习一下。"
            else:
                msg.text = f"欢迎回来！上次你学到了{last_topic}，要继续吗？" if last_topic else "欢迎回来！"

            return msg
        finally:
            db.close()

    def apply_forgetting_decay(self, user_id: str) -> List[str]:
        """应用遗忘衰减

        对3天以上未复习的知识点，strength *= 0.95
        mastery随strength同步衰减

        Returns:
            List[str]: 衰减的知识点ID列表
        """
        db = SessionLocal()
        try:
            from app.models.profile import ProfileKnowledgeMasteryModel

            three_days_ago = datetime.now() - timedelta(days=3)

            # 找到需要衰减的记录
            stale_records = db.query(ProfileKnowledgeMasteryModel).filter(
                ProfileKnowledgeMasteryModel.user_id == user_id,
                ProfileKnowledgeMasteryModel.last_reviewed_at < three_days_ago,
                ProfileKnowledgeMasteryModel.strength > 0.1
            ).all()

            decayed = []
            for record in stale_records:
                old_strength = record.strength
                record.strength = max(0.1, old_strength * 0.95)
                # mastery随strength衰减
                record.mastery = min(record.mastery, record.strength)
                decayed.append(record.node_id)

            db.commit()

            if decayed:
                logger.info(f"Applied forgetting decay for user {user_id}: {len(decayed)} nodes")

            return decayed
        except Exception as e:
            db.rollback()
            logger.error(f"Forgetting decay failed: {e}")
            return []
        finally:
            db.close()


# 全局单例
progress_engine = ProgressEngine()
