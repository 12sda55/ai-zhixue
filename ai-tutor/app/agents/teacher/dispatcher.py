"""Agent分发调度器 - Function Calling结果处理

对照 ai_architecture_plan.md：
- 参数校验：Function Calling返回后校验参数完整性
- 规则兜底：检测到知识点名称→强制走文档+题库Agent
- 降级模式：Function Calling失败→纯对话模式
- 调用限制：单轮最多5次Agent调用
"""

from __future__ import annotations
import logging
from typing import Optional

from app.schemas.knowledge_graph import get_knowledge_node

logger = logging.getLogger(__name__)

# ===== 知识点名称标准化映射 =====

KNOWLEDGE_POINT_ALIASES = {
    # 中文名 → 标准ID（严格对照 knowledge_graph.py 中的31个知识点ID）
    # 线性结构
    "数组": "array",
    "链表": "linked_list",
    "栈": "stack",
    "队列": "queue",
    "双端队列": "deque",
    "串": "string",
    # 哈希
    "哈希表": "hash_table",
    "散列表": "hash_table",
    "字典": "hash_table",
    # 树结构
    "二叉树": "binary_tree",
    "树": "binary_tree",
    "二叉搜索树": "bst",
    "BST": "bst",
    "二叉查找树": "bst",
    "AVL树": "avl",
    "AVL": "avl",
    "红黑树": "red_black_tree",
    "堆": "heap",
    "优先队列": "heap",
    "B树": "b_tree",
    # 图结构
    "图": "graph_basics",
    "图的基本概念": "graph_basics",
    "图的遍历": "graph_traversal",
    "广度优先": "graph_traversal",
    "BFS": "graph_traversal",
    "深度优先": "graph_traversal",
    "DFS": "graph_traversal",
    "拓扑排序": "topological_sort",
    "最短路径": "shortest_path",
    "Dijkstra": "shortest_path",
    "最小生成树": "mst",
    # 排序
    "排序": "bubble_sort",
    "冒泡排序": "bubble_sort",
    "选择排序": "selection_sort",
    "插入排序": "insertion_sort",
    "希尔排序": "shell_sort",
    "快速排序": "quick_sort",
    "归并排序": "merge_sort",
    "堆排序": "heap_sort",
    "基数排序": "radix_sort",
    # 查找
    "查找": "sequential_search",
    "顺序查找": "sequential_search",
    "线性查找": "sequential_search",
    "二分查找": "binary_search",
    "折半查找": "binary_search",
    "BST查找": "bst_search",
    # 基础
    "递归": "recursion",
    "复杂度": "complexity",
    "时间复杂度": "complexity",
    "空间复杂度": "complexity",
    "算法复杂度": "complexity",
}


def normalize_knowledge_point(kp: str) -> str:
    """标准化知识点名称

    支持中文名、别名、标准ID，统一转为标准ID。
    例如："二叉搜索树" → "bst", "数组" → "array"
    """
    if not kp:
        return ""

    # 先查别名映射
    if kp in KNOWLEDGE_POINT_ALIASES:
        return KNOWLEDGE_POINT_ALIASES[kp]

    # 再查知识点依赖图
    node = get_knowledge_node(kp)
    if node:
        return kp

    # 尝试小写匹配
    kp_lower = kp.lower().replace(" ", "_")
    if kp_lower in KNOWLEDGE_POINT_ALIASES:
        return KNOWLEDGE_POINT_ALIASES[kp_lower]

    node = get_knowledge_node(kp_lower)
    if node:
        return kp_lower

    # 无法识别，返回原始值（后续Agent可能自行处理）
    logger.warning(f"无法识别的知识点名称: {kp}")
    return kp


def validate_agent_args(agent_name: str, args: dict) -> dict:
    """校验并补全Agent调用参数

    Args:
        agent_name: Agent名称
        args: Function Calling返回的参数

    Returns:
        校验后的参数dict
    """
    validated = dict(args)

    # 通用校验：user_id必填
    if "user_id" not in validated or not validated["user_id"]:
        logger.warning(f"Agent {agent_name} 缺少user_id，使用默认值")
        validated["user_id"] = "unknown"

    # 各Agent特定校验
    if agent_name in ("document_agent", "question_agent", "code_agent",
                      "multimodal_agent", "tutor_agent"):
        # 知识点名称标准化
        kp = validated.get("knowledge_point", "")
        if kp:
            validated["knowledge_point"] = normalize_knowledge_point(kp)
        else:
            logger.warning(f"Agent {agent_name} 缺少knowledge_point")

    if agent_name == "question_agent":
        # 题目数量默认3
        if "count" not in validated or validated["count"] <= 0:
            validated["count"] = 3
        if "count" not in validated or validated["count"] > 10:
            validated["count"] = 10  # 最多10题

    if agent_name == "code_agent":
        # 代码操作默认template
        if "action" not in validated:
            validated["action"] = "template"

    if agent_name == "tutor_agent":
        # 辅导模式默认socratic
        if "mode" not in validated:
            validated["mode"] = "socratic"

    return validated


