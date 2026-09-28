"""对话状态机 — 跟踪用户学习阶段，自动推进流程"""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    """对话阶段枚举"""
    COLD_START = "cold_start"      # 冷启动画像采集
    IDLE = "idle"                  # 空闲，等待用户指令
    LEARNING = "learning"          # 学习中（文档/视频）
    PRACTICING = "practicing"      # 练习中（做题）
    ASSESSING = "assessing"        # 评估中
    REVIEWING = "reviewing"        # 复习中


@dataclass
class SessionContext:
    """会话上下文"""
    state: SessionState = SessionState.COLD_START
    current_knowledge_point: str = ""
    current_path_id: str = ""
    current_path_node_id: str = ""
    last_agent: str = ""
    last_action: str = ""
    rounds_in_state: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SessionStateMachine:
    """对话状态机

    状态转换规则：
    cold_start → idle      (画像采集完成)
    idle → learning        (用户请求学习/系统推荐)
    idle → practicing      (用户请求做题)
    learning → practicing  (学完文档→建议做题)
    learning → idle        (用户不想做题)
    practicing → idle      (做完题)
    practicing → assessing (阶段完成→评估)
    assessing → idle       (评估完成)
    idle → reviewing       (遗忘曲线触发复习)
    reviewing → idle       (复习完成)
    """

    # 合法状态转换
    TRANSITIONS = {
        SessionState.COLD_START: [SessionState.IDLE],
        SessionState.IDLE: [SessionState.LEARNING, SessionState.PRACTICING, SessionState.REVIEWING],
        SessionState.LEARNING: [SessionState.PRACTICING, SessionState.IDLE],
        SessionState.PRACTICING: [SessionState.IDLE, SessionState.ASSESSING],
        SessionState.ASSESSING: [SessionState.IDLE],
        SessionState.REVIEWING: [SessionState.IDLE],
    }

    def __init__(self):
        self._sessions: Dict[str, SessionContext] = {}

    def get_session(self, user_id: str) -> SessionContext:
        """获取用户会话上下文"""
        if user_id not in self._sessions:
            self._sessions[user_id] = SessionContext()
        return self._sessions[user_id]

    def transition(self, user_id: str, new_state: SessionState, **kwargs) -> bool:
        """状态转换

        Args:
            user_id: 用户ID
            new_state: 目标状态
            **kwargs: 额外上下文（如knowledge_point, path_id等）

        Returns:
            bool: 转换是否合法
        """
        session = self.get_session(user_id)
        old_state = session.state

        # 检查转换合法性
        if new_state not in self.TRANSITIONS.get(old_state, []):
            logger.warning(f"Invalid transition: {old_state} → {new_state} for user {user_id}")
            return False

        # 执行转换
        session.state = new_state
        session.rounds_in_state = 0

        # 更新额外上下文
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

        logger.info(f"Session transition: {old_state} → {new_state} for user {user_id}")
        return True

    def determine_next_action(self, user_id: str, trigger: str = "", agent_result: Dict = None) -> Optional[str]:
        """根据当前状态和触发条件，决定下一步行动

        Args:
            user_id: 用户ID
            trigger: 触发条件（如 "after_document_generated", "after_quiz_all_correct"）
            agent_result: Agent执行结果

        Returns:
            Optional[str]: 建议的下一步行动描述，None表示不需要主动推进
        """
        session = self.get_session(user_id)

        if trigger == "after_cold_start_completed":
            self.transition(user_id, SessionState.IDLE)
            return "画像采集完成！要我帮你规划学习路径吗？"

        if trigger == "after_document_generated":
            self.transition(user_id, SessionState.LEARNING,
                          current_knowledge_point=agent_result.get("knowledge_point", "") if agent_result else "")
            return "这个概念你理解了吗？要不要做几道题检验一下？"

        if trigger == "after_quiz_all_correct":
            self.transition(user_id, SessionState.IDLE)
            return "全对！你已经掌握了这个知识点。下一步推荐继续学习。"

        if trigger == "after_quiz_completed":
            self.transition(user_id, SessionState.IDLE)
            return None  # 做完题了，不主动推进

        if trigger == "path_phase_completed":
            self.transition(user_id, SessionState.ASSESSING)
            return "这个阶段完成了！要不要看看你的学习效果评估？"

        if trigger == "user_return_after_3_days":
            self.transition(user_id, SessionState.REVIEWING)
            return "欢迎回来！根据遗忘曲线，你可能需要复习一下之前学的内容。"

        return None

    def increment_round(self, user_id: str):
        """增加当前状态的轮次计数"""
        session = self.get_session(user_id)
        session.rounds_in_state += 1

    def save_to_redis(self, user_id: str):
        """持久化会话状态到Redis"""
        try:
            import redis, json
            from app.core.config import get_settings
            settings = get_settings()
            r = redis.from_url(settings.redis_url)
            session = self.get_session(user_id)
            data = {
                "state": session.state.value,
                "current_knowledge_point": session.current_knowledge_point,
                "current_path_id": session.current_path_id,
                "current_path_node_id": session.current_path_node_id,
                "last_agent": session.last_agent,
                "last_action": session.last_action,
                "rounds_in_state": str(session.rounds_in_state),
                "metadata": json.dumps(session.metadata or {}, ensure_ascii=False),
            }
            r.hset(f"session:{user_id}", mapping=data)
            r.expire(f"session:{user_id}", 48 * 3600)  # 48小时TTL
        except Exception as e:
            logger.debug(f"Redis save failed: {e}")

    def load_from_redis(self, user_id: str):
        """从Redis加载会话状态"""
        try:
            import redis, json
            from app.core.config import get_settings
            settings = get_settings()
            r = redis.from_url(settings.redis_url)
            data = r.hgetall(f"session:{user_id}")
            if data:
                session = self.get_session(user_id)
                session.state = SessionState(data.get(b"state", b"cold_start").decode())
                session.current_knowledge_point = data.get(b"current_knowledge_point", b"").decode()
                session.current_path_id = data.get(b"current_path_id", b"").decode()
                session.current_path_node_id = data.get(b"current_path_node_id", b"").decode()
                session.last_agent = data.get(b"last_agent", b"").decode()
                session.last_action = data.get(b"last_action", b"").decode()
                session.rounds_in_state = int(data.get(b"rounds_in_state", b"0"))
                # 恢复metadata
                meta_raw = data.get(b"metadata", b"{}").decode()
                try:
                    session.metadata = json.loads(meta_raw) if meta_raw else {}
                except json.JSONDecodeError:
                    session.metadata = {}
        except Exception as e:
            logger.debug(f"Redis load failed: {e}")


# 全局单例
session_state_machine = SessionStateMachine()
