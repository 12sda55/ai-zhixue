"""知识库文本 - 31个知识点的教学内容

每个知识点包含：概念讲解、核心原理、代码示例、常见误区、应用场景
用于ChromaDB向量化存储和RAG检索
"""

from __future__ import annotations

KNOWLEDGE_TEXTS = {
    "array": """# 数组

## 概念
数组是一种线性数据结构，用连续的内存空间存储相同类型的数据元素。通过索引（下标）可以直接访问任意元素，访问时间复杂度为O(1)。

## 核心原理
- **连续存储**：元素在内存中紧密排列，通过首地址+偏移量计算任意元素地址
- **随机访问**：通过索引直接定位，时间O(1)
- **插入/删除代价高**：需要移动后续元素，平均O(n)

## Python示例
```python
# 数组基本操作
arr = [3, 1, 4, 1, 5, 9, 2, 6]

# 访问元素 O(1)
print(arr[0])  # 3

# 尾部插入 O(1) amortized
arr.append(7)

# 中间插入 O(n)
arr.insert(2, 99)  # 在索引2处插入

# 删除 O(n)
arr.pop(2)  # 删除索引2的元素

# 遍历 O(n)
for x in arr:
    print(x)
```

## 常见误区
1. 混淆数组的"逻辑大小"和"物理容量"
2. 认为数组插入总是O(n)——尾部插入是O(1)均摊
3. 忽略数组越界访问的危险

## 应用场景
- 需要频繁随机访问的场景
- 数据量已知且变化不大
- 实现其他数据结构（栈、队列、堆）的底层存储
""",

    "linked_list": """# 链表

## 概念
链表是一种线性数据结构，每个节点包含数据域和指针域。节点在内存中不必连续存储，通过指针链接。分为单链表、双链表、循环链表。

## 核心原理
- **非连续存储**：节点分散在内存中，通过指针连接
- **插入/删除高效**：只需修改指针，O(1)（已知位置时）
- **访问需遍历**：无法随机访问，查找O(n)

## Python示例
```python
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

# 创建链表: 1 -> 2 -> 3
head = ListNode(1, ListNode(2, ListNode(3)))

# 遍历链表
def traverse(head):
    curr = head
    while curr:
        print(curr.val)
        curr = curr.next

# 头部插入 O(1)
new_node = ListNode(0, head)
head = new_node

# 删除节点（已知前驱）O(1)
# prev.next = prev.next.next
```

## 常见误区
1. 忘记处理头节点和尾节点的特殊情况
2. 删除节点时丢失引用导致内存泄漏
3. 混淆单链表和双链表的操作差异

## 与数组对比
| 操作 | 数组 | 链表 |
|------|------|------|
| 访问 | O(1) | O(n) |
| 插入 | O(n) | O(1) |
| 删除 | O(n) | O(1) |
| 空间 | 紧凑 | 额外指针开销 |
""",

    "stack": """# 栈

## 概念
栈是一种后进先出（LIFO）的线性数据结构。只允许在栈顶进行插入（push）和删除（pop）操作。

## 核心原理
- **LIFO原则**：最后入栈的元素最先出栈
- **只操作栈顶**：push入栈、pop出栈、peek查看栈顶
- **时间复杂度**：push/pop/peek均为O(1)

## Python示例
```python
# 用列表实现栈
stack = []

# 入栈
stack.append(1)
stack.append(2)
stack.append(3)  # stack = [1, 2, 3]

# 出栈
top = stack.pop()  # top = 3, stack = [1, 2]

# 查看栈顶
peek = stack[-1]  # peek = 2

# 判空
is_empty = len(stack) == 0
```

## 经典应用
1. **括号匹配**：检查表达式中的括号是否配对
2. **函数调用栈**：递归调用的底层实现
3. **表达式求值**：中缀转后缀，后缀求值
4. **浏览器前进/后退**：两个栈实现
5. **撤销操作**：Ctrl+Z的底层原理

## 括号匹配示例
```python
def is_valid(s: str) -> bool:
    stack = []
    pairs = {')': '(', ']': '[', '}': '{'}
    for ch in s:
        if ch in '([{':
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack
```
""",

    "queue": """# 队列

## 概念
队列是一种先进先出（FIFO）的线性数据结构。在队尾入队（enqueue），在队头出队（dequeue）。

## 核心原理
- **FIFO原则**：先入队的元素先出队
- **两端操作**：队尾入队，队头出队
- **时间复杂度**：enqueue/dequeue均为O(1)

## Python示例
```python
from collections import deque

# 用deque实现队列（列表pop(0)是O(n)）
queue = deque()

# 入队
queue.append(1)
queue.append(2)
queue.append(3)  # queue = deque([1, 2, 3])

# 出队
front = queue.popleft()  # front = 1

# 查看队头
peek = queue[0]  # peek = 2

# 判空
is_empty = len(queue) == 0
```

## 经典应用
1. **BFS广度优先搜索**：图的层序遍历
2. **任务调度**：先来先服务
3. **消息队列**：生产者-消费者模式
4. **缓冲区管理**：打印队列、请求队列
""",

    "recursion": """# 递归

## 概念
递归是函数直接或间接调用自身的编程技巧。将大问题分解为相同结构的子问题，直到达到最小问题（基准条件）。

## 核心原理
1. **基准条件**：递归终止的条件，必须有
2. **递归步骤**：将问题规模缩小，向基准条件靠近
3. **调用栈**：每次递归调用在栈上分配新帧

## Python示例
```python
# 阶乘
def factorial(n):
    if n <= 1:  # 基准条件
        return 1
    return n * factorial(n - 1)  # 递归步骤

# 斐波那契数列（朴素递归，效率低）
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)

# 斐波那契（带记忆化，效率高）
from functools import lru_cache
@lru_cache
def fib_memo(n):
    if n <= 1:
        return n
    return fib_memo(n-1) + fib_memo(n-2)
```

## 常见误区
1. 忘记基准条件 → 无限递归 → 栈溢出
2. 递归步骤没有缩小问题规模
3. 重复计算（如朴素斐波那契）→ 用记忆化优化
4. 递归深度过大 → 改用迭代

## 递归 vs 迭代
- 递归代码简洁，但空间开销大（调用栈）
- 迭代效率高，但代码可能复杂
- 所有递归都可以转为迭代
""",

    "complexity": """# 算法复杂度分析

## 概念
算法复杂度用于衡量算法的运行效率，包括时间复杂度（执行速度）和空间复杂度（内存占用）。用大O表示法描述增长趋势。

## 核心原理
- **大O表示法**：描述上界，忽略常数和低阶项
- **时间复杂度**：基本操作执行次数与输入规模的关系
- **空间复杂度**：额外内存与输入规模的关系

## 常见复杂度
| 复杂度 | 名称 | 典型算法 |
|--------|------|----------|
| O(1) | 常数 | 数组访问、哈希查找 |
| O(log n) | 对数 | 二分查找 |
| O(n) | 线性 | 遍历数组 |
| O(n log n) | 线性对数 | 归并排序、快排 |
| O(n²) | 平方 | 冒泡排序、选择排序 |
| O(2^n) | 指数 | 穷举子集 |

## 分析技巧
1. **看循环**：单层循环O(n)，嵌套循环O(n²)
2. **看递归**：主定理分析
3. **最好/最坏/平均**：关注最坏情况
4. **均摊分析**：动态数组扩容的append是O(1)均摊

## 示例
```python
# O(n) - 单层循环
def find_max(arr):
    max_val = arr[0]
    for x in arr:
        if x > max_val:
            max_val = x
    return max_val

# O(n²) - 嵌套循环
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(n-1-i):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]

# O(log n) - 每次减半
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```
""",

    "binary_tree": """# 二叉树

## 概念
二叉树是每个节点最多有两个子节点（左子节点和右子节点）的树结构。是树结构中最基础、最重要的形式。

## 核心概念
- **根节点**：树的最顶层节点
- **叶子节点**：没有子节点的节点
- **深度**：从根到该节点的边数
- **高度**：从该节点到最远叶子的边数
- **满二叉树**：所有非叶节点都有2个子节点
- **完全二叉树**：除最后一层外全满，最后一层从左到右连续

## Python示例
```python
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

# 构建二叉树
#       1
#      / \\
#     2   3
#    / \\
#   4   5
root = TreeNode(1,
    TreeNode(2, TreeNode(4), TreeNode(5)),
    TreeNode(3))

# 三种遍历
def preorder(root):  # 前序：根-左-右
    if not root: return []
    return [root.val] + preorder(root.left) + preorder(root.right)

def inorder(root):   # 中序：左-根-右
    if not root: return []
    return inorder(root.left) + [root.val] + inorder(root.right)

def postorder(root): # 后序：左-右-根
    if not root: return []
    return postorder(root.left) + postorder(root.right) + [root.val]

# 层序遍历（BFS）
from collections import deque
def levelorder(root):
    if not root: return []
    result, queue = [], deque([root])
    while queue:
        node = queue.popleft()
        result.append(node.val)
        if node.left: queue.append(node.left)
        if node.right: queue.append(node.right)
    return result
```
""",

    "bst": """# 二叉搜索树（BST）

## 概念
二叉搜索树是一种特殊的二叉树，满足：左子树所有节点值 < 根节点值 < 右子树所有节点值。中序遍历BST得到有序序列。

## 核心操作
- **查找**：从根开始，比当前小往左，比当前大往右，平均O(log n)
- **插入**：找到合适位置插入新叶节点
- **删除**：三种情况——叶节点直接删、单子节点替代、找后继替代

## Python示例
```python
class BSTNode:
    def __init__(self, val):
        self.val = val
        self.left = None
        self.right = None

class BST:
    def __init__(self):
        self.root = None

    def search(self, val):
        curr = self.root
        while curr:
            if val == curr.val: return curr
            elif val < curr.val: curr = curr.left
            else: curr = curr.right
        return None

    def insert(self, val):
        if not self.root:
            self.root = BSTNode(val)
            return
        curr = self.root
        while True:
            if val < curr.val:
                if not curr.left:
                    curr.left = BSTNode(val)
                    return
                curr = curr.left
            else:
                if not curr.right:
                    curr.right = BSTNode(val)
                    return
                curr = curr.right

    def inorder(self):
        result = []
        def dfs(node):
            if node:
                dfs(node.left)
                result.append(node.val)
                dfs(node.right)
        dfs(self.root)
        return result
```

## 常见误区
1. BST最坏情况退化为链表，查找O(n)
2. 删除节点时忘记处理两个子节点的情况
3. 插入重复值的处理策略不明确

## 性能
| 操作 | 平均 | 最坏 |
|------|------|------|
| 查找 | O(log n) | O(n) |
| 插入 | O(log n) | O(n) |
| 删除 | O(log n) | O(n) |
""",

    "hash_table": """# 哈希表

## 概念
哈希表通过哈希函数将键映射到数组下标，实现近O(1)的查找、插入和删除。是最高效的键值存储结构。

## 核心原理
1. **哈希函数**：将键转换为数组下标 hash(key) % size
2. **冲突处理**：不同键映射到同一位置
   - 链地址法：每个桶存链表
   - 开放寻址法：找下一个空位
3. **负载因子**：元素数/桶数，超过阈值需扩容

## Python示例
```python
# Python字典就是哈希表
d = {}
d['name'] = 'Alice'
d['age'] = 20
print(d['name'])  # O(1)平均

# 手动实现简单哈希表（链地址法）
class SimpleHashTable:
    def __init__(self, size=16):
        self.size = size
        self.buckets = [[] for _ in range(size)]

    def _hash(self, key):
        return hash(key) % self.size

    def put(self, key, value):
        idx = self._hash(key)
        for i, (k, v) in enumerate(self.buckets[idx]):
            if k == key:
                self.buckets[idx][i] = (key, value)
                return
        self.buckets[idx].append((key, value))

    def get(self, key):
        idx = self._hash(key)
        for k, v in self.buckets[idx]:
            if k == key:
                return v
        return None
```

## 经典应用
1. **两数之和**：用哈希表记录已遍历的数
2. **字符频率统计**：计数器
3. **去重**：集合的底层实现
4. **缓存**：LRU Cache
""",

    "bubble_sort": """# 冒泡排序

## 概念
冒泡排序通过重复遍历列表，比较相邻元素并交换，使较大元素逐渐"冒泡"到末尾。是最简单的排序算法。

## 核心原理
- 每轮遍历将最大元素移到未排序部分末尾
- 优化：如果某轮没有交换，说明已有序，提前终止

## Python示例
```python
def bubble_sort(arr):
    n = len(arr)
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:  # 提前终止
            break
    return arr

print(bubble_sort([5, 3, 8, 4, 2]))  # [2, 3, 4, 5, 8]
```

## 复杂度
| 情况 | 时间 | 说明 |
|------|------|------|
| 最好 | O(n) | 已有序，一轮检测 |
| 最坏 | O(n²) | 逆序 |
| 平均 | O(n²) | |
| 空间 | O(1) | 原地排序 |
| 稳定性 | 稳定 | 相等元素不交换 |
""",

    "quick_sort": """# 快速排序

## 概念
快速排序采用分治策略：选一个基准值（pivot），将数组分为小于和大于pivot的两部分，递归排序。

## 核心原理
1. **选择基准**：通常选最后一个元素或随机选
2. **分区（Partition）**：小于pivot放左，大于放右
3. **递归排序**：对左右两部分递归

## Python示例
```python
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[-1]
    left = [x for x in arr[:-1] if x <= pivot]
    right = [x for x in arr[:-1] if x > pivot]
    return quick_sort(left) + [pivot] + quick_sort(right)

# 原地分区版本
def quick_sort_inplace(arr, lo=0, hi=None):
    if hi is None: hi = len(arr) - 1
    if lo >= hi: return
    pivot = partition(arr, lo, hi)
    quick_sort_inplace(arr, lo, pivot - 1)
    quick_sort_inplace(arr, pivot + 1, hi)

def partition(arr, lo, hi):
    pivot = arr[hi]
    i = lo
    for j in range(lo, hi):
        if arr[j] <= pivot:
            arr[i], arr[j] = arr[j], arr[i]
            i += 1
    arr[i], arr[hi] = arr[hi], arr[i]
    return i
```

## 复杂度
| 情况 | 时间 |
|------|------|
| 最好 | O(n log n) |
| 最坏 | O(n²) — 已有序且选端点为pivot |
| 平均 | O(n log n) |
| 空间 | O(log n) 递归栈 |
""",

    "merge_sort": """# 归并排序

## 概念
归并排序采用分治策略：将数组分成两半，分别排序，然后合并两个有序数组。保证O(n log n)的时间复杂度。

## 核心原理
1. **分割**：将数组从中间一分为二
2. **递归排序**：对两半分别排序
3. **合并**：将两个有序数组合并为一个

## Python示例
```python
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

print(merge_sort([5, 3, 8, 4, 2, 7, 1, 6]))
```

## 复杂度
| 情况 | 时间 |
|------|------|
| 所有情况 | O(n log n) |
| 空间 | O(n) 需要额外数组 |
| 稳定性 | 稳定 |
""",

    "binary_search": """# 二分查找

## 概念
二分查找在有序数组中，每次比较中间元素，将搜索范围缩小一半。时间复杂度O(log n)。

## 核心原理
1. 数组必须有序
2. 每次排除一半的搜索空间
3. 注意边界条件（开区间/闭区间）

## Python示例
```python
# 标准二分查找
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1

# 查找第一个大于等于target的位置（lower_bound）
def lower_bound(arr, target):
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo

print(binary_search([1, 3, 5, 7, 9, 11], 7))  # 3
```

## 常见变体
1. 查找第一个等于target的位置
2. 查找最后一个等于target的位置
3. 查找第一个大于target的位置
4. 旋转排序数组中的查找
""",

    "graph_basics": """# 图的基本概念

## 概念
图由顶点（Vertex）和边（Edge）组成，表示多对多的关系。分为有向图和无向图、加权图和无权图。

## 核心概念
- **顶点/节点**：图中的数据元素
- **边**：顶点之间的连接
- **度**：与顶点相连的边数
- **路径**：从一个顶点到另一个顶点的边序列
- **连通**：两个顶点之间存在路径

## 存储方式
```python
# 邻接矩阵（适合稠密图）
# matrix[i][j] = 1 表示i和j之间有边
matrix = [
    [0, 1, 1, 0],
    [1, 0, 0, 1],
    [1, 0, 0, 1],
    [0, 1, 1, 0],
]

# 邻接表（适合稀疏图，更常用）
from collections import defaultdict
graph = defaultdict(list)
graph[0] = [1, 2]
graph[1] = [0, 3]
graph[2] = [0, 3]
graph[3] = [1, 2]
```

## 常见误区
1. 混淆有向图和无向图的度数计算
2. 邻接矩阵空间O(V²)对稀疏图浪费
3. 忘记处理自环和重边
""",

    "graph_traversal": """# 图的遍历（BFS/DFS）

## 概念
图的遍历是访问图中所有顶点的过程。BFS按层遍历，DFS沿一条路径走到底再回溯。

## BFS（广度优先搜索）
- 使用队列，逐层扩展
- 可求最短路径（无权图）
- 时间O(V+E)，空间O(V)

## DFS（深度优先搜索）
- 使用栈（或递归），一条路走到底
- 可检测环、拓扑排序
- 时间O(V+E)，空间O(V)

## Python示例
```python
from collections import deque

def bfs(graph, start):
    visited = set([start])
    queue = deque([start])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return order

def dfs(graph, start, visited=None):
    if visited is None:
        visited = set()
    visited.add(start)
    order = [start]
    for neighbor in graph[start]:
        if neighbor not in visited:
            order.extend(dfs(graph, neighbor, visited))
    return order
```
""",

    "heap": """# 堆

## 概念
堆是一种特殊的完全二叉树，满足堆性质：最大堆中每个节点值≥其子节点值，最小堆中每个节点值≤其子节点值。通常用数组实现。

## 核心操作
- **插入**：添加到末尾，上浮调整 O(log n)
- **取堆顶**：返回根节点 O(1)
- **删除堆顶**：用末尾替代根，下沉调整 O(log n)

## Python示例
```python
import heapq

# Python的heapq是最小堆
heap = []
heapq.heappush(heap, 5)
heapq.heappush(heap, 2)
heapq.heappush(heap, 8)
heapq.heappush(heap, 1)

print(heapq.heappop(heap))  # 1（最小值）
print(heapq.heappop(heap))  # 2

# 最大堆技巧：取负数
max_heap = []
heapq.heappush(max_heap, -5)
heapq.heappush(max_heap, -2)
print(-heapq.heappop(max_heap))  # 5

# Top-K问题
def top_k(arr, k):
    return heapq.nlargest(k, arr)
```

## 经典应用
1. **优先队列**：任务调度
2. **Top-K问题**：求前K大/小
3. **堆排序**：O(n log n)原地排序
4. **Dijkstra算法**：最短路径
""",

    "avl": """# AVL树

## 概念
AVL树是一种自平衡二叉搜索树，任意节点的左右子树高度差不超过1。通过旋转操作维持平衡，保证查找/插入/删除均为O(log n)。

## 核心原理
- **平衡因子**：左子树高度 - 右子树高度，必须∈{-1, 0, 1}
- **四种旋转**：LL右旋、RR左旋、LR先左旋再右旋、RL先右旋再左旋

## 旋转示例
```
LL型（左左）→ 右旋：
    30           20
   /  \\         /  \\
  20   40  →   10   30
 /                  / \\
10                  25  40

RR型（右右）→ 左旋：
  20              30
 /  \\            /  \\
10   30    →   20   40
      / \\     / \\
    25   40  10  25
```

## 复杂度
| 操作 | 时间 |
|------|------|
| 查找 | O(log n) |
| 插入 | O(log n) |
| 删除 | O(log n) |

AVL比普通BST稳定，但旋转操作比红黑树频繁。
""",

    "selection_sort": """# 选择排序

## 概念
选择排序每轮从未排序部分找到最小元素，放到已排序部分末尾。

## Python示例
```python
def selection_sort(arr):
    n = len(arr)
    for i in range(n - 1):
        min_idx = i
        for j in range(i + 1, n):
            if arr[j] < arr[min_idx]:
                min_idx = j
        arr[i], arr[min_idx] = arr[min_idx], arr[i]
    return arr
```

## 复杂度：时间O(n²)，空间O(1)，不稳定
""",

    "insertion_sort": """# 插入排序

## 概念
插入排序将数组分为已排序和未排序两部分，每次取未排序的第一个元素，插入到已排序部分的正确位置。

## Python示例
```python
def insertion_sort(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr
```

## 复杂度：最好O(n)（已有序），最坏O(n²)，空间O(1)，稳定
""",

    "deque": """# 双端队列

## 概念
双端队列（Deque）两端都可以入队和出队的线性结构，是栈和队列的泛化。

## Python示例
```python
from collections import deque

dq = deque([1, 2, 3])
dq.appendleft(0)   # 左端入队
dq.append(4)       # 右端入队
dq.popleft()       # 左端出队 → 0
dq.pop()           # 右端出队 → 4
```

## 应用：滑动窗口最大值
""",

    "string": """# 串

## 概念
串（字符串）是由字符组成的线性序列。字符串匹配是核心问题。

## 核心操作
- 模式匹配：朴素O(nm)、KMP O(n+m)
- 字符串哈希：快速比较子串

## Python示例
```python
# 朴素匹配
def naive_search(text, pattern):
    n, m = len(text), len(pattern)
    for i in range(n - m + 1):
        if text[i:i+m] == pattern:
            return i
    return -1
```
""",

    "red_black_tree": """# 红黑树

## 概念
红黑树是一种近似平衡的二叉搜索树，通过节点颜色（红/黑）和5条规则维持平衡。比AVL旋转少，实际应用更广。

## 五条规则
1. 每个节点是红色或黑色
2. 根节点是黑色
3. 叶节点（NIL）是黑色
4. 红节点的子节点必须是黑色
5. 从任一节点到其所有叶节点的路径包含相同数目的黑节点

## 应用：C++ STL的map/set、Java的TreeMap、Linux内核进程调度
""",

    "b_tree": """# B树

## 概念
B树是一种多路平衡搜索树，每个节点可以有多个子节点。广泛应用于数据库索引和文件系统。

## 特点
- 每个节点存储多个关键字
- 所有叶节点在同一层
- 查找、插入、删除均为O(log n)
- 减少磁盘I/O次数
""",

    "heap_sort": """# 堆排序

## 概念
堆排序利用最大堆的性质进行排序：建堆后反复取堆顶（最大值）放到末尾。

## Python示例
```python
def heap_sort(arr):
    import heapq
    heapq.heapify(arr)  # 建最小堆
    return [heapq.heappop(arr) for _ in range(len(arr))]
```

## 复杂度：时间O(n log n)，空间O(1)原地，不稳定
""",

    "shell_sort": """# 希尔排序

## 概念
希尔排序是插入排序的改进版，通过分组（间隔递减）逐步减少逆序对。

## 复杂度：约O(n^1.3)，空间O(1)，不稳定
""",

    "radix_sort": """# 基数排序

## 概念
基数排序按位排序，从最低位到最高位依次进行稳定排序。

## 复杂度：时间O(d·n)，d为位数，空间O(n)，稳定
""",

    "sequential_search": """# 顺序查找

## 概念
从头到尾逐个比较，最简单的查找算法。

## 复杂度：时间O(n)，空间O(1)
""",

    "bst_search": """# BST查找

## 概念
利用二叉搜索树的有序性进行查找，比目标小往左，比目标大往右。

## 复杂度：平均O(log n)，最坏O(n)（退化为链表时）
""",

    "topological_sort": """# 拓扑排序

## 概念
拓扑排序将有向无环图（DAG）的顶点排成线性序列，使得每条边的起点在终点之前。

## 应用：课程先修关系、编译依赖、任务调度

## Python示例（Kahn算法）
```python
from collections import deque, defaultdict

def topological_sort(n, edges):
    graph = defaultdict(list)
    in_degree = [0] * n
    for u, v in edges:
        graph[u].append(v)
        in_degree[v] += 1

    queue = deque([i for i in range(n) if in_degree[i] == 0])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    return order if len(order) == n else []  # 有环返回空
```
""",

    "shortest_path": """# 最短路径

## 概念
求图中两个顶点之间权值和最小的路径。Dijkstra算法解决单源最短路径（无负权边）。

## Dijkstra算法
```python
import heapq

def dijkstra(graph, start):
    dist = {start: 0}
    heap = [(0, start)]
    while heap:
        d, node = heapq.heappop(heap)
        if d > dist.get(node, float('inf')):
            continue
        for neighbor, weight in graph[node]:
            new_dist = d + weight
            if new_dist < dist.get(neighbor, float('inf')):
                dist[neighbor] = new_dist
                heapq.heappush(heap, (new_dist, neighbor))
    return dist
```

## 复杂度：O((V+E)log V) 用优先队列
""",

    "mst": """# 最小生成树

## 概念
最小生成树是连通加权无向图中权值之和最小的生成树。Kruskal和Prim是两种经典算法。

## Kruskal算法（边贪心+并查集）
```python
def kruskal(n, edges):
    parent = list(range(n))
    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    edges.sort(key=lambda e: e[2])
    mst, total = [], 0
    for u, v, w in edges:
        pu, pv = find(u), find(v)
        if pu != pv:
            parent[pu] = pv
            mst.append((u, v, w))
            total += w
    return mst, total
```

## 复杂度：O(E log E)
""",
}

# 确保所有31个知识点都有文本
def get_all_knowledge_texts() -> dict:
    """获取所有知识点文本"""
    return KNOWLEDGE_TEXTS
