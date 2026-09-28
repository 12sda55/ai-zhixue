"""执行上下文 - 一次消息处理周期的共享上下文

对照 AI开发指南_产品内核与架构规范.md 第5.3节：
- Agent 不自己管理数据库连接
- 所有 Agent 共享同一个执行上下文
- 上下文包含：db_session, user_profile, learning_path, dialogue_history, generated_resources
- Agent 之间的数据传递通过上下文对象，不是通过函数返回值堆叠
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

from sqlalchemy.orm import Session

from app.schemas.profile import StudentProfile

logger = logging.getLogger(__name__)


@dataclass
class GeneratedResource:
    """生成的资源记录"""
    id: str
    type: str           # "path" | "document" | "question" | "code" | "video" | "mind_map" | "assessment" | "reading"
    content: dict       # 资源的具体内容
    kg_node_ids: list[str] = field(default_factory=list)  # 关联的知识图谱节点
    path_node_id: Optional[str] = None  # 关联的学习路径节点
    parent_resource_id: Optional[str] = None  # 父资源
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionContext:
    """一次消息处理周期的共享上下文

    所有Agent共享此上下文，不自己开DB连接。
    Agent之间的数据传递通过此上下文对象。
    """
    # 唯一的数据库会话
    db_session: Session

    # 用户信息
    user_id: str

    # 当前用户画像（内存对象，编排器加载后共享）
    profile: Optional[StudentProfile] = None

    # 当前学习路径（如果有）
    current_path: Optional[Any] = None  # LearningPath对象

    # 本次会话的对话历史
    dialogue_history: list[dict] = field(default_factory=list)

    # 本次生成的所有资源
    generated_resources: list[GeneratedResource] = field(default_factory=list)

    # Agent间传递的中间数据（Agent A的输出作为Agent B的输入）
    agent_outputs: dict[str, dict] = field(default_factory=dict)

    # 编排器决策信息
    execution_plan: Optional[dict] = None  # 编排器的执行计划
    response_strategy: str = "text_and_resources"  # 回复策略

    # 元信息
    created_at: datetime = field(default_factory=datetime.now)

    def add_resource(self, resource: GeneratedResource) -> None:
        """添加生成的资源"""
        self.generated_resources.append(resource)
        logger.info(f"资源已生成: type={resource.type}, id={resource.id}, kg_nodes={resource.kg_node_ids}")

    def get_agent_output(self, agent_name: str) -> Optional[dict]:
        """获取前序Agent的输出"""
        return self.agent_outputs.get(agent_name)

    def set_agent_output(self, agent_name: str, output: dict) -> None:
        """设置Agent的输出（供后续Agent使用）"""
        self.agent_outputs[agent_name] = output

    def get_current_path_node(self) -> Optional[str]:
        """获取当前学习路径中用户所在的节点"""
        if not self.current_path:
            return None
        # 从路径中找到当前正在学习的节点
        # ... implementation depends on LearningPath structure
        return None
