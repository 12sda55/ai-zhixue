"""定时任务调度器 - 遗忘曲线衰减 + 定期画像审视

对照 ai_architecture_plan.md Phase 1.4：
- 遗忘曲线定时任务：每天检查7天未复习的知识点，衰减5%
- 定期画像审视：每5轮对话，LLM审视画像合理性
"""

from __future__ import annotations
import asyncio
import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.core.database import SessionLocal
from app.services.profile_service import profile_service
from app.core.llm import llm_client
from app.core.config import get_settings
from app.schemas.profile import StudentProfile

logger = logging.getLogger(__name__)
settings = get_settings()

# ===== 画像审视Prompt =====

PROFILE_REVIEW_PROMPT = """你是一个教育画像分析专家。请审视以下学生画像，判断是否需要调整。

审视规则：
1. 如果学生自述已掌握但mastery低于0.5，说明可能低估，建议提升
2. 如果学生多次犯错但不在薄弱环节中，建议加入
3. 如果学习节奏和实际行为不匹配（如自述稳步型但频繁试错），建议调整
4. 如果难度偏好和实际表现不匹配，建议调整

学生画像：
{profile_json}

请输出JSON格式：
{{
    "needs_adjustment": true/false,
    "adjustments": [
        {{
            "dimension": "维度名",
            "field": "字段名",
            "suggested_value": "建议值",
            "reason": "原因"
        }}
    ],
    "summary": "审视总结"
}}

如果画像合理不需要调整，输出：
{{"needs_adjustment": false, "adjustments": [], "summary": "画像当前合理"}}"""