def apply_fallback_rules(agent_calls: list[dict]) -> list[dict]:
    """规则兜底：检测到知识点名称→强制走文档+题库Agent

    当LLM只调了一个Agent但涉及知识点学习时，
    自动补充文档Agent和题库Agent调用。

    Args:
        agent_calls: LLM决定的Agent调用列表

    Returns:
        补充后的Agent调用列表
    """
    if not agent_calls:
        return agent_calls

    called_agents = {call["agent"] for call in agent_calls}

    # 检查是否有涉及知识点的调用
    knowledge_points = set()
    for call in agent_calls:
        kp = call.get("args", {}).get("knowledge_point", "")
        if kp:
            knowledge_points.add(kp)

    if not knowledge_points:
        return agent_calls

    # 规则1：如果涉及知识点但没调文档Agent，补充
    if "document_agent" not in called_agents and knowledge_points:
        for kp in knowledge_points:
            agent_calls.append({
                "agent": "document_agent",
                "args": {
                    "knowledge_point": kp,
                    "user_id": agent_calls[0]["args"].get("user_id", "unknown"),
                    "style": "concept",
                },
                "call_id": f"fallback_doc_{kp}",
            })
            logger.info(f"规则兜底：补充文档Agent调用，知识点={kp}")

    # 规则2：如果涉及知识点但没调题库Agent，补充
    if "question_agent" not in called_agents and knowledge_points:
        for kp in knowledge_points:
            agent_calls.append({
                "agent": "question_agent",
                "args": {
                    "knowledge_point": kp,
                    "user_id": agent_calls[0]["args"].get("user_id", "unknown"),
                    "count": 2,  # 兜底只出2题
                    "question_type": "choice",
                },
                "call_id": f"fallback_q_{kp}",
            })
            logger.info(f"规则兜底：补充题库Agent调用，知识点={kp}")

    return agent_calls


def check_call_limit(call_count: int, max_calls: int = 5) -> bool:
    """检查Agent调用次数是否超限

    Args:
        call_count: 当前调用次数
        max_calls: 最大调用次数

    Returns:
        True=还可以调用，False=已达上限
    """
    return call_count < max_calls


# ===== 依赖规则表 =====

# 定义哪些Agent可以并行，哪些必须串行
AGENT_DEPENDENCIES = {
    # path_agent 依赖 profile_agent 的结果
    "path_agent": ["profile_agent"],
    # tutor_agent 可以依赖 document_agent 的内容
    "tutor_agent": [],  # 可并行
    # 其他Agent之间无依赖
    "document_agent": [],
    "question_agent": [],
    "code_agent": [],
    "multimodal_agent": [],
    "profile_agent": [],
}

# 可并行的Agent组合
PARALLEL_GROUPS = [
    {"document_agent", "question_agent", "multimodal_agent"},  # 学习资料三件套
    {"code_agent", "question_agent"},  # 代码+题目
]


def get_execution_plan(agent_calls: list[dict]) -> list[list[dict]]:
    """根据依赖规则生成执行计划（分层执行）

    Returns:
        分层执行计划，每层内的Agent可并行执行
        例如：[[profile_agent], [document_agent, question_agent, multimodal_agent]]
    """
    if not agent_calls:
        return []

    # 简单分层算法
    called_names = {call["agent"] for call in agent_calls}
    remaining = list(agent_calls)
    plan = []

    while remaining:
        # 找出当前层可执行的Agent（依赖已满足）
        current_layer = []
        still_remaining = []

        for call in remaining:
            agent_name = call["agent"]
            deps = AGENT_DEPENDENCIES.get(agent_name, [])
            # 检查依赖是否都已在之前的层中
            deps_met = all(
                dep not in called_names or any(
                    prev_call["agent"] == dep
                    for layer in plan
                    for prev_call in layer
                )
                for dep in deps
            )
            if deps_met:
                current_layer.append(call)
            else:
                still_remaining.append(call)

        if not current_layer:
            # 避免死锁：如果没有任何Agent可以执行，全部放入当前层
            plan.append(still_remaining)
            break

        plan.append(current_layer)
        remaining = still_remaining

    return plan
