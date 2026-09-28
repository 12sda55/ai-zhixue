"""知识点依赖图 - 对照 ai_architecture_plan.md 设计

数据结构与算法课程的30个知识点依赖关系
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class KnowledgeNodeDef(BaseModel):
    """知识点定义"""
    id: str                          # 唯一标识，如 "bst"
    name: str                        # 中文名，如 "二叉搜索树"
    category: str                    # 分类，如 "树结构"
    dependencies: list[str] = Field(default_factory=list)  # 前置知识点ID
    optional: bool = False           # 是否可选（如红黑树）
    description: str = ""


# ===== 完整知识点依赖图 =====

KNOWLEDGE_GRAPH: list[KnowledgeNodeDef] = [
    # === 线性结构 ===
    KnowledgeNodeDef(id="array", name="数组", category="线性结构", dependencies=[]),
    KnowledgeNodeDef(id="linked_list", name="链表", category="线性结构", dependencies=["array"]),
    KnowledgeNodeDef(id="stack", name="栈", category="线性结构", dependencies=["linked_list"]),
    KnowledgeNodeDef(id="queue", name="队列", category="线性结构", dependencies=["linked_list"]),
    KnowledgeNodeDef(id="deque", name="双端队列", category="线性结构", dependencies=["queue"]),
    KnowledgeNodeDef(id="string", name="串", category="线性结构", dependencies=["array"]),

    # === 哈希 ===
    KnowledgeNodeDef(id="hash_table", name="哈希表", category="哈希", dependencies=["array", "linked_list"]),

    # === 树结构 ===
    KnowledgeNodeDef(id="binary_tree", name="二叉树", category="树结构", dependencies=["linked_list"]),
    KnowledgeNodeDef(id="bst", name="二叉搜索树", category="树结构", dependencies=["binary_tree"]),
    KnowledgeNodeDef(id="avl", name="AVL树", category="树结构", dependencies=["bst"]),
    KnowledgeNodeDef(id="red_black_tree", name="红黑树", category="树结构", dependencies=["avl"], optional=True),
    KnowledgeNodeDef(id="heap", name="堆", category="树结构", dependencies=["binary_tree"]),
    KnowledgeNodeDef(id="b_tree", name="B树", category="树结构", dependencies=["bst"], optional=True),

    # === 图结构 ===
    KnowledgeNodeDef(id="graph_basics", name="图的基本概念", category="图结构", dependencies=[]),
    KnowledgeNodeDef(id="graph_traversal", name="图的遍历(BFS/DFS)", category="图结构", dependencies=["graph_basics", "stack", "queue"]),
    KnowledgeNodeDef(id="topological_sort", name="拓扑排序", category="图结构", dependencies=["graph_traversal"]),
    KnowledgeNodeDef(id="shortest_path", name="最短路径", category="图结构", dependencies=["graph_traversal", "heap"]),
    KnowledgeNodeDef(id="mst", name="最小生成树", category="图结构", dependencies=["graph_traversal", "heap"]),

    # === 排序 ===
    KnowledgeNodeDef(id="bubble_sort", name="冒泡排序", category="排序", dependencies=["array"]),
    KnowledgeNodeDef(id="selection_sort", name="选择排序", category="排序", dependencies=["array"]),
    KnowledgeNodeDef(id="insertion_sort", name="插入排序", category="排序", dependencies=["array"]),
    KnowledgeNodeDef(id="shell_sort", name="希尔排序", category="排序", dependencies=["insertion_sort"], optional=True),
    KnowledgeNodeDef(id="quick_sort", name="快速排序", category="排序", dependencies=["array", "recursion"]),
    KnowledgeNodeDef(id="merge_sort", name="归并排序", category="排序", dependencies=["array", "recursion"]),
    KnowledgeNodeDef(id="heap_sort", name="堆排序", category="排序", dependencies=["heap"]),
    KnowledgeNodeDef(id="radix_sort", name="基数排序", category="排序", dependencies=["queue"], optional=True),

    # === 查找 ===
    KnowledgeNodeDef(id="sequential_search", name="顺序查找", category="查找", dependencies=["array"]),
    KnowledgeNodeDef(id="binary_search", name="二分查找", category="查找", dependencies=["array"]),
    KnowledgeNodeDef(id="bst_search", name="BST查找", category="查找", dependencies=["bst"]),

    # === 基础概念 ===
    KnowledgeNodeDef(id="recursion", name="递归", category="基础", dependencies=[]),
    KnowledgeNodeDef(id="complexity", name="算法复杂度分析", category="基础", dependencies=[]),
]


def get_knowledge_node(node_id: str) -> Optional[KnowledgeNodeDef]:
    """根据ID获取知识点定义"""
    for node in KNOWLEDGE_GRAPH:
        if node.id == node_id:
            return node
    return None


def get_dependencies(node_id: str) -> list[str]:
    """获取直接前置依赖"""
    node = get_knowledge_node(node_id)
    return node.dependencies if node else []


def get_all_dependents(node_id: str) -> list[str]:
    """获取所有后续依赖该知识点的节点"""
    dependents = []
    for node in KNOWLEDGE_GRAPH:
        if node_id in node.dependencies:
            dependents.append(node.id)
            dependents.extend(get_all_dependents(node.id))
    return list(set(dependents))


def get_topological_order() -> list[str]:
    """拓扑排序 - 返回合法的学习顺序"""
    in_degree = {node.id: len(node.dependencies) for node in KNOWLEDGE_GRAPH}
    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    result = []

    while queue:
        current = queue.pop(0)
        result.append(current)
        for node in KNOWLEDGE_GRAPH:
            if current in node.dependencies:
                in_degree[node.id] -= 1
                if in_degree[node.id] == 0:
                    queue.append(node.id)

    return result


def get_categories() -> dict[str, list[str]]:
    """按分类获取知识点"""
    categories: dict[str, list[str]] = {}
    for node in KNOWLEDGE_GRAPH:
        if node.category not in categories:
            categories[node.category] = []
        categories[node.category].append(node.id)
    return categories
