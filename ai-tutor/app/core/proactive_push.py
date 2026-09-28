"""主动推送系统 — 在关键节点主动推进学习流程

5条推送规则：
1. after_document_generated — 学完文档→建议做题
2. after_quiz_all_correct — 全对→推荐下一步
3. user_return_after_3_days — 3天未登录→遗忘衰减+复习建议
4. path_phase_completed — 阶段完成→评估
5. video_ready — 视频生成完成→通知

推送作为Orchestrator的follow_up阶段执行，不是定时任务，不是前端轮询
"""

from typing import Optional, Dict, List
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class PushMessage:
    """推送消息"""
    text: str                          # 推送文本
    quick_action: Optional[str] = None # 快捷动作标识（前端显示按钮）
    quick_action_label: Optional[str] = None  # 按钮文字
    trigger: str = ""                  # 触发条件


class ProactivePushSystem:
    """主动推送系统"""

    def check_and_push(self, trigger: str, context: Dict = None) -> Optional[PushMessage]:
        """检查触发条件并返回推送消息

        Args:
            trigger: 触发条件
            context: 上下文信息（user_id, knowledge_point, agent_result等）

        Returns:
            PushMessage or None
        """
        context = context or {}

        if trigger == "after_document_generated":
            kp = context.get("knowledge_point", "这个知识点")
            return PushMessage(
                text=f"关于{kp}的讲解文档已生成。这个概念你理解了吗？要不要做几道题检验一下？",
                quick_action="start_practice",
                quick_action_label="做几道题",
                trigger=trigger
            )

        if trigger == "after_quiz_all_correct":
            kp = context.get("knowledge_point", "")
            next_topic = context.get("next_topic", "下一个知识点")
            return PushMessage(
                text=f"全对！你已经掌握了{kp}。下一步推荐学习{next_topic}。",
                quick_action="learn_next",
                quick_action_label=f"学习{next_topic}",
                trigger=trigger
            )

        if trigger == "after_quiz_partial":
            kp = context.get("knowledge_point", "")
            wrong_count = context.get("wrong_count", 0)
            return PushMessage(
                text=f"有{wrong_count}道题答错了，{kp}还需要多练习。要我再讲解一下吗？",
                quick_action="relearn",
                quick_action_label="重新学习",
                trigger=trigger
            )

        if trigger == "user_return_after_3_days":
            days_gone = context.get("days_gone", 0)
            last_topic = context.get("last_topic", "之前的内容")
            return PushMessage(
                text=f"欢迎回来！你{days_gone}天前学到了{last_topic}，根据遗忘曲线可能需要复习一下。",
                quick_action="review",
                quick_action_label="开始复习",
                trigger=trigger
            )

        if trigger == "path_phase_completed":
            phase_name = context.get("phase_name", "这个阶段")
            return PushMessage(
                text=f"{phase_name}完成了！要不要看看你的学习效果评估？",
                quick_action="assess",
                quick_action_label="查看评估",
                trigger=trigger
            )

        if trigger == "video_ready":
            kp = context.get("knowledge_point", "")
            return PushMessage(
                text=f"🎬 {kp}的讲解视频已生成，点击查看",
                quick_action="watch_video",
                quick_action_label="观看视频",
                trigger=trigger
            )

        if trigger == "after_cold_start_completed":
            return PushMessage(
                text="画像采集完成！要我帮你规划学习路径吗？",
                quick_action="plan_path",
                quick_action_label="规划路径",
                trigger=trigger
            )

        return None


# 全局单例
proactive_push = ProactivePushSystem()
