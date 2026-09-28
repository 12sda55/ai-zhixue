"""多模态资源Agent服务 - 对照 ai_architecture_plan.md Agent 5

提供可视化配置、思维导图、算法时间机器、算法对比、B站视频推荐、
云视频共享、代码可视化等多模态学习资源服务。
"""

from __future__ import annotations

import copy
import logging
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.knowledge_graph import (
    KNOWLEDGE_GRAPH,
    get_knowledge_node,
    get_dependencies,
    get_all_dependents,
)
from app.schemas.profile import StudentProfile, CognitiveStyle, DifficultyLevel
from app.knowledge.texts import KNOWLEDGE_TEXTS
from app.core.llm import llm_client

logger = logging.getLogger(__name__)


# ===== 数据模型 =====


class StepHighlight(BaseModel):
    """步骤高亮信息"""
    indices: list[int] = Field(default_factory=list, description="高亮的索引列表")
    highlight_type: str = Field(default="compare", description="高亮类型: compare/swap/sorted/current")


class AlgorithmStep(BaseModel):
    """算法执行步骤"""
    step_number: int
    description: str
    array_state: list[int]
    highlights: list[StepHighlight] = Field(default_factory=list)
    comparisons: int = 0
    swaps: int = 0


class TreeNodeState(BaseModel):
    """树节点状态"""
    value: int
    left: Optional[int] = None  # 子节点索引
    right: Optional[int] = None
    highlighted: bool = False


class TreeAlgorithmStep(BaseModel):
    """树操作算法步骤"""
    step_number: int
    description: str
    tree_state: list[TreeNodeState] = Field(default_factory=list)
    highlighted_node: Optional[int] = None  # 高亮节点索引


class VisualizationConfig(BaseModel):
    """可视化组件配置"""
    component_type: str
    data_schema: dict
    default_data: dict
    steps: list[str] = Field(default_factory=list)
    controls: dict = Field(default_factory=dict)


class ComparisonMetrics(BaseModel):
    """算法对比指标"""
    algorithm1_comparisons: int = 0
    algorithm1_swaps: int = 0
    algorithm1_time_complexity: str = ""
    algorithm2_comparisons: int = 0
    algorithm2_swaps: int = 0
    algorithm2_time_complexity: str = ""


class AlgorithmComparison(BaseModel):
    """算法对比结果"""
    algorithm1_steps: list[AlgorithmStep]
    algorithm2_steps: list[AlgorithmStep]
    shared_input_data: list[int]
    comparison_metrics: ComparisonMetrics


class VideoRecommendation(BaseModel):
    """视频推荐条目"""
    title: str
    url: str
    duration: str
    knowledge_points: list[str] = Field(default_factory=list)
    difficulty: str = "basic"


class CloudVideo(BaseModel):
    """云视频资源"""
    video_id: str
    title: str
    url: str
    knowledge_point: str
    uploaded_by: str = ""
    rating: float = 0.0
    rating_count: int = 0
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CodeVisualizationStep(BaseModel):
    """代码可视化步骤"""
    line_number: int
    description: str
    variables: dict = Field(default_factory=dict, description="当前变量状态")
    output: str = ""
    call_stack: list[str] = Field(default_factory=list, description="调用栈")


class CodeVisualizationConfig(BaseModel):
    """代码可视化配置"""
    code: str
    language: str = "python"
    steps: list[CodeVisualizationStep] = Field(default_factory=list)
    total_steps: int = 0


# ===== 可视化配置数据 =====
# 只保留 component_type、data_schema、controls（这些是前端组件配置，不是数据）
# default_data 和 steps 由 get_visualization_config 动态生成

