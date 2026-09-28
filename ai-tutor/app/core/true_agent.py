"""TrueAgent 抽象基类 — 每个Agent必须实现 think→execute→reflect 三阶段"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


# Agent 注册表
AGENT_REGISTRY: Dict[str, type] = {}


def register_agent(name: str):
    """Agent注册装饰器

    用法:
        @register_agent("document_agent")
        class DocumentAgent(TrueAgent):
            ...
    """
    def decorator(cls):
        AGENT_REGISTRY[name] = cls
        cls._agent_name = name
        return cls
    return decorator


@dataclass
class AgentPlan:
    """Agent的执行计划（think阶段的输出）"""
    tasks: List[Dict] = field(default_factory=list)  # 要执行的任务列表
    focus_areas: List[str] = field(default_factory=list)  # 重点关注领域
    parameters: Dict = field(default_factory=dict)  # 执行参数


@dataclass
class AgentResult:
    """Agent的执行结果"""
    success: bool = True
    data: Dict = field(default_factory=dict)
    resources: List[Dict] = field(default_factory=list)  # 生成的资源
    summary: str = ""  # 结果摘要
    errors: List[str] = field(default_factory=list)


@dataclass
class AgentReflection:
    """Agent的自省结果"""
    quality_score: float = 0.0  # 0-1
    issues: List[str] = field(default_factory=list)  # 发现的问题
    improvements: List[str] = field(default_factory=list)  # 改进建议
    should_retry: bool = False  # 是否需要重试


class TrueAgent(ABC):
    """TrueAgent 抽象基类

    每个Agent必须实现三阶段：
    1. think() — 分析任务，制定执行计划
    2. execute() — 执行计划，生成结果
    3. reflect() — 自省结果质量

    可选实现：
    - remember() — 从历史记忆中获取上下文
    - memorize() — 将结果存入记忆
    """

    _agent_name: str = ""

    def __init__(self, context=None):
        """初始化Agent

        Args:
            context: ExecutionContext，包含db_session, user_id, profile等
        """
        self.context = context
        self._plan: Optional[AgentPlan] = None
        self._result: Optional[AgentResult] = None
        self._reflection: Optional[AgentReflection] = None
        self._memory: Dict = {}

    @property
    def agent_name(self) -> str:
        return self._agent_name or self.__class__.__name__

    async def run(self, task: Dict) -> AgentResult:
        """完整的Agent执行流程：think→execute→reflect

        Args:
            task: 任务描述，包含intent, knowledge_point, user_message等

        Returns:
            AgentResult: 执行结果
        """
        # 1. 记忆阶段
        self._memory = await self.remember(task)

        # 2. 思考阶段
        self._plan = await self.think(task)
        logger.info(f"[{self.agent_name}] Plan: {len(self._plan.tasks)} tasks, focus: {self._plan.focus_areas}")

        # 3. 执行阶段
        self._result = await self.execute(self._plan)
        logger.info(f"[{self.agent_name}] Result: success={self._result.success}, resources={len(self._result.resources)}")

        # 4. 自省阶段
        self._reflection = await self.reflect(self._result)
        logger.info(f"[{self.agent_name}] Reflection: quality={self._reflection.quality_score:.2f}")

        # 5. 如果质量不达标且需要重试，最多重试1次
        if self._reflection.should_retry and self._reflection.quality_score < 0.5:
            logger.info(f"[{self.agent_name}] Quality low ({self._reflection.quality_score:.2f}), retrying...")
            self._plan = await self.think(task)  # 重新规划
            self._result = await self.execute(self._plan)
            self._reflection = await self.reflect(self._result)

        # 6. 记忆存储
        await self.memorize(self._result)

        return self._result

    @abstractmethod
    async def think(self, task: Dict) -> AgentPlan:
        """思考阶段：分析任务，制定执行计划

        Args:
            task: 任务描述

        Returns:
            AgentPlan: 执行计划
        """
        ...

    @abstractmethod
    async def execute(self, plan: AgentPlan) -> AgentResult:
        """执行阶段：按计划执行，生成结果

        Args:
            plan: 执行计划

        Returns:
            AgentResult: 执行结果
        """
        ...

    @abstractmethod
    async def reflect(self, result: AgentResult) -> AgentReflection:
        """自省阶段：检查结果质量

        Args:
            result: 执行结果

        Returns:
            AgentReflection: 自省结果
        """
        ...

    async def remember(self, task: Dict) -> Dict:
        """记忆阶段：从历史中获取上下文（可选重写）

        Args:
            task: 当前任务

        Returns:
            Dict: 记忆上下文
        """
        memory = {}
        if self.context:
            # 从ExecutionContext获取已有资源
            try:
                memory["previous_resources"] = self.context.get_agent_outputs()
            except Exception:
                pass
        return memory

    async def memorize(self, result: AgentResult) -> None:
        """记忆存储：将结果存入上下文（可选重写）

        Args:
            result: 执行结果
        """
        if self.context and result.success:
            try:
                self.context.add_agent_output(self.agent_name, result.data)
            except Exception:
                pass
