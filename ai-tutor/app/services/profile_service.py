"""画像服务层 - CRUD + 规则引擎 + 快照 + Redis广播

对照 ai_architecture_plan.md：
- 9维度画像存储
- 11条P0规则引擎
- 事件驱动更新
- 画像快照
- Redis变更广播
"""

from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import Optional

import redis
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.profile import ProfileModel, ProfileSnapshotModel, ConversationModel
from app.schemas.profile import StudentProfile, ProfileChangeEvent, DifficultyLevel
from app.rules.profile_rules import ProfileRuleEngine, LearningEvent, EventType

logger = logging.getLogger(__name__)
settings = get_settings()


class ProfileService:
    """画像服务 - 统一管理画像的读写、更新、广播"""

    def __init__(self):
        self.rule_engine = ProfileRuleEngine()
        self._redis_client: Optional[redis.Redis] = None

    @property
    def redis_client(self) -> redis.Redis:
        """懒加载Redis连接"""
        if self._redis_client is None:
            try:
                self._redis_client = redis.from_url(settings.redis_url, decode_responses=True)
                self._redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis连接失败，画像变更广播不可用: {e}")
                self._redis_client = None
        return self._redis_client

    # ===== CRUD =====

    def get_profile(self, db: Session, user_id: str) -> Optional[StudentProfile]:
        """获取画像"""
        record = db.query(ProfileModel).filter(ProfileModel.user_id == user_id).first()
        if record is None:
            return None
        profile = StudentProfile.model_validate_json(record.profile_json)
        profile.conversation_count = record.conversation_count
        return profile

    def list_profiles(self, db: Session, exclude_user_id: str = "", limit: int = 50) -> list[StudentProfile]:
        """获取画像列表（用于伙伴匹配等）"""
        query = db.query(ProfileModel)
        if exclude_user_id:
            query = query.filter(ProfileModel.user_id != exclude_user_id)
        records = query.limit(limit).all()
        profiles = []
        for record in records:
            try:
                profile = StudentProfile.model_validate_json(record.profile_json)
                profile.conversation_count = record.conversation_count
                profiles.append(profile)
            except Exception:
                continue
        return profiles

    def create_profile(self, db: Session, profile: StudentProfile) -> StudentProfile:
        """创建画像"""
        now = datetime.now()
        record = ProfileModel(
            user_id=profile.user_id,
            profile_json=profile.model_dump_json(),
            conversation_count=profile.conversation_count,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        # 保存初始快照
        self._save_snapshot(db, profile.user_id, profile, "初始画像创建")
        return profile

    def update_profile(self, db: Session, profile: StudentProfile, reason: str = "") -> None:
        """更新画像"""
        record = db.query(ProfileModel).filter(ProfileModel.user_id == profile.user_id).first()
        if record is None:
            # 不存在则创建
            self.create_profile(db, profile)
            return

        record.profile_json = profile.model_dump_json()
        record.conversation_count = profile.conversation_count
        record.updated_at = datetime.now()
        db.commit()

        # 保存快照
        self._save_snapshot(db, profile.user_id, profile, reason)

    def delete_profile(self, db: Session, user_id: str) -> bool:
        """删除画像"""
        record = db.query(ProfileModel).filter(ProfileModel.user_id == user_id).first()
        if record:
            db.delete(record)
            db.commit()
            return True
        return False

    def get_or_create_profile(self, db: Session, user_id: str) -> StudentProfile:
        """获取或创建画像"""
        profile = self.get_profile(db, user_id)
        if profile is None:
            profile = StudentProfile(user_id=user_id)
            self.create_profile(db, profile)
        return profile

    # ===== 快照 =====

    def _save_snapshot(self, db: Session, user_id: str, profile: StudentProfile, reason: str) -> None:
        """保存画像快照"""
        snapshot = ProfileSnapshotModel(
            user_id=user_id,
            profile_json=profile.model_dump_json(),
            change_reason=reason[:256],
        )
        db.add(snapshot)
        db.commit()

    def get_snapshots(self, db: Session, user_id: str, limit: int = 20) -> list[dict]:
        """获取画像快照列表（学习成长轨迹）"""
        records = (
            db.query(ProfileSnapshotModel)
            .filter(ProfileSnapshotModel.user_id == user_id)
            .order_by(ProfileSnapshotModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "profile": StudentProfile.model_validate_json(r.profile_json),
                "reason": r.change_reason,
                "created_at": r.created_at,
            }
            for r in records
        ]

    # ===== 事件处理 =====

    def process_event(self, db: Session, event: LearningEvent) -> list[ProfileChangeEvent]:
        """处理学习事件：规则引擎 → 更新画像 → 广播变更"""
        profile = self.get_or_create_profile(db, event.user_id)
        changes = self.rule_engine.process_event(event, profile)

        if changes:
            # 更新画像到数据库
            reason = "; ".join(c.reason for c in changes)
            self.update_profile(db, profile, reason)

            # 广播变更
            self._broadcast_changes(event.user_id, changes)

        return changes

    def batch_process_events(self, db: Session, events: list[LearningEvent]) -> list[ProfileChangeEvent]:
        """批量处理事件（防抖动：同一维度多次变更合并）"""
        if not events:
            return []

        # 按user_id分组
        user_events: dict[str, list[LearningEvent]] = {}
        for event in events:
            user_events.setdefault(event.user_id, []).append(event)

        all_changes = []
        for user_id, user_event_list in user_events.items():
            profile = self.get_or_create_profile(db, user_id)
            # 按优先级排序处理（自述 > 行为 > 隐式推断）
            changes = self.rule_engine.process_events_sorted(user_event_list, profile)

            if changes:
                # 合并同一维度的变更（防抖动：取最终值）
                merged = self._merge_changes(changes)
                reason = "; ".join(c.reason for c in merged)
                self.update_profile(db, profile, reason)
                self._broadcast_changes(user_id, merged)
                all_changes.extend(merged)

        return all_changes

    # ===== Redis广播 =====

    PROFILE_CHANGE_CHANNEL = "profile_changes"
    # 用户级频道格式：profile_changes:{user_id}
    USER_CHANNEL_PREFIX = "profile_changes:"

    def _broadcast_changes(self, user_id: str, changes: list[ProfileChangeEvent]) -> None:
        """通过Redis发布画像变更事件（全局频道 + 用户级频道 + 历史记录）"""
        if self.redis_client is None:
            return

        history_key = f"profile_changes_history:{user_id}"
        for change in changes:
            try:
                message = json.dumps({
                    "user_id": user_id,
                    "dimension": change.dimension,
                    "field": change.field,
                    "old_value": change.old_value,
                    "new_value": change.new_value,
                    "reason": change.reason,
                    "timestamp": change.timestamp.isoformat(),
                }, ensure_ascii=False)
                # 全局频道
                self.redis_client.publish(self.PROFILE_CHANGE_CHANNEL, message)
                # 用户级频道（其他Agent可只订阅特定用户）
                user_channel = f"{self.USER_CHANNEL_PREFIX}{user_id}"
                self.redis_client.publish(user_channel, message)
                # 历史记录（保留最近100条）
                self.redis_client.lpush(history_key, message)
                self.redis_client.ltrim(history_key, 0, 99)
            except Exception as e:
                logger.error(f"Redis广播失败: {e}")

    def subscribe_changes(self, callback, user_id: Optional[str] = None):
        """订阅画像变更事件

        Args:
            callback: 回调函数，接收变更数据dict
            user_id: 可选，只订阅特定用户的变更。None则订阅全局
        """
        if self.redis_client is None:
            logger.warning("Redis不可用，无法订阅画像变更")
            return

        channel = f"{self.USER_CHANNEL_PREFIX}{user_id}" if user_id else self.PROFILE_CHANGE_CHANNEL
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(channel)
        for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                callback(data)

    def get_recent_changes(self, user_id: str, limit: int = 20) -> list[dict]:
        """获取用户最近的画像变更记录（从Redis List读取）

        Args:
            user_id: 用户ID
            limit: 返回条数

        Returns:
            变更记录列表
        """
        if self.redis_client is None:
            return []

        key = f"profile_changes_history:{user_id}"
        try:
            records = self.redis_client.lrange(key, 0, limit - 1)
            return [json.loads(r) for r in records]
        except Exception as e:
            logger.error(f"获取画像变更历史失败: {e}")
            return []

    # ===== 遗忘曲线 =====

    def check_all_forgetting_decay(self, db: Session) -> list[ProfileChangeEvent]:
        """检查所有用户的遗忘衰减（定时任务调用）"""
        all_profiles = db.query(ProfileModel).all()
        all_changes = []

        for record in all_profiles:
            profile = StudentProfile.model_validate_json(record.profile_json)
            profile.conversation_count = record.conversation_count
            changes = self.rule_engine.check_forgetting_decay(profile)
            if changes:
                reason = "遗忘曲线衰减"
                self.update_profile(db, profile, reason)
                self._broadcast_changes(profile.user_id, changes)
                all_changes.extend(changes)

        return all_changes

    # ===== 对话管理 =====

    def save_conversation(self, db: Session, user_id: str, conversation_id: str, role: str, content: str) -> None:
        """保存对话记录"""
        record = ConversationModel(
            user_id=user_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        db.add(record)
        db.commit()

    def get_conversations(self, db: Session, user_id: str, conversation_id: str, limit: int = 50) -> list[dict]:
        """获取对话历史"""
        records = (
            db.query(ConversationModel)
            .filter(
                ConversationModel.user_id == user_id,
                ConversationModel.conversation_id == conversation_id,
            )
            .order_by(ConversationModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {"role": r.role, "content": r.content, "created_at": r.created_at}
            for r in reversed(records)
        ]

    def increment_conversation_count(self, db: Session, user_id: str) -> int:
        """增加对话轮次（同时更新JSON中的conversation_count保持同步）"""
        record = db.query(ProfileModel).filter(ProfileModel.user_id == user_id).first()
        if record:
            record.conversation_count += 1
            # 同步更新JSON中的conversation_count
            profile = StudentProfile.model_validate_json(record.profile_json)
            profile.conversation_count = record.conversation_count
            record.profile_json = profile.model_dump_json()
            db.commit()
            return record.conversation_count
        return 0

    # ===== 工具方法 =====

    def _merge_changes(self, changes: list[ProfileChangeEvent]) -> list[ProfileChangeEvent]:
        """合并同一维度的变更（防抖动：取最终值）"""
        merged: dict[str, ProfileChangeEvent] = {}
        for change in changes:
            key = f"{change.dimension}.{change.field}"
            if key in merged:
                # 合并：保留最早的old_value和最新的new_value
                merged[key].new_value = change.new_value
                merged[key].reason = f"{merged[key].reason}; {change.reason}"
            else:
                merged[key] = change
        return list(merged.values())

    # ===== 维度更新方法 =====

    def update_learning_pace(self, db: Session, profile: StudentProfile, completion_data: dict) -> None:
        """根据路径阶段完成情况更新学习节奏

        Args:
            db: 数据库会话
            profile: 学生画像
            completion_data: 阶段完成数据，包含如:
                - phase_name: 阶段名称
                - time_spent_hours: 耗时（小时）
                - expected_hours: 预期耗时
                - error_rate: 错误率
                - hint_usage_rate: 提示使用率
        """
        try:
            from app.core.llm import llm_client

            prompt = f"""根据以下学习阶段完成数据，判断学生的学习节奏类型。

当前学习节奏: {profile.learning_pace.value}
阶段完成数据: {json.dumps(completion_data, ensure_ascii=False)}

学习节奏类型说明：
- trial_error（试错型）: 快速尝试、频繁试错、提示使用率高
- deep_think（深思型）: 耗时长、错误率低、提示使用率低
- steady（稳步型）: 按预期节奏推进、错误率和提示使用率适中

请只输出一个JSON：{{"learning_pace": "trial_error/deep_think/steady", "reason": "原因"}}"""

            response = llm_client.chat(
                messages=[
                    {"role": "system", "content": "你是教育数据分析专家，只输出JSON格式。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            result = json.loads(response)
            new_pace = result.get("learning_pace")

            if new_pace:
                from app.schemas.profile import LearningPace
                try:
                    old_pace = profile.learning_pace.value
                    profile.learning_pace = LearningPace(new_pace)
                    self.update_profile(db, profile, f"阶段完成分析更新学习节奏: {old_pace}→{new_pace}")
                    logger.info(f"学习节奏已更新 user_id={profile.user_id}: {old_pace}→{new_pace}, 原因: {result.get('reason', '')}")
                except ValueError:
                    logger.warning(f"学习节奏更新跳过无效值: {new_pace}")
        except Exception as e:
            logger.error(f"更新学习节奏失败 user_id={profile.user_id}: {e}")

    def update_learning_goals(self, db: Session, profile: StudentProfile, new_goals: list[str]) -> None:
        """更新学习目标

        Args:
            db: 数据库会话
            profile: 学生画像
            new_goals: 新的学习目标列表
        """
        profile.learning_goals = new_goals
        self.update_profile(db, profile, "用户更新学习目标")
        logger.info(f"学习目标已更新 user_id={profile.user_id}: {new_goals}")

    def update_difficulty_from_quiz(self, db: Session, profile: StudentProfile, accuracy: float) -> None:
        """根据答题正确率调整难度偏好

        规则：
        - 正确率 > 80% → 升级难度
        - 正确率 < 50% → 降低难度

        Args:
            db: 数据库会话
            profile: 学生画像
            accuracy: 答题正确率 (0.0 ~ 1.0)
        """
        old_level = profile.difficulty_level

        if accuracy > 0.8 and profile.difficulty_level != DifficultyLevel.ADVANCED:
            if profile.difficulty_level == DifficultyLevel.BASIC:
                profile.difficulty_level = DifficultyLevel.INTERMEDIATE
            elif profile.difficulty_level == DifficultyLevel.INTERMEDIATE:
                profile.difficulty_level = DifficultyLevel.ADVANCED
        elif accuracy < 0.5 and profile.difficulty_level != DifficultyLevel.BASIC:
            if profile.difficulty_level == DifficultyLevel.ADVANCED:
                profile.difficulty_level = DifficultyLevel.INTERMEDIATE
            elif profile.difficulty_level == DifficultyLevel.INTERMEDIATE:
                profile.difficulty_level = DifficultyLevel.BASIC

        if profile.difficulty_level != old_level:
            self.update_profile(db, profile, f"答题正确率{accuracy:.0%}调整难度: {old_level.value}→{profile.difficulty_level.value}")
            logger.info(
                f"难度偏好已调整 user_id={profile.user_id}: "
                f"{old_level.value}→{profile.difficulty_level.value} (正确率{accuracy:.0%})"
            )

    def update_major_stage(self, db: Session, profile: StudentProfile, major: str = None, stage: str = None) -> None:
        """更新专业/阶段（仅当用户明确请求时调用）

        Args:
            db: 数据库会话
            profile: 学生画像
            major: 新的专业，None表示不更新
            stage: 新的阶段，None表示不更新
        """
        from app.schemas.profile import Major, Stage

        if major is not None:
            try:
                profile.major = Major(major)
            except ValueError:
                logger.warning(f"专业更新跳过无效值: {major}")
                major = None

        if stage is not None:
            try:
                profile.stage = Stage(stage)
            except ValueError:
                logger.warning(f"阶段更新跳过无效值: {stage}")
                stage = None

        if major is not None or stage is not None:
            changes = []
            if major is not None:
                changes.append(f"专业→{major}")
            if stage is not None:
                changes.append(f"阶段→{stage}")
            self.update_profile(db, profile, f"用户更新专业/阶段: {', '.join(changes)}")
            logger.info(f"专业/阶段已更新 user_id={profile.user_id}: {', '.join(changes)}")


# 全局单例
profile_service = ProfileService()