class SchedulerService:
    """定时任务调度器"""

    def __init__(self):
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._redis_client = None

    def _get_redis(self):
        """懒加载Redis客户端"""
        if self._redis_client is None:
            try:
                import redis
                self._redis_client = redis.from_url(settings.redis_url, decode_responses=True)
                self._redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis连接失败: {e}")
                self._redis_client = None
        return self._redis_client

    def start(self) -> None:
        """启动定时任务调度器"""
        if self._scheduler is not None:
            return

        self._scheduler = AsyncIOScheduler()

        # 遗忘曲线衰减：每天凌晨3点执行
        self._scheduler.add_job(
            self._run_forgetting_decay,
            CronTrigger(hour=3, minute=0),
            id="forgetting_decay",
            name="遗忘曲线衰减检查",
            replace_existing=True,
        )

        # 画像审视：每6小时执行一次（检查是否有用户达到5轮对话阈值）
        self._scheduler.add_job(
            self._run_profile_review,
            IntervalTrigger(hours=6),
            id="profile_review",
            name="定期画像审视",
            replace_existing=True,
        )

        self._scheduler.start()
        logger.info("定时任务调度器已启动")

    def stop(self) -> None:
        """停止定时任务调度器"""
        if self._scheduler:
            self._scheduler.shutdown()
            self._scheduler = None
            logger.info("定时任务调度器已停止")

    # ===== 遗忘曲线衰减 =====

    async def _run_forgetting_decay(self) -> None:
        """执行遗忘曲线衰减检查（定时任务）"""
        logger.info("开始执行遗忘曲线衰减检查...")
        try:
            db = SessionLocal()
            try:
                changes = profile_service.check_all_forgetting_decay(db)
                logger.info(f"遗忘曲线衰减完成，共{len(changes)}处变更")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"遗忘曲线衰减任务失败: {e}")

    # ===== 定期画像审视 =====

    async def _run_profile_review(self) -> None:
        """执行定期画像审视（每5轮对话触发LLM审视）"""
        logger.info("开始执行定期画像审视...")
        try:
            db = SessionLocal()
            try:
                from app.models.profile import ProfileModel
                records = db.query(ProfileModel).all()
                reviewed_count = 0

                for record in records:
                    # 每5轮对话审视一次
                    if record.conversation_count > 0 and record.conversation_count % 5 == 0:
                        profile = profile_service.get_profile(db, record.user_id)
                        if profile is None:
                            continue

                        # 用Redis记录上次审视的轮次，避免重复审视
                        last_reviewed_at_count = 0
                        redis_client = self._get_redis()
                        if redis_client is not None:
                            try:
                                key = f"profile_review_last_count:{record.user_id}"
                                val = redis_client.get(key)
                                if val:
                                    last_reviewed_at_count = int(val)
                            except Exception:
                                pass

                        if record.conversation_count > last_reviewed_at_count:
                            await self._review_single_profile(db, profile)
                            reviewed_count += 1

                            # 记录本次审视的轮次
                            if redis_client is not None:
                                try:
                                    key = f"profile_review_last_count:{record.user_id}"
                                    redis_client.set(key, str(record.conversation_count))
                                except Exception:
                                    pass

                logger.info(f"画像审视完成，共审视{reviewed_count}个用户")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"画像审视任务失败: {e}")

    async def _review_single_profile(self, db, profile: StudentProfile) -> None:
        """用LLM审视单个用户画像，若需调整则更新数据库"""
        try:
            profile_json = profile.model_dump_json()
            prompt = PROFILE_REVIEW_PROMPT.format(profile_json=profile_json)

            response = llm_client.chat(
                messages=[
                    {"role": "system", "content": "你是教育画像分析专家，只输出JSON格式。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            import json
            result = json.loads(response)

            if result.get("needs_adjustment") and result.get("adjustments"):
                # 解析调整项并应用到画像
                updated_fields = []
                for adj in result["adjustments"]:
                    field = adj.get("field", "")
                    suggested_value = adj.get("suggested_value")
                    reason = adj.get("reason", "")

                    if field == "cognitive_style" and suggested_value:
                        try:
                            from app.schemas.profile import CognitiveStyle
                            profile.cognitive_style = CognitiveStyle(suggested_value)
                            updated_fields.append(f"cognitive_style→{suggested_value}")
                        except ValueError:
                            logger.warning(f"画像审视跳过无效值: cognitive_style={suggested_value}")

                    elif field == "learning_pace" and suggested_value:
                        try:
                            from app.schemas.profile import LearningPace
                            profile.learning_pace = LearningPace(suggested_value)
                            updated_fields.append(f"learning_pace→{suggested_value}")
                        except ValueError:
                            logger.warning(f"画像审视跳过无效值: learning_pace={suggested_value}")

                    elif field == "weak_points" and suggested_value:
                        if isinstance(suggested_value, str):
                            profile.add_weak_point(suggested_value, reason or "画像审视建议")
                            updated_fields.append(f"weak_points+{suggested_value}")
                        elif isinstance(suggested_value, list):
                            for wp in suggested_value:
                                wp_name = wp if isinstance(wp, str) else wp.get("knowledge_point", "")
                                if wp_name:
                                    profile.add_weak_point(wp_name, reason or "画像审视建议")
                            updated_fields.append(f"weak_points+{suggested_value}")

                    elif field == "learning_preference" and suggested_value:
                        try:
                            from app.schemas.profile import LearningPreference
                            profile.learning_preference = LearningPreference(suggested_value)
                            updated_fields.append(f"learning_preference→{suggested_value}")
                        except ValueError:
                            logger.warning(f"画像审视跳过无效值: learning_preference={suggested_value}")

                    elif field == "learning_goals" and suggested_value:
                        if isinstance(suggested_value, list):
                            profile.learning_goals = suggested_value
                            updated_fields.append(f"learning_goals→{suggested_value}")

                # 持久化更新到数据库
                if updated_fields:
                    profile_service.update_profile(db, profile, reason="画像审视自动更新")
                    logger.info(
                        f"画像审视已更新 user_id={profile.user_id}: "
                        f"{result.get('summary', '')}, "
                        f"更新字段={updated_fields}"
                    )
                else:
                    logger.info(
                        f"画像审视无需更新 user_id={profile.user_id}: "
                        f"{result.get('summary', '')}"
                    )
            else:
                logger.info(
                    f"画像审视结果 user_id={profile.user_id}: "
                    f"{result.get('summary', '画像当前合理')}"
                )

        except Exception as e:
            logger.error(f"画像审视失败 user_id={profile.user_id}: {e}")

    # ===== 手动触发接口 =====

    async def trigger_forgetting_decay(self) -> dict:
        """手动触发遗忘曲线衰减"""
        db = SessionLocal()
        try:
            changes = profile_service.check_all_forgetting_decay(db)
            return {"triggered": True, "changes_count": len(changes)}
        finally:
            db.close()

    async def trigger_profile_review(self, user_id: str) -> dict:
        """手动触发指定用户的画像审视"""
        db = SessionLocal()
        try:
            profile = profile_service.get_profile(db, user_id)
            if profile is None:
                return {"error": "用户画像不存在"}

            await self._review_single_profile(db, profile)
            return {"triggered": True, "user_id": user_id}
        finally:
            db.close()


# 全局单例
scheduler_service = SchedulerService()