_VISUALIZATION_CONFIGS: dict[str, dict] = {
    "array": {
        "component_type": "array_visualizer",
        "data_schema": {
            "type": "object",
            "properties": {
                "elements": {"type": "array", "items": {"type": "integer"}},
                "highlights": {"type": "array", "items": {"type": "integer"}},
                "labels": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["elements"],
        },
        "controls": {"play": True, "pause": True, "step": True, "rewind": True, "speed": [0.5, 1.0, 2.0]},
    },
    "linked_list": {
        "component_type": "linked_list_visualizer",
        "data_schema": {
            "type": "object",
            "properties": {
                "nodes": {"type": "array", "items": {"type": "object", "properties": {"value": {"type": "integer"}, "next": {"type": "integer"}}}},
                "highlight_node": {"type": "integer"},
                "operation": {"type": "string"},
            },
            "required": ["nodes"],
        },
        "controls": {"play": True, "pause": True, "step": True, "rewind": True, "speed": [0.5, 1.0, 2.0]},
    },
    "stack": {
        "component_type": "stack_visualizer",
        "data_schema": {
            "type": "object",
            "properties": {
                "elements": {"type": "array", "items": {"type": "integer"}},
                "top_index": {"type": "integer"},
                "operation": {"type": "string"},
            },
            "required": ["elements"],
        },
        "controls": {"play": True, "pause": True, "step": True, "rewind": True, "speed": [0.5, 1.0, 2.0]},
    },
    "queue": {
        "component_type": "queue_visualizer",
        "data_schema": {
            "type": "object",
            "properties": {
                "elements": {"type": "array", "items": {"type": "integer"}},
                "front": {"type": "integer"},
                "rear": {"type": "integer"},
                "operation": {"type": "string"},
            },
            "required": ["elements"],
        },
        "controls": {"play": True, "pause": True, "step": True, "rewind": True, "speed": [0.5, 1.0, 2.0]},
    },
    "binary_tree": {
        "component_type": "tree_visualizer",
        "data_schema": {
            "type": "object",
            "properties": {
                "nodes": {"type": "array", "items": {"type": "object", "properties": {"value": {"type": "integer"}, "left": {"type": "integer"}, "right": {"type": "integer"}}}},
                "highlight_node": {"type": "integer"},
                "traversal_order": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["nodes"],
        },
        "controls": {"play": True, "pause": True, "step": True, "rewind": True, "speed": [0.5, 1.0, 2.0]},
    },
    "bst": {
        "component_type": "tree_visualizer",
        "data_schema": {
            "type": "object",
            "properties": {
                "nodes": {"type": "array", "items": {"type": "object", "properties": {"value": {"type": "integer"}, "left": {"type": "integer"}, "right": {"type": "integer"}}}},
                "highlight_node": {"type": "integer"},
                "search_path": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["nodes"],
        },
        "controls": {"play": True, "pause": True, "step": True, "rewind": True, "speed": [0.5, 1.0, 2.0]},
    },
    "avl": {
        "component_type": "tree_visualizer",
        "data_schema": {
            "type": "object",
            "properties": {
                "nodes": {"type": "array", "items": {"type": "object", "properties": {"value": {"type": "integer"}, "left": {"type": "integer"}, "right": {"type": "integer"}, "balance_factor": {"type": "integer"}}}},
                "highlight_node": {"type": "integer"},
                "rotation_type": {"type": "string"},
            },
            "required": ["nodes"],
        },
        "controls": {"play": True, "pause": True, "step": True, "rewind": True, "speed": [0.5, 1.0, 2.0]},
    },
    "heap": {
        "component_type": "tree_visualizer",
        "data_schema": {
            "type": "object",
            "properties": {
                "array_representation": {"type": "array", "items": {"type": "integer"}},
                "highlight_indices": {"type": "array", "items": {"type": "integer"}},
                "operation": {"type": "string"},
            },
            "required": ["array_representation"],
        },
        "controls": {"play": True, "pause": True, "step": True, "rewind": True, "speed": [0.5, 1.0, 2.0]},
    },
    "graph_basics": {
        "component_type": "graph_visualizer",
        "data_schema": {
            "type": "object",
            "properties": {
                "nodes": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "label": {"type": "string"}}}},
                "edges": {"type": "array", "items": {"type": "object", "properties": {"from": {"type": "integer"}, "to": {"type": "integer"}, "weight": {"type": "integer"}}}},
                "directed": {"type": "boolean"},
                "highlight_nodes": {"type": "array", "items": {"type": "integer"}},
                "highlight_edges": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["nodes", "edges"],
        },
        "controls": {"play": True, "pause": True, "step": True, "rewind": True, "speed": [0.5, 1.0, 2.0]},
    },
    "graph_traversal": {
        "component_type": "graph_visualizer",
        "data_schema": {
            "type": "object",
            "properties": {
                "nodes": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "label": {"type": "string"}}}},
                "edges": {"type": "array", "items": {"type": "object", "properties": {"from": {"type": "integer"}, "to": {"type": "integer"}, "weight": {"type": "integer"}}}},
                "directed": {"type": "boolean"},
                "visited": {"type": "array", "items": {"type": "integer"}},
                "current_node": {"type": "integer"},
                "queue_or_stack": {"type": "array", "items": {"type": "integer"}},
                "traversal_order": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["nodes", "edges"],
        },
        "controls": {"play": True, "pause": True, "step": True, "rewind": True, "speed": [0.5, 1.0, 2.0]},
    },
    "bubble_sort": {
        "component_type": "sort_visualizer",
        "data_schema": {
            "type": "object",
            "properties": {
                "array": {"type": "array", "items": {"type": "integer"}},
                "comparing": {"type": "array", "items": {"type": "integer"}},
                "swapping": {"type": "array", "items": {"type": "integer"}},
                "sorted": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["array"],
        },
        "controls": {"play": True, "pause": True, "step": True, "rewind": True, "speed": [0.5, 1.0, 2.0, 4.0]},
    },
    "quick_sort": {
        "component_type": "sort_visualizer",
        "data_schema": {
            "type": "object",
            "properties": {
                "array": {"type": "array", "items": {"type": "integer"}},
                "pivot": {"type": "integer"},
                "left_partition": {"type": "array", "items": {"type": "integer"}},
                "right_partition": {"type": "array", "items": {"type": "integer"}},
                "comparing": {"type": "array", "items": {"type": "integer"}},
                "sorted": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["array"],
        },
        "controls": {"play": True, "pause": True, "step": True, "rewind": True, "speed": [0.5, 1.0, 2.0, 4.0]},
    },
    "merge_sort": {
        "component_type": "sort_visualizer",
        "data_schema": {
            "type": "object",
            "properties": {
                "array": {"type": "array", "items": {"type": "integer"}},
                "left_half": {"type": "array", "items": {"type": "integer"}},
                "right_half": {"type": "array", "items": {"type": "integer"}},
                "merging": {"type": "array", "items": {"type": "integer"}},
                "sorted": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["array"],
        },
        "controls": {"play": True, "pause": True, "step": True, "rewind": True, "speed": [0.5, 1.0, 2.0, 4.0]},
    },
    "hash_table": {
        "component_type": "hash_table_visualizer",
        "data_schema": {
            "type": "object",
            "properties": {
                "buckets": {"type": "array", "items": {"type": "array", "items": {"type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "integer"}}}}},
                "highlight_bucket": {"type": "integer"},
                "operation": {"type": "string"},
                "load_factor": {"type": "number"},
            },
            "required": ["buckets"],
        },
        "controls": {"play": True, "pause": True, "step": True, "rewind": True, "speed": [0.5, 1.0, 2.0]},
    },
}


def _generate_default_data(knowledge_point: str) -> dict:
    """根据知识点动态生成默认可视化数据

    对于排序算法，运行实际算法获取初始状态；
    对于数据结构，生成标准示例数据。
    """
    import random

    # 排序类：生成随机数组
    sort_kps = {"bubble_sort", "selection_sort", "insertion_sort", "quick_sort", "merge_sort", "heap_sort"}
    if knowledge_point in sort_kps:
        arr = random.sample(range(1, 20), min(8, 10))
        return {"array": arr, "comparing": [], "swapping": [], "sorted": []}

    # 数据结构类
    if knowledge_point == "array":
        arr = random.sample(range(1, 20), 8)
        return {"elements": arr, "highlights": [], "labels": []}

    if knowledge_point == "linked_list":
        values = random.sample(range(1, 10), 4)
        nodes = [{"value": v, "next": i + 1 if i < len(values) - 1 else -1} for i, v in enumerate(values)]
        return {"nodes": nodes, "highlight_node": -1, "operation": "traverse"}

    if knowledge_point == "stack":
        values = random.sample(range(1, 10), 3)
        return {"elements": values, "top_index": len(values) - 1, "operation": "push"}

    if knowledge_point == "queue":
        values = random.sample(range(1, 10), 3)
        return {"elements": values, "front": 0, "rear": len(values) - 1, "operation": "enqueue"}

    if knowledge_point == "binary_tree":
        values = random.sample(range(1, 15), 5)
        nodes = []
        for i, v in enumerate(values):
            left = 2 * i + 1 if 2 * i + 1 < len(values) else -1
            right = 2 * i + 2 if 2 * i + 2 < len(values) else -1
            nodes.append({"value": v, "left": left, "right": right})
        return {"nodes": nodes, "highlight_node": -1, "traversal_order": []}

    if knowledge_point == "bst":
        values = random.sample(range(1, 15), 6)
        # Build BST structure
        nodes = _build_bst_nodes(values)
        return {"nodes": nodes, "highlight_node": -1, "search_path": []}

    if knowledge_point == "avl":
        values = random.sample(range(1, 15), 4)
        nodes = _build_bst_nodes(values)
        # Add balance_factor
        for node in nodes:
            node["balance_factor"] = 0
        return {"nodes": nodes, "highlight_node": -1, "rotation_type": ""}

    if knowledge_point == "heap":
        arr = random.sample(range(1, 15), 7)
        return {"array_representation": arr, "highlight_indices": [], "operation": "insert"}

    if knowledge_point == "graph_basics":
        n = 4
        nodes = [{"id": i, "label": chr(65 + i)} for i in range(n)]
        edges = [
            {"from": 0, "to": 1, "weight": 1},
            {"from": 0, "to": 2, "weight": 1},
            {"from": 1, "to": 3, "weight": 1},
            {"from": 2, "to": 3, "weight": 1},
        ]
        return {"nodes": nodes, "edges": edges, "directed": False, "highlight_nodes": [], "highlight_edges": []}

    if knowledge_point == "graph_traversal":
        n = 5
        nodes = [{"id": i, "label": chr(65 + i)} for i in range(n)]
        edges = [
            {"from": 0, "to": 1, "weight": 1},
            {"from": 0, "to": 2, "weight": 1},
            {"from": 1, "to": 3, "weight": 1},
            {"from": 2, "to": 3, "weight": 1},
            {"from": 3, "to": 4, "weight": 1},
        ]
        return {
            "nodes": nodes, "edges": edges, "directed": False,
            "visited": [], "current_node": -1, "queue_or_stack": [], "traversal_order": [],
        }

    if knowledge_point == "hash_table":
        keys = ["a", "d", "f", "q"]
        values_map = {"a": 1, "d": 4, "f": 6, "q": 17}
        bucket_count = 8
        buckets = [[] for _ in range(bucket_count)]
        for k, v in values_map.items():
            idx = hash(k) % bucket_count
            buckets[idx].append({"key": k, "value": v})
        return {"buckets": buckets, "highlight_bucket": -1, "operation": "insert", "load_factor": len(keys) / bucket_count}

    # 默认
    return {"elements": [3, 1, 4, 1, 5, 9, 2, 6], "highlights": [], "labels": []}


def _build_bst_nodes(values: list[int]) -> list[dict]:
    """根据插入序列构建BST节点列表（用于可视化）"""
    nodes: list[dict] = []
    for val in values:
        if not nodes:
            nodes.append({"value": val, "left": -1, "right": -1})
            continue
        curr_idx = 0
        while True:
            if val < nodes[curr_idx]["value"]:
                if nodes[curr_idx]["left"] == -1:
                    new_idx = len(nodes)
                    nodes[curr_idx]["left"] = new_idx
                    nodes.append({"value": val, "left": -1, "right": -1})
                    break
                curr_idx = nodes[curr_idx]["left"]
            else:
                if nodes[curr_idx]["right"] == -1:
                    new_idx = len(nodes)
                    nodes[curr_idx]["right"] = new_idx
                    nodes.append({"value": val, "left": -1, "right": -1})
                    break
                curr_idx = nodes[curr_idx]["right"]
    return nodes


def _generate_steps(knowledge_point: str) -> list[str]:
    """根据知识点动态生成步骤描述

    对于排序算法，从时间机器步骤中提取描述；
    对于数据结构，生成操作步骤描述。
    """
    # 排序类：从时间机器步骤提取
    sort_kps = {"bubble_sort", "selection_sort", "insertion_sort", "quick_sort", "merge_sort", "heap_sort"}
    if knowledge_point in sort_kps:
        try:
            steps_data = multimodal_service.get_time_machine_steps(knowledge_point)
            if steps_data:
                return [s.description for s in steps_data[:10]]
        except Exception:
            pass
        # 降级：返回通用步骤
        return ["初始化数组", "执行排序操作", "排序完成"]

    # 数据结构类
    step_templates = {
        "array": ["初始化数组", "访问指定索引元素", "尾部插入元素", "中间插入元素（需移动后续元素）", "删除元素（需移动后续元素）"],
        "linked_list": ["创建头节点", "逐节点遍历", "头部插入O(1)", "中间插入O(1)（已知前驱）", "删除节点（修改指针）"],
        "stack": ["空栈", "push(1)", "push(2)", "push(3)", "pop() → 3", "peek() → 2"],
        "queue": ["空队列", "enqueue(1)", "enqueue(2)", "enqueue(3)", "dequeue() → 1", "查看队头 → 2"],
        "binary_tree": ["构建二叉树", "前序遍历：根→左→右", "中序遍历：左→根→右", "后序遍历：左→右→根", "层序遍历：BFS逐层"],
        "bst": ["BST性质：左<根<右", "查找：从根开始比较", "插入：找到空位挂载", "删除叶节点", "删除单子节点：替代", "删除双子节点：找后继替代"],
        "avl": ["插入节点后检查平衡因子", "LL型→右旋", "RR型→左旋", "LR型→先左旋再右旋", "RL型→先右旋再左旋", "旋转后更新平衡因子"],
        "heap": ["完全二叉树的数组表示", "插入：添加到末尾，上浮调整", "取堆顶：返回根节点", "删除堆顶：末尾替代，下沉调整", "建堆：从最后一个非叶节点下沉"],
        "graph_basics": ["图的顶点和边", "邻接矩阵表示", "邻接表表示", "度数计算", "连通性判断"],
        "graph_traversal": ["选择起始节点", "BFS：入队→出队→访问→邻居入队", "BFS：逐层扩展", "DFS：入栈→出栈→访问→邻居入栈", "DFS：一条路走到底再回溯", "遍历完成"],
        "hash_table": ["哈希函数计算桶索引", "插入：放入对应桶", "冲突：链地址法追加到桶链表", "查找：计算索引→遍历桶链表", "负载因子过高→扩容rehash"],
    }
    return step_templates.get(knowledge_point, ["初始化", "执行操作", "完成"])


# ===== 服务类 =====


class MultimodalService:
    """多模态资源Agent服务

    提供可视化配置、思维导图、算法时间机器、算法对比、
    B站视频推荐、云视频共享、代码可视化等功能。
    """

    def __init__(self):
        pass

    # ============================================================
    # 1. 可视化配置
    # ============================================================

    def get_visualization_config(self, knowledge_point: str) -> Optional[VisualizationConfig]:
        """获取知识点对应的可视化组件配置

        component_type 和 data_schema 来自预定义配置（前端组件类型），
        default_data 和 steps 动态生成（实际数据内容）。

        Args:
            knowledge_point: 知识点ID，如 "array", "bst", "bubble_sort"

        Returns:
            VisualizationConfig 或 None（无对应配置时）
        """
        config = _VISUALIZATION_CONFIGS.get(knowledge_point)
        if config:
            return VisualizationConfig(
                component_type=config["component_type"],
                data_schema=config["data_schema"],
                default_data=_generate_default_data(knowledge_point),
                steps=_generate_steps(knowledge_point),
                controls=config.get("controls", {}),
            )

        # 尝试根据类别推断
        node = get_knowledge_node(knowledge_point)
        if not node:
            logger.warning("未找到知识点 %s 的可视化配置", knowledge_point)
            return None

        # 排序类知识点使用 sort_visualizer
        if node.category == "排序":
            sort_config = _VISUALIZATION_CONFIGS["bubble_sort"]
            return VisualizationConfig(
                component_type="sort_visualizer",
                data_schema=sort_config["data_schema"],
                default_data=_generate_default_data(knowledge_point),
                steps=_generate_steps(knowledge_point),
                controls=sort_config.get("controls", {}),
            )

        # 查找类知识点使用 tree_visualizer 或 array_visualizer
        if node.category == "查找":
            if "bst" in knowledge_point:
                return self.get_visualization_config("bst")
            return self.get_visualization_config("array")

        # 图类知识点
        if node.category == "图结构":
            return self.get_visualization_config("graph_basics")

        # 树类知识点
        if node.category == "树结构":
            return self.get_visualization_config("binary_tree")

        logger.warning("知识点 %s 无匹配的可视化配置", knowledge_point)
        return None

    # ============================================================
    # 2. 思维导图生成
    # ============================================================

    def generate_mind_map(self, knowledge_point: str, max_depth: int = 3) -> str:
        """生成知识点的思维导图（Markdown格式，可被Markmap渲染）

        Args:
            knowledge_point: 知识点ID
            max_depth: 最大展开深度

        Returns:
            层级Markdown字符串
        """
        node = get_knowledge_node(knowledge_point)
        if not node:
            logger.warning("未找到知识点: %s", knowledge_point)
            return f"# {knowledge_point}"

        # 尝试LLM生成，失败则使用模板
        try:
            return self._generate_mind_map_with_llm(knowledge_point, max_depth)
        except Exception as e:
            logger.warning("LLM思维导图生成失败，降级为模板: %s", e)
            return self._generate_mind_map_template(knowledge_point, max_depth)

    def _generate_mind_map_with_llm(self, knowledge_point: str, max_depth: int) -> str:
        """使用LLM生成思维导图"""
        node = get_knowledge_node(knowledge_point)
        text_content = KNOWLEDGE_TEXTS.get(knowledge_point, "")

        # 获取依赖和后续知识点
        deps = get_dependencies(knowledge_point)
        dependents = get_all_dependents(knowledge_point)

        dep_names = []
        for dep_id in deps:
            dep_node = get_knowledge_node(dep_id)
            dep_names.append(dep_node.name if dep_node else dep_id)

        dep_names_str = "、".join(dep_names) if dep_names else "无"

        dependent_names = []
        for dep_id in dependents[:5]:
            dep_node = get_knowledge_node(dep_id)
            dependent_names.append(dep_node.name if dep_node else dep_id)
        dependent_names_str = "、".join(dependent_names) if dependent_names else "无"

        prompt = f"""请为知识点「{node.name}」生成一个思维导图，使用Markdown层级格式输出。

要求：
1. 第一行是 # {node.name}
2. 使用 ## 和 ### 等标题层级表示分支
3. 使用 - 列表项表示叶子节点
4. 深度不超过{max_depth}层
5. 内容要涵盖：核心概念、关键操作、时间复杂度、应用场景、常见误区
6. 前置知识：{dep_names_str}
7. 后续知识：{dependent_names_str}

参考知识内容：
{text_content[:1500]}

请直接输出Markdown格式的思维导图，不要其他解释。"""

        result = llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500,
        )
        return result.strip()

    def _generate_mind_map_template(self, knowledge_point: str, max_depth: int) -> str:
        """模板方式生成思维导图（LLM降级方案）"""
        node = get_knowledge_node(knowledge_point)
        if not node:
            return f"# {knowledge_point}"

        lines = [f"# {node.name}"]

        # 前置知识
        deps = get_dependencies(knowledge_point)
        if deps and max_depth >= 1:
            lines.append("\n## 前置知识")
            for dep_id in deps:
                dep_node = get_knowledge_node(dep_id)
                dep_name = dep_node.name if dep_node else dep_id
                if max_depth >= 2:
                    dep_deps = get_dependencies(dep_id)
                    lines.append(f"- {dep_name}")
                    for dd_id in dep_deps[:3]:
                        dd_node = get_knowledge_node(dd_id)
                        lines.append(f"  - {dd_node.name if dd_node else dd_id}")
                else:
                    lines.append(f"- {dep_name}")

        # 从知识文本提取关键概念
        text_content = KNOWLEDGE_TEXTS.get(knowledge_point, "")
        if text_content and max_depth >= 1:
            lines.append("\n## 核心概念")
            # 提取二级标题作为子主题
            for line in text_content.split("\n"):
                stripped = line.strip()
                if stripped.startswith("## ") and stripped != f"# {node.name}":
                    sub_topic = stripped[3:].strip()
                    lines.append(f"- {sub_topic}")

        # 关键操作
        if max_depth >= 1:
            lines.append("\n## 关键操作")
            category = node.category
            if category == "线性结构":
                lines.append("- 插入")
                lines.append("- 删除")
                lines.append("- 查找")
                lines.append("- 遍历")
            elif category == "树结构":
                lines.append("- 插入节点")
                lines.append("- 删除节点")
                lines.append("- 查找节点")
                lines.append("- 遍历（前序/中序/后序/层序）")
            elif category == "排序":
                lines.append("- 比较")
                lines.append("- 交换/移动")
                lines.append("- 分区/合并")
            elif category == "图结构":
                lines.append("- BFS遍历")
                lines.append("- DFS遍历")
                lines.append("- 最短路径")
                lines.append("- 最小生成树")
            elif category == "哈希":
                lines.append("- 哈希函数计算")
                lines.append("- 插入键值对")
                lines.append("- 查找键")
                lines.append("- 冲突处理")

        # 后续知识
        dependents = get_all_dependents(knowledge_point)
        if dependents and max_depth >= 1:
            lines.append("\n## 后续知识")
            for dep_id in dependents[:5]:
                dep_node = get_knowledge_node(dep_id)
                lines.append(f"- {dep_node.name if dep_node else dep_id}")

        return "\n".join(lines)

    # ============================================================
    # 3. 算法时间机器
    # ============================================================

    def get_time_machine_steps(
        self,
        algorithm: str,
        input_data: Optional[list[int]] = None,
    ) -> list[AlgorithmStep] | list[TreeAlgorithmStep]:
        """获取算法的逐步执行轨迹

        Args:
            algorithm: 算法名称，如 "bubble_sort", "quick_sort", "bst_insert"
            input_data: 输入数据，默认使用预设数据

        Returns:
            算法步骤列表（排序算法返回 AlgorithmStep，树操作返回 TreeAlgorithmStep）
        """
        sorting_algorithms = {
            "bubble_sort": self._trace_bubble_sort,
            "quick_sort": self._trace_quick_sort,
            "merge_sort": self._trace_merge_sort,
            "insertion_sort": self._trace_insertion_sort,
            "selection_sort": self._trace_selection_sort,
            "heap_sort": self._trace_heap_sort,
        }

        tree_algorithms = {
            "bst_insert": self._trace_bst_insert,
            "bst_search": self._trace_bst_search,
        }

        if algorithm in sorting_algorithms:
            data = input_data if input_data is not None else [5, 3, 8, 4, 2]
            return sorting_algorithms[algorithm](data)
        elif algorithm in tree_algorithms:
            data = input_data if input_data is not None else [8, 3, 10, 1, 6, 9]
            return tree_algorithms[algorithm](data)
        else:
            logger.warning("不支持的算法: %s", algorithm)
            return []

    def _trace_bubble_sort(self, data: list[int]) -> list[AlgorithmStep]:
        """冒泡排序步骤追踪"""
        arr = data.copy()
        steps: list[AlgorithmStep] = []
        n = len(arr)
        total_comparisons = 0
        total_swaps = 0

        steps.append(AlgorithmStep(
            step_number=0,
            description=f"初始数组: {arr}",
            array_state=arr.copy(),
            highlights=[],
            comparisons=0,
            swaps=0,
        ))

        for i in range(n - 1):
            swapped = False
            for j in range(n - 1 - i):
                total_comparisons += 1
                steps.append(AlgorithmStep(
                    step_number=len(steps),
                    description=f"比较 arr[{j}]={arr[j]} 和 arr[{j+1}]={arr[j+1]}",
                    array_state=arr.copy(),
                    highlights=[
                        StepHighlight(indices=[j, j + 1], highlight_type="compare"),
                    ],
                    comparisons=total_comparisons,
                    swaps=total_swaps,
                ))

                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
                    total_swaps += 1
                    swapped = True
                    steps.append(AlgorithmStep(
                        step_number=len(steps),
                        description=f"交换 arr[{j}] 和 arr[{j+1}]，数组变为: {arr}",
                        array_state=arr.copy(),
                        highlights=[
                            StepHighlight(indices=[j, j + 1], highlight_type="swap"),
                        ],
                        comparisons=total_comparisons,
                        swaps=total_swaps,
                    ))

            # 标记已排序部分
            sorted_indices = list(range(n - 1 - i, n))
            steps.append(AlgorithmStep(
                step_number=len(steps),
                description=f"第{i+1}轮完成，arr[{n-1-i}..{n-1}]已排序",
                array_state=arr.copy(),
                highlights=[
                    StepHighlight(indices=sorted_indices, highlight_type="sorted"),
                ],
                comparisons=total_comparisons,
                swaps=total_swaps,
            ))

            if not swapped:
                steps.append(AlgorithmStep(
                    step_number=len(steps),
                    description="本轮无交换，提前终止",
                    array_state=arr.copy(),
                    highlights=[StepHighlight(indices=list(range(n)), highlight_type="sorted")],
                    comparisons=total_comparisons,
                    swaps=total_swaps,
                ))
                break

        steps.append(AlgorithmStep(
            step_number=len(steps),
            description=f"排序完成: {arr}",
            array_state=arr.copy(),
            highlights=[StepHighlight(indices=list(range(n)), highlight_type="sorted")],
            comparisons=total_comparisons,
            swaps=total_swaps,
        ))

        return steps

    def _trace_quick_sort(self, data: list[int]) -> list[AlgorithmStep]:
        """快速排序步骤追踪"""
        arr = data.copy()
        steps: list[AlgorithmStep] = []
        _state = {"comparisons": 0, "swaps": 0}

        steps.append(AlgorithmStep(
            step_number=0,
            description=f"初始数组: {arr}",
            array_state=arr.copy(),
            highlights=[],
            comparisons=0,
            swaps=0,
        ))

        def _partition(lo: int, hi: int) -> int:
            pivot = arr[hi]
            steps.append(AlgorithmStep(
                step_number=len(steps),
                description=f"选择基准值 pivot={pivot}（arr[{hi}]）",
                array_state=arr.copy(),
                highlights=[StepHighlight(indices=[hi], highlight_type="current")],
                comparisons=_state["comparisons"],
                swaps=_state["swaps"],
            ))

            i = lo
            for j in range(lo, hi):
                _state["comparisons"] += 1
                steps.append(AlgorithmStep(
                    step_number=len(steps),
                    description=f"比较 arr[{j}]={arr[j]} 与 pivot={pivot}",
                    array_state=arr.copy(),
                    highlights=[
                        StepHighlight(indices=[j], highlight_type="compare"),
                        StepHighlight(indices=[hi], highlight_type="current"),
                    ],
                    comparisons=_state["comparisons"],
                    swaps=_state["swaps"],
                ))

                if arr[j] <= pivot:
                    if i != j:
                        arr[i], arr[j] = arr[j], arr[i]
                        _state["swaps"] += 1
                        steps.append(AlgorithmStep(
                            step_number=len(steps),
                            description=f"交换 arr[{i}] 和 arr[{j}]",
                            array_state=arr.copy(),
                            highlights=[StepHighlight(indices=[i, j], highlight_type="swap")],
                            comparisons=_state["comparisons"],
                            swaps=_state["swaps"],
                        ))
                    i += 1

            if i != hi:
                arr[i], arr[hi] = arr[hi], arr[i]
                _state["swaps"] += 1
                steps.append(AlgorithmStep(
                    step_number=len(steps),
                    description=f"pivot归位: 交换 arr[{i}] 和 arr[{hi}]，pivot位置={i}",
                    array_state=arr.copy(),
                    highlights=[StepHighlight(indices=[i], highlight_type="current")],
                    comparisons=_state["comparisons"],
                    swaps=_state["swaps"],
                ))

            return i

        def _quick_sort(lo: int, hi: int) -> None:
            if lo >= hi:
                return
            pivot_idx = _partition(lo, hi)
            _quick_sort(lo, pivot_idx - 1)
            _quick_sort(pivot_idx + 1, hi)

        _quick_sort(0, len(arr) - 1)

        steps.append(AlgorithmStep(
            step_number=len(steps),
            description=f"排序完成: {arr}",
            array_state=arr.copy(),
            highlights=[StepHighlight(indices=list(range(len(arr))), highlight_type="sorted")],
            comparisons=_state["comparisons"],
            swaps=_state["swaps"],
        ))

        return steps

    def _trace_merge_sort(self, data: list[int]) -> list[AlgorithmStep]:
        """归并排序步骤追踪"""
        arr = data.copy()
        steps: list[AlgorithmStep] = []
        _state = {"comparisons": 0, "swaps": 0}

        steps.append(AlgorithmStep(
            step_number=0,
            description=f"初始数组: {arr}",
            array_state=arr.copy(),
            highlights=[],
            comparisons=0,
            swaps=0,
        ))

        def _merge_sort(sub: list[int], start: int) -> list[int]:
            if len(sub) <= 1:
                return sub

            mid = len(sub) // 2
            steps.append(AlgorithmStep(
                step_number=len(steps),
                description=f"分割: [{start}..{start + len(sub) - 1}] → [{start}..{start + mid - 1}] 和 [{start + mid}..{start + len(sub) - 1}]",
                array_state=arr.copy(),
                highlights=[StepHighlight(indices=list(range(start, start + len(sub))), highlight_type="compare")],
                comparisons=_state["comparisons"],
                swaps=_state["swaps"],
            ))

            left = _merge_sort(sub[:mid], start)
            right = _merge_sort(sub[mid:], start + mid)

            # 合并
            merged = []
            i = j = 0
            while i < len(left) and j < len(right):
                _state["comparisons"] += 1
                if left[i] <= right[j]:
                    merged.append(left[i])
                    i += 1
                else:
                    merged.append(right[j])
                    j += 1
                    _state["swaps"] += 1

            merged.extend(left[i:])
            merged.extend(right[j:])

            # 更新原数组
            for k, val in enumerate(merged):
                arr[start + k] = val

            steps.append(AlgorithmStep(
                step_number=len(steps),
                description=f"合并: [{start}..{start + len(merged) - 1}] → {merged}",
                array_state=arr.copy(),
                highlights=[StepHighlight(indices=list(range(start, start + len(merged))), highlight_type="current")],
                comparisons=_state["comparisons"],
                swaps=_state["swaps"],
            ))

            return merged

        _merge_sort(arr, 0)

        steps.append(AlgorithmStep(
            step_number=len(steps),
            description=f"排序完成: {arr}",
            array_state=arr.copy(),
            highlights=[StepHighlight(indices=list(range(len(arr))), highlight_type="sorted")],
            comparisons=_state["comparisons"],
            swaps=_state["swaps"],
        ))

        return steps

    def _trace_insertion_sort(self, data: list[int]) -> list[AlgorithmStep]:
        """插入排序步骤追踪"""
        arr = data.copy()
        steps: list[AlgorithmStep] = []
        total_comparisons = 0
        total_swaps = 0

        steps.append(AlgorithmStep(
            step_number=0,
            description=f"初始数组: {arr}",
            array_state=arr.copy(),
            highlights=[],
            comparisons=0,
            swaps=0,
        ))

        for i in range(1, len(arr)):
            key = arr[i]
            j = i - 1

            steps.append(AlgorithmStep(
                step_number=len(steps),
                description=f"取出 arr[{i}]={key}，准备插入已排序部分",
                array_state=arr.copy(),
                highlights=[StepHighlight(indices=[i], highlight_type="current")],
                comparisons=total_comparisons,
                swaps=total_swaps,
            ))

            while j >= 0 and arr[j] > key:
                total_comparisons += 1
                arr[j + 1] = arr[j]
                total_swaps += 1
                steps.append(AlgorithmStep(
                    step_number=len(steps),
                    description=f"arr[{j}]={arr[j]} > {key}，右移到 arr[{j+1}]",
                    array_state=arr.copy(),
                    highlights=[StepHighlight(indices=[j, j + 1], highlight_type="swap")],
                    comparisons=total_comparisons,
                    swaps=total_swaps,
                ))
                j -= 1

            if j >= 0:
                total_comparisons += 1

            arr[j + 1] = key
            steps.append(AlgorithmStep(
                step_number=len(steps),
                description=f"将 {key} 插入到位置 arr[{j+1}]",
                array_state=arr.copy(),
                highlights=[StepHighlight(indices=[j + 1], highlight_type="current")],
                comparisons=total_comparisons,
                swaps=total_swaps,
            ))

        steps.append(AlgorithmStep(
            step_number=len(steps),
            description=f"排序完成: {arr}",
            array_state=arr.copy(),
            highlights=[StepHighlight(indices=list(range(len(arr))), highlight_type="sorted")],
            comparisons=total_comparisons,
            swaps=total_swaps,
        ))

        return steps

    def _trace_selection_sort(self, data: list[int]) -> list[AlgorithmStep]:
        """选择排序步骤追踪"""
        arr = data.copy()
        steps: list[AlgorithmStep] = []
        total_comparisons = 0
        total_swaps = 0

        steps.append(AlgorithmStep(
            step_number=0,
            description=f"初始数组: {arr}",
            array_state=arr.copy(),
            highlights=[],
            comparisons=0,
            swaps=0,
        ))

        n = len(arr)
        for i in range(n - 1):
            min_idx = i
            steps.append(AlgorithmStep(
                step_number=len(steps),
                description=f"第{i+1}轮：从 arr[{i}] 开始找最小值",
                array_state=arr.copy(),
                highlights=[StepHighlight(indices=[i], highlight_type="current")],
                comparisons=total_comparisons,
                swaps=total_swaps,
            ))

            for j in range(i + 1, n):
                total_comparisons += 1
                steps.append(AlgorithmStep(
                    step_number=len(steps),
                    description=f"比较 arr[{min_idx}]={arr[min_idx]} 和 arr[{j}]={arr[j]}",
                    array_state=arr.copy(),
                    highlights=[StepHighlight(indices=[min_idx, j], highlight_type="compare")],
                    comparisons=total_comparisons,
                    swaps=total_swaps,
                ))

                if arr[j] < arr[min_idx]:
                    min_idx = j

            if min_idx != i:
                arr[i], arr[min_idx] = arr[min_idx], arr[i]
                total_swaps += 1
                steps.append(AlgorithmStep(
                    step_number=len(steps),
                    description=f"交换 arr[{i}] 和 arr[{min_idx}]",
                    array_state=arr.copy(),
                    highlights=[StepHighlight(indices=[i, min_idx], highlight_type="swap")],
                    comparisons=total_comparisons,
                    swaps=total_swaps,
                ))

        steps.append(AlgorithmStep(
            step_number=len(steps),
            description=f"排序完成: {arr}",
            array_state=arr.copy(),
            highlights=[StepHighlight(indices=list(range(n)), highlight_type="sorted")],
            comparisons=total_comparisons,
            swaps=total_swaps,
        ))

        return steps

    def _trace_heap_sort(self, data: list[int]) -> list[AlgorithmStep]:
        """堆排序步骤追踪"""
        arr = data.copy()
        steps: list[AlgorithmStep] = []
        _state = {"comparisons": 0, "swaps": 0}

        steps.append(AlgorithmStep(
            step_number=0,
            description=f"初始数组: {arr}",
            array_state=arr.copy(),
            highlights=[],
            comparisons=0,
            swaps=0,
        ))

        def _sift_down(n: int, i: int) -> None:
            largest = i
            left = 2 * i + 1
            right = 2 * i + 2

            if left < n:
                _state["comparisons"] += 1
                if arr[left] > arr[largest]:
                    largest = left

            if right < n:
                _state["comparisons"] += 1
                if arr[right] > arr[largest]:
                    largest = right

            if largest != i:
                arr[i], arr[largest] = arr[largest], arr[i]
                _state["swaps"] += 1
                steps.append(AlgorithmStep(
                    step_number=len(steps),
                    description=f"下沉: 交换 arr[{i}]={arr[largest]} 和 arr[{largest}]={arr[i]}",
                    array_state=arr.copy(),
                    highlights=[StepHighlight(indices=[i, largest], highlight_type="swap")],
                    comparisons=_state["comparisons"],
                    swaps=_state["swaps"],
                ))
                _sift_down(n, largest)

        # 建堆
        n = len(arr)
        steps.append(AlgorithmStep(
            step_number=len(steps),
            description="开始建最大堆",
            array_state=arr.copy(),
            highlights=[],
            comparisons=_state["comparisons"],
            swaps=_state["swaps"],
        ))

        for i in range(n // 2 - 1, -1, -1):
            _sift_down(n, i)

        steps.append(AlgorithmStep(
            step_number=len(steps),
            description=f"最大堆建立完成: {arr}",
            array_state=arr.copy(),
            highlights=[StepHighlight(indices=[0], highlight_type="current")],
            comparisons=_state["comparisons"],
            swaps=_state["swaps"],
        ))

        # 逐个取出堆顶
        for i in range(n - 1, 0, -1):
            arr[0], arr[i] = arr[i], arr[0]
            _state["swaps"] += 1
            steps.append(AlgorithmStep(
                step_number=len(steps),
                description=f"将堆顶 arr[0]={arr[i]} 与 arr[{i}]={arr[0]} 交换",
                array_state=arr.copy(),
                highlights=[
                    StepHighlight(indices=[0, i], highlight_type="swap"),
                    StepHighlight(indices=list(range(i + 1, n)), highlight_type="sorted"),
                ],
                comparisons=_state["comparisons"],
                swaps=_state["swaps"],
            ))
            _sift_down(i, 0)

        steps.append(AlgorithmStep(
            step_number=len(steps),
            description=f"排序完成: {arr}",
            array_state=arr.copy(),
            highlights=[StepHighlight(indices=list(range(n)), highlight_type="sorted")],
            comparisons=_state["comparisons"],
            swaps=_state["swaps"],
        ))

        return steps

    def _trace_bst_insert(self, data: list[int]) -> list[TreeAlgorithmStep]:
        """BST插入步骤追踪"""
        steps: list[TreeAlgorithmStep] = []
        # 用简单的树结构模拟
        nodes: list[TreeNodeState] = []

        steps.append(TreeAlgorithmStep(
            step_number=0,
            description="空BST，准备插入",
            tree_state=[],
            highlighted_node=None,
        ))

        for val in data:
            if not nodes:
                nodes.append(TreeNodeState(value=val, left=None, right=None, highlighted=True))
                steps.append(TreeAlgorithmStep(
                    step_number=len(steps),
                    description=f"插入 {val} 作为根节点",
                    tree_state=copy.deepcopy(nodes),
                    highlighted_node=0,
                ))
                nodes[0].highlighted = False
                continue

            # 查找插入位置
            curr_idx = 0
            while True:
                curr_val = nodes[curr_idx].value
                steps.append(TreeAlgorithmStep(
                    step_number=len(steps),
                    description=f"插入 {val}：比较 {val} 与 {curr_val}",
                    tree_state=copy.deepcopy(nodes),
                    highlighted_node=curr_idx,
                ))

                if val < curr_val:
                    if nodes[curr_idx].left is None:
                        new_idx = len(nodes)
                        nodes[curr_idx].left = new_idx
                        nodes.append(TreeNodeState(value=val, left=None, right=None, highlighted=True))
                        steps.append(TreeAlgorithmStep(
                            step_number=len(steps),
                            description=f"{val} < {curr_val}，插入为左子节点",
                            tree_state=copy.deepcopy(nodes),
                            highlighted_node=new_idx,
                        ))
                        nodes[new_idx].highlighted = False
                        break
                    else:
                        curr_idx = nodes[curr_idx].left
                else:
                    if nodes[curr_idx].right is None:
                        new_idx = len(nodes)
                        nodes[curr_idx].right = new_idx
                        nodes.append(TreeNodeState(value=val, left=None, right=None, highlighted=True))
                        steps.append(TreeAlgorithmStep(
                            step_number=len(steps),
                            description=f"{val} >= {curr_val}，插入为右子节点",
                            tree_state=copy.deepcopy(nodes),
                            highlighted_node=new_idx,
                        ))
                        nodes[new_idx].highlighted = False
                        break
                    else:
                        curr_idx = nodes[curr_idx].right

        steps.append(TreeAlgorithmStep(
            step_number=len(steps),
            description=f"BST插入完成，共插入 {len(data)} 个节点",
            tree_state=copy.deepcopy(nodes),
            highlighted_node=None,
        ))

        return steps

    def _trace_bst_search(self, data: list[int]) -> list[TreeAlgorithmStep]:
        """BST查找步骤追踪"""
        # 先构建BST
        nodes: list[TreeNodeState] = []
        for val in data:
            if not nodes:
                nodes.append(TreeNodeState(value=val, left=None, right=None))
                continue
            curr_idx = 0
            while True:
                if val < nodes[curr_idx].value:
                    if nodes[curr_idx].left is None:
                        new_idx = len(nodes)
                        nodes[curr_idx].left = new_idx
                        nodes.append(TreeNodeState(value=val, left=None, right=None))
                        break
                    curr_idx = nodes[curr_idx].left
                else:
                    if nodes[curr_idx].right is None:
                        new_idx = len(nodes)
                        nodes[curr_idx].right = new_idx
                        nodes.append(TreeNodeState(value=val, left=None, right=None))
                        break
                    curr_idx = nodes[curr_idx].right

        steps: list[TreeAlgorithmStep] = []

        steps.append(TreeAlgorithmStep(
            step_number=0,
            description=f"BST已构建，查找目标: {data[-1]}",
            tree_state=copy.deepcopy(nodes),
            highlighted_node=None,
        ))

        # 查找最后一个插入的值
        target = data[-1]
        curr_idx = 0
        while curr_idx is not None:
            curr_val = nodes[curr_idx].value
            if target == curr_val:
                nodes[curr_idx].highlighted = True
                steps.append(TreeAlgorithmStep(
                    step_number=len(steps),
                    description=f"找到目标 {target}，位于节点索引 {curr_idx}",
                    tree_state=copy.deepcopy(nodes),
                    highlighted_node=curr_idx,
                ))
                nodes[curr_idx].highlighted = False
                break
            elif target < curr_val:
                nodes[curr_idx].highlighted = True
                steps.append(TreeAlgorithmStep(
                    step_number=len(steps),
                    description=f"{target} < {curr_val}，向左子树查找",
                    tree_state=copy.deepcopy(nodes),
                    highlighted_node=curr_idx,
                ))
                nodes[curr_idx].highlighted = False
                curr_idx = nodes[curr_idx].left
            else:
                nodes[curr_idx].highlighted = True
                steps.append(TreeAlgorithmStep(
                    step_number=len(steps),
                    description=f"{target} > {curr_val}，向右子树查找",
                    tree_state=copy.deepcopy(nodes),
                    highlighted_node=curr_idx,
                ))
                nodes[curr_idx].highlighted = False
                curr_idx = nodes[curr_idx].right

        if curr_idx is None:
            steps.append(TreeAlgorithmStep(
                step_number=len(steps),
                description=f"未找到目标 {target}",
                tree_state=copy.deepcopy(nodes),
                highlighted_node=None,
            ))

        return steps

    # ============================================================
    # 4. 算法对比
    # ============================================================

    def get_algorithm_comparison(
        self,
        algorithm1: str,
        algorithm2: str,
        input_data: Optional[list[int]] = None,
    ) -> Optional[AlgorithmComparison]:
        """获取两个算法的对比数据

        Args:
            algorithm1: 第一个算法名称
            algorithm2: 第二个算法名称
            input_data: 共享输入数据

        Returns:
            AlgorithmComparison 或 None
        """
        supported = {"bubble_sort", "quick_sort", "merge_sort", "insertion_sort", "selection_sort", "heap_sort"}
        if algorithm1 not in supported or algorithm2 not in supported:
            logger.warning("不支持的算法对比: %s vs %s", algorithm1, algorithm2)
            return None

        data = input_data if input_data is not None else [5, 3, 8, 4, 2, 7, 1, 6]

        steps1 = self.get_time_machine_steps(algorithm1, data.copy())
        steps2 = self.get_time_machine_steps(algorithm2, data.copy())

        # 提取最终统计
        final1 = steps1[-1] if steps1 else AlgorithmStep(step_number=0, description="", array_state=[])
        final2 = steps2[-1] if steps2 else AlgorithmStep(step_number=0, description="", array_state=[])

        complexity_map = {
            "bubble_sort": "O(n²)",
            "quick_sort": "O(n log n)",
            "merge_sort": "O(n log n)",
            "insertion_sort": "O(n²)",
            "selection_sort": "O(n²)",
            "heap_sort": "O(n log n)",
        }

        return AlgorithmComparison(
            algorithm1_steps=steps1,
            algorithm2_steps=steps2,
            shared_input_data=data,
            comparison_metrics=ComparisonMetrics(
                algorithm1_comparisons=final1.comparisons,
                algorithm1_swaps=final1.swaps,
                algorithm1_time_complexity=complexity_map.get(algorithm1, ""),
                algorithm2_comparisons=final2.comparisons,
                algorithm2_swaps=final2.swaps,
                algorithm2_time_complexity=complexity_map.get(algorithm2, ""),
            ),
        )

    # ============================================================
    # 5. B站视频推荐
    # ============================================================

    def get_video_recommendations(
        self,
        knowledge_point: str,
        difficulty: Optional[str] = None,
    ) -> list[VideoRecommendation]:
        """获取B站视频推荐

        优先使用LLM动态生成推荐，降级使用基础模板。

        Args:
            knowledge_point: 知识点ID
            difficulty: 难度过滤 basic/intermediate/advanced

        Returns:
            视频推荐列表
        """
        # 尝试LLM动态生成推荐
        try:
            videos = self._generate_video_recommendations_with_llm(knowledge_point, difficulty)
            if videos:
                return videos
        except Exception as e:
            logger.warning("LLM视频推荐生成失败，降级为基础推荐: %s", e)

        # 降级：返回基础推荐
        node = get_knowledge_node(knowledge_point)
        name = node.name if node else knowledge_point
        return [
            VideoRecommendation(
                title=f"{name}详解 - B站搜索",
                url=f"https://search.bilibili.com/all?keyword={name}",
                duration="--",
                knowledge_points=[knowledge_point],
                difficulty=difficulty or "basic",
            )
        ]

    def _generate_video_recommendations_with_llm(
        self,
        knowledge_point: str,
        difficulty: Optional[str] = None,
    ) -> list[VideoRecommendation]:
        """使用LLM动态生成B站视频推荐"""
        node = get_knowledge_node(knowledge_point)
        name = node.name if node else knowledge_point

        diff_desc = {"basic": "入门基础", "intermediate": "进阶深入", "advanced": "高级挑战"}.get(difficulty or "", "通用")

        prompt = f"""请为知识点「{name}」推荐3-5个B站视频，以JSON格式输出。

要求：
1. 每个视频包含：title(标题), url(B站链接), duration(时长), difficulty(basic/intermediate/advanced)
2. 视频难度偏好：{diff_desc}
3. URL格式：https://www.bilibili.com/video/BVxxxxxx
4. 如果不确定真实BV号，使用搜索链接：https://search.bilibili.com/all?keyword=关键词
5. 只输出JSON数组，不要其他内容

示例格式：
[
  {{"title": "视频标题", "url": "https://www.bilibili.com/video/BVxxx", "duration": "15:30", "difficulty": "basic"}}
]"""

        result = llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        import json as _json
        try:
            parsed = _json.loads(result)
            items = parsed if isinstance(parsed, list) else parsed.get("videos", parsed.get("recommendations", []))
            videos = []
            for item in items[:5]:
                videos.append(VideoRecommendation(
                    title=item.get("title", name),
                    url=item.get("url", f"https://search.bilibili.com/all?keyword={name}"),
                    duration=item.get("duration", "--"),
                    knowledge_points=[knowledge_point],
                    difficulty=item.get("difficulty", difficulty or "basic"),
                ))
            return videos
        except (_json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("解析LLM视频推荐失败: %s", e)
            return []

    # ============================================================
    # 6. 云视频共享
    # ============================================================

    def get_cloud_videos(
        self,
        knowledge_point: Optional[str] = None,
        sort_by: str = "rating",
        db: "Session" = None,
    ) -> list[CloudVideo]:
        """获取云视频列表 - 查询MySQL

        Args:
            knowledge_point: 按知识点过滤，None表示全部
            sort_by: 排序方式 rating/newest
            db: 数据库session（可选）

        Returns:
            云视频列表
        """
        from app.core.database import SessionLocal

        if db is None:
            db = SessionLocal()

        try:
            return self._get_cloud_videos_db(db, knowledge_point, sort_by)
        except Exception as e:
            logger.warning("MySQL云视频查询失败: %s", e)
            return []

    def _get_cloud_videos_db(self, db: "Session", knowledge_point: Optional[str], sort_by: str) -> list[CloudVideo]:
        """从MySQL获取云视频"""
        from app.models.profile import CloudVideoModel
        import json as _json

        query = db.query(CloudVideoModel)
        if knowledge_point:
            query = query.filter(CloudVideoModel.knowledge_point == knowledge_point)

        if sort_by == "rating":
            query = query.order_by(CloudVideoModel.rating.desc())
        elif sort_by == "newest":
            query = query.order_by(CloudVideoModel.created_at.desc())

        models = query.all()
        return [
            CloudVideo(
                video_id=m.video_id,
                title=m.title,
                url=m.url,
                knowledge_point=m.knowledge_point,
                uploaded_by=m.uploaded_by,
                rating=m.rating,
                rating_count=m.rating_count,
                tags=_json.loads(m.tags_json) if m.tags_json else [],
                created_at=m.created_at.isoformat() if m.created_at else "",
            )
            for m in models
        ]

    def add_cloud_video(
        self,
        title: str,
        url: str,
        knowledge_point: str,
        uploaded_by: str = "",
        tags: Optional[list[str]] = None,
        db: "Session" = None,
    ) -> CloudVideo:
        """添加云视频 - 写入MySQL

        Args:
            title: 视频标题
            url: 视频链接
            knowledge_point: 关联知识点
            uploaded_by: 上传者
            tags: 标签列表
            db: 数据库session（可选）

        Returns:
            新创建的CloudVideo
        """
        import json as _json
        from app.core.database import SessionLocal

        if db is None:
            db = SessionLocal()

        video_id = str(uuid.uuid4())[:8]
        video = CloudVideo(
            video_id=video_id,
            title=title,
            url=url,
            knowledge_point=knowledge_point,
            uploaded_by=uploaded_by,
            tags=tags or [],
        )

        # 写入MySQL
        try:
            from app.models.profile import CloudVideoModel
            model = CloudVideoModel(
                video_id=video_id,
                title=title,
                url=url,
                knowledge_point=knowledge_point,
                uploaded_by=uploaded_by,
                tags_json=_json.dumps(tags or [], ensure_ascii=False),
            )
            db.add(model)
            db.commit()
        except Exception as e:
            logger.warning("MySQL云视频写入失败: %s", e)
            db.rollback()

        logger.info("添加云视频: %s (%s)", title, video_id)
        return video

    def rate_video(
        self,
        video_id: str,
        rating: int,
        tags: Optional[list[str]] = None,
        user_id: str = "",
        db: "Session" = None,
    ) -> Optional[CloudVideo]:
        """为云视频评分 - 写入MySQL

        Args:
            video_id: 视频ID
            rating: 评分 1-5
            tags: 评价标签
            user_id: 评分用户
            db: 数据库session（可选）

        Returns:
            更新后的CloudVideo 或 None
        """
        import json as _json
        from app.core.database import SessionLocal

        if db is None:
            db = SessionLocal()

        rating = max(1, min(5, rating))

        try:
            from app.models.profile import CloudVideoModel, VideoRatingModel
            video_model = db.query(CloudVideoModel).filter(CloudVideoModel.video_id == video_id).first()
            if not video_model:
                logger.warning("视频不存在(MySQL): %s", video_id)
                return None

            # 记录评分
            rating_model = VideoRatingModel(
                video_id=video_id,
                user_id=user_id,
                rating=rating,
                tags_json=_json.dumps(tags or [], ensure_ascii=False),
            )
            db.add(rating_model)

            # 更新平均评分
            all_ratings = db.query(VideoRatingModel).filter(VideoRatingModel.video_id == video_id).all()
            avg = sum(r.rating for r in all_ratings) / len(all_ratings)
            video_model.rating = round(avg, 1)
            video_model.rating_count = len(all_ratings)

            # 合并标签
            if tags:
                existing_tags = set(_json.loads(video_model.tags_json)) if video_model.tags_json else set()
                video_model.tags_json = _json.dumps(list(existing_tags | set(tags)), ensure_ascii=False)

            db.commit()

            return CloudVideo(
                video_id=video_id,
                title=video_model.title,
                url=video_model.url,
                knowledge_point=video_model.knowledge_point,
                uploaded_by=video_model.uploaded_by,
                rating=video_model.rating,
                rating_count=video_model.rating_count,
                tags=_json.loads(video_model.tags_json) if video_model.tags_json else [],
                created_at=video_model.created_at.isoformat() if video_model.created_at else "",
            )

        except Exception as e:
            logger.warning("MySQL视频评分失败: %s", e)
            db.rollback()

        return None

    def get_recommended_cloud_videos(
        self,
        profile: StudentProfile,
        limit: int = 5,
    ) -> list[CloudVideo]:
        """基于学生画像推荐云视频

        根据薄弱环节和认知风格推荐相关视频

        Args:
            profile: 学生画像
            limit: 返回数量上限

        Returns:
            推荐视频列表
        """
        all_videos = self.get_cloud_videos()
        if not all_videos:
            return []

        # 根据薄弱环节优先推荐
        weak_points = [wp.knowledge_point for wp in profile.weak_points]
        scored_videos: list[tuple[float, CloudVideo]] = []

        for video in all_videos:
            score = video.rating  # 基础分：评分

            # 薄弱环节匹配加分
            if video.knowledge_point in weak_points:
                score += 3.0

            # 认知风格匹配
            if profile.cognitive_style == CognitiveStyle.VISUAL:
                # 视觉型偏好有演示的视频
                if "演示" in video.title or "动画" in video.title or "可视化" in video.title:
                    score += 1.5
            elif profile.cognitive_style == CognitiveStyle.PRACTICAL:
                # 实践型偏好有代码的视频
                if "代码" in video.title or "实现" in video.title or "编程" in video.title:
                    score += 1.5

            # 难度匹配
            difficulty_tags = video.tags
            if profile.difficulty_level == DifficultyLevel.BASIC and "基础" in difficulty_tags:
                score += 1.0
            elif profile.difficulty_level == DifficultyLevel.INTERMEDIATE and "进阶" in difficulty_tags:
                score += 1.0
            elif profile.difficulty_level == DifficultyLevel.ADVANCED and "挑战" in difficulty_tags:
                score += 1.0

            scored_videos.append((score, video))

        scored_videos.sort(key=lambda x: x[0], reverse=True)
        return [v for _, v in scored_videos[:limit]]

    # ============================================================
    # 7. 代码可视化
    # ============================================================

    def get_code_visualization(
        self,
        code: str,
        language: str = "python",
        input_data: Optional[dict] = None,
    ) -> CodeVisualizationConfig:
        """获取代码执行可视化配置

        定义前端可渲染的代码执行步骤schema

        Args:
            code: 学生提交的代码
            language: 编程语言
            input_data: 输入数据

        Returns:
            CodeVisualizationConfig
        """
        # 尝试LLM分析代码生成执行步骤，失败则返回基础配置
        try:
            return self._generate_code_visualization_with_llm(code, language, input_data)
        except Exception as e:
            logger.warning("LLM代码可视化生成失败，降级为基础配置: %s", e)
            return CodeVisualizationConfig(
                code=code,
                language=language,
                steps=[],
                total_steps=0,
            )

    def _generate_code_visualization_with_llm(
        self,
        code: str,
        language: str,
        input_data: Optional[dict],
    ) -> CodeVisualizationConfig:
        """使用LLM生成代码执行步骤"""
        input_desc = f"输入数据: {input_data}" if input_data else "无特定输入数据"

        prompt = f"""请分析以下{language}代码，生成逐步执行追踪。

代码：
```{language}
{code}
```

{input_desc}

请用JSON格式输出执行步骤，格式如下：
{{
  "steps": [
    {{
      "line_number": 1,
      "description": "执行了什么操作",
      "variables": {{"变量名": "当前值"}},
      "output": "该步产生的输出（如有）",
      "call_stack": ["函数调用栈"]
    }}
  ]
}}

要求：
1. 每个有意义的执行步骤都要记录
2. variables记录该步执行后所有可见变量的状态
3. call_stack记录当前函数调用栈
4. 最多生成30步
5. 只输出JSON，不要其他内容"""

        result = llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )

        import json
        try:
            parsed = json.loads(result)
            steps_data = parsed.get("steps", [])
            steps = []
            for i, s in enumerate(steps_data):
                steps.append(CodeVisualizationStep(
                    line_number=s.get("line_number", 0),
                    description=s.get("description", ""),
                    variables=s.get("variables", {}),
                    output=s.get("output", ""),
                    call_stack=s.get("call_stack", []),
                ))
            return CodeVisualizationConfig(
                code=code,
                language=language,
                steps=steps,
                total_steps=len(steps),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("解析代码可视化步骤失败: %s", e)
            return CodeVisualizationConfig(
                code=code,
                language=language,
                steps=[],
                total_steps=0,
            )


# 全局单例
multimodal_service = MultimodalService()
