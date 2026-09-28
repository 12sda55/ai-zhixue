"""题库生成服务 - 经典题 + LLM动态生成

对照 ai_architecture_plan.md Phase 4:
- 预建经典题库（LeetCode Hot 100 / 教材习题 / 408真题）
- LLM动态生成（RAG知识库 + 经典题样例驱动）
- 难度梯阶（L1概念 → L2原理 → L3代码）
- 交叉验证（动态题校验，经典题免校验）
- 画像感知出题（薄弱点/难度偏好/认知风格/当前阶段）
"""

from __future__ import annotations
import json
import logging
import random
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.llm import llm_client
from app.knowledge.texts import get_all_knowledge_texts
from app.schemas.knowledge_graph import get_knowledge_node

logger = logging.getLogger(__name__)

# ===== 难度阶梯配置 =====

LEVEL_CONFIG = {
    1: {"name": "概念识别", "types": ["choice", "judge"], "upgrade": 2, "downgrade": None,
        "upgrade_threshold": 2, "downgrade_threshold": 2},
    2: {"name": "原理理解", "types": ["fill_blank", "choice", "analysis"], "upgrade": 3, "downgrade": 1,
        "upgrade_threshold": 2, "downgrade_threshold": 2},
    3: {"name": "代码实现", "types": ["code", "analysis"], "upgrade": None, "downgrade": 2,
        "upgrade_threshold": 2, "downgrade_threshold": 2},
}


def get_starting_level(mastery: float) -> int:
    """根据掌握度决定起始难度等级"""
    if mastery < 0.3:
        return 1
    elif mastery <= 0.6:
        return 2
    else:
        return 3


def get_level_by_mastery(mastery: float) -> int:
    """根据掌握度决定起始难度等级"""
    return get_starting_level(mastery)


def get_cold_start_level(profile) -> int:
    """冷启动：利用 stage / major / difficulty_level 推导初始难度等级

    当 knowledge_tree 为空时（新用户），画像太薄无法用 mastery 出题，
    改用冷启动三问的结果来估算合理起始等级。

    规则：
    - preview + non_cs → L1
    - review / exam_prep + cs → L3
    - synchronous → L2
    - difficulty_level 作为上限
    """
    if profile is None:
        return 1

    stage = str(profile.stage.value) if hasattr(profile.stage, 'value') else str(profile.stage)
    major = str(profile.major.value) if hasattr(profile.major, 'value') else str(profile.major)
    diff = str(profile.difficulty_level.value) if hasattr(profile.difficulty_level, 'value') else str(profile.difficulty_level)

    # 基础等级由阶段决定
    if stage in ("preview",):
        base = 1
    elif stage in ("review", "exam_prep"):
        base = 3
    else:  # synchronous 或其他
        base = 2

    # 非计算机专业降一级
    if major in ("non_cs", "cross_exam"):
        base = max(1, base - 1)
    elif major == "computer_science":
        base = min(3, base + 1)

    # 难度偏好作为校准
    if diff == "basic":
        base = max(1, base - 1)
    elif diff == "advanced":
        base = min(3, base + 1)

    return max(1, min(3, base))


# ===== 预建经典题库 =====

CLASSIC_QUESTIONS = {
    "array": [
        {
            "id": "array_classic_1",
            "type": "choice",
            "level": 1,
            "difficulty": 1,
            "description": "在长度为n的数组中，通过下标访问任意元素的时间复杂度是？",
            "options": ["O(1)", "O(n)", "O(log n)", "O(n^2)"],
            "answer": "O(1)",
            "explanation": "数组支持随机访问，通过下标可以在常数时间内访问任意位置的元素。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "array_classic_2",
            "type": "fill_blank",
            "level": 2,
            "difficulty": 2,
            "description": "在数组中间位置插入一个元素的时间复杂度是____，因为需要将插入位置之后的所有元素____。",
            "answer": "O(n), 后移一位",
            "explanation": "数组插入需要移动元素：最好情况在末尾插入O(1)，最坏情况在开头插入O(n)，平均O(n)。删除同理。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "array_classic_3",
            "type": "analysis",
            "level": 2,
            "difficulty": 3,
            "description": "动态数组（如Python的list）在容量不足时会进行扩容。请分析：为什么扩容通常采用翻倍策略？这种策略的均摊时间复杂度是多少？请用聚合分析法或记账法简要说明。",
            "answer": "翻倍策略的均摊时间复杂度为O(1)。分析：假设初始容量为1，每次翻倍。插入n个元素时，扩容发生在第1、2、4、8...次，总复制成本为1+2+4+...+n/2 ≈ n，n次插入总成本约2n，每次均摊O(1)。如果每次只增加固定容量，均摊复杂度会退化为O(n)。",
            "explanation": "这是均摊分析的经典案例。翻倍策略在空间和时间之间取得了良好平衡，Python的list和Java的ArrayList都采用此策略。",
            "classic": True,
            "source": "408真题",
        },
        {
            "id": "array_classic_4",
            "type": "code",
            "level": 3,
            "difficulty": 3,
            "description": "给定一个整数数组nums，将数组中的所有元素向右移动k个位置（k非负）。请实现rotate(nums, k)函数，原地修改数组。",
            "answer": "见测试用例",
            "starter_code": "def rotate(nums, k):\n    pass",
            "test_cases": [
                {"input": "nums=[1,2,3,4,5,6,7], k=3", "expected": "[5,6,7,1,2,3,4]"},
                {"input": "nums=[-1,-100,3,99], k=2", "expected": "[3,99,-1,-100]"},
            ],
            "explanation": "经典旋转数组问题（LeetCode 189），解法：先整体翻转，再分别翻转前k个和后n-k个。时间复杂度O(n)，空间O(1)。",
            "classic": True,
            "source": "LeetCode 189",
        },
        {
            "id": "array_classic_5",
            "type": "code",
            "level": 3,
            "difficulty": 4,
            "description": "给定一个数组nums，编写函数将所有0移动到数组的末尾，同时保持非零元素的相对顺序。要求原地操作。",
            "answer": "见测试用例",
            "starter_code": "def moveZeroes(nums):\n    pass",
            "test_cases": [
                {"input": "nums=[0,1,0,3,12]", "expected": "[1,3,12,0,0]"},
                {"input": "nums=[0]", "expected": "[0]"},
            ],
            "explanation": "LeetCode 283，双指针经典题。慢指针j指向下一个非零元素应放的位置，快指针i遍历数组，遇到非零就交换到j位置。时间复杂度O(n)，空间O(1)。",
            "classic": True,
            "source": "LeetCode 283",
        },
    ],
    "linked_list": [
        {
            "id": "linked_list_classic_1",
            "type": "choice",
            "level": 1,
            "difficulty": 1,
            "description": "单链表中删除某个节点，已知指向该节点的指针，下列描述正确的是？",
            "options": [
                "不需要遍历，可直接删除",
                "需要从头遍历找到前驱节点",
                "如果该节点不是尾节点，可复制下一个节点值来间接删除",
                "只能通过释放内存来删除"
            ],
            "answer": "如果该节点不是尾节点，可复制下一个节点值来间接删除",
            "explanation": "已知要删除节点的指针但不知道前驱时，如果节点不是尾节点，可以将下一个节点的值复制到当前节点，然后删除下一个节点（O(1)）。如果是尾节点则必须遍历找前驱。",
            "classic": True,
            "source": "面试经典",
        },
        {
            "id": "linked_list_classic_2",
            "type": "judge",
            "level": 2,
            "difficulty": 2,
            "description": "链表支持O(1)时间的随机访问，因此在需要频繁按下标访问元素的场景下优于数组。",
            "answer": "错误",
            "explanation": "链表不支持随机访问，按下标访问需要从头遍历，时间复杂度O(n)。数组才支持O(1)随机访问。链表的优势在于插入删除O(1)（已知位置时）和动态扩容。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "linked_list_classic_3",
            "type": "fill_blank",
            "level": 2,
            "difficulty": 2,
            "description": "在单链表中，头插法建立链表的顺序与输入顺序____（填'相同'或'相反'），尾插法则____。",
            "answer": "相反, 相同",
            "explanation": "头插法每次将新节点插入头部，先插入的节点在链表尾部，后插入的在头部，因此逆序。尾插法每次插入尾部，保持输入顺序。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "linked_list_classic_4",
            "type": "code",
            "level": 3,
            "difficulty": 4,
            "description": "给定一个单链表的头节点head，请反转链表并返回反转后的头节点。",
            "answer": "见测试用例",
            "starter_code": "class ListNode:\n    def __init__(self, val=0, next=None):\n        self.val = val\n        self.next = next\n\ndef reverseList(head):\n    pass",
            "test_cases": [
                {"input": "head=[1,2,3,4,5]", "expected": "[5,4,3,2,1]"},
                {"input": "head=[1,2]", "expected": "[2,1]"},
                {"input": "head=[]", "expected": "[]"},
            ],
            "explanation": "LeetCode 206，经典反转链表。迭代法：prev=None, curr=head，每次将curr.next指向prev。递归法：reverseList(head.next)后，head.next.next=head。",
            "classic": True,
            "source": "LeetCode 206",
        },
        {
            "id": "linked_list_classic_5",
            "type": "code",
            "level": 3,
            "difficulty": 3,
            "description": "给定一个链表，判断链表中是否有环。如果链表中有某个节点，可以通过连续跟踪next指针再次到达，则链表中存在环。请实现hasCycle(head)函数。",
            "answer": "见测试用例",
            "starter_code": "class ListNode:\n    def __init__(self, x):\n        self.val = x\n        self.next = None\n\ndef hasCycle(head):\n    pass",
            "test_cases": [
                {"input": "head=[3,2,0,-4], pos=1（2指向0）", "expected": "True"},
                {"input": "head=[1], pos=-1（无环）", "expected": "False"},
            ],
            "explanation": "LeetCode 141，快慢指针（Floyd判圈算法）经典应用。快指针每次走两步，慢指针每次走一步，若有环则必定相遇。时间复杂度O(n)，空间O(1)。",
            "classic": True,
            "source": "LeetCode 141",
        },
    ],
    "stack": [
        {
            "id": "stack_classic_1",
            "type": "judge",
            "level": 1,
            "difficulty": 1,
            "description": "栈是一种先进先出(FIFO)的数据结构。",
            "answer": "错误",
            "explanation": "栈是后进先出(LIFO)，先进先出(FIFO)是队列。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "stack_classic_2",
            "type": "fill_blank",
            "level": 2,
            "difficulty": 2,
            "description": "栈在计算机科学中有广泛应用，请列举三个典型应用场景：____、____、____。",
            "answer": "函数调用栈, 表达式求值, 括号匹配",
            "explanation": "栈的LIFO特性使其非常适合处理嵌套结构。函数调用使用调用栈保存返回地址；表达式求值用操作数栈和运算符栈；括号匹配检查嵌套配对。此外还有撤销操作(Undo)、浏览器的前进后退等。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "stack_classic_3",
            "type": "analysis",
            "level": 2,
            "difficulty": 3,
            "description": "请分析中缀表达式转后缀表达式（逆波兰表达式）的过程。以表达式 `3 + 4 * 2 / (1 - 5)` 为例，写出转换步骤和最终的后缀表达式。",
            "answer": "转换步骤：1) 遇到3，输出3；2) +入栈；3) 遇到4，输出4；4) *入栈（优先级高于+）；5) 遇到2，输出2；6) /优先级等于*，先弹出*输出，再/入栈；7) (入栈；8) 遇到1，输出1；9) -入栈；10) 遇到5，输出5；11) )弹出-输出，(丢弃；12) 依次弹出/、+输出。最终后缀表达式：3 4 2 * 1 5 - / +",
            "explanation": "这是栈在表达式求值中的经典应用。中缀转后缀遵循操作数直接输出、运算符按优先级处理、括号特殊处理的规则。后缀表达式不需要括号就能明确运算顺序，方便计算机计算。",
            "classic": True,
            "source": "教材习题",
        },
        {
            "id": "stack_classic_4",
            "type": "code",
            "level": 3,
            "difficulty": 3,
            "description": "给定一个只包含 '('、')'、'{'、'}'、'['、']' 的字符串s，判断字符串是否有效（括号正确配对且顺序正确）。",
            "answer": "见测试用例",
            "starter_code": "def isValid(s):\n    pass",
            "test_cases": [
                {"input": "s='()'", "expected": "True"},
                {"input": "s='()[]{}'", "expected": "True"},
                {"input": "s='(]'", "expected": "False"},
            ],
            "explanation": "LeetCode 20，栈的经典应用。遍历字符串，遇到左括号入栈，遇到右括号检查栈顶是否匹配。最后栈为空则有效。",
            "classic": True,
            "source": "LeetCode 20",
        },
        {
            "id": "stack_classic_5",
            "type": "code",
            "level": 3,
            "difficulty": 4,
            "description": "设计一个支持push、pop、top操作，并能在常数时间内检索到最小元素的栈。实现MinStack类：push(val)将元素推入栈，pop()删除栈顶元素，top()获取栈顶元素，getMin()检索栈中最小元素。",
            "answer": "见测试用例",
            "starter_code": "class MinStack:\n    def __init__(self):\n        pass\n    def push(self, val):\n        pass\n    def pop(self):\n        pass\n    def top(self):\n        pass\n    def getMin(self):\n        pass",
            "test_cases": [
                {"input": "push(-2),push(0),push(-3),getMin(),pop(),top(),getMin()", "expected": "getMin返回-3, top返回0, getMin返回-2"},
            ],
            "explanation": "LeetCode 155，使用辅助栈保存每个状态下的最小值。主栈正常push/pop，辅助栈push时比较当前val和栈顶，取较小值入栈。这样getMin只需O(1)时间返回辅助栈顶。",
            "classic": True,
            "source": "LeetCode 155",
        },
    ],
    "bst": [
        {
            "id": "bst_classic_1",
            "type": "choice",
            "level": 1,
            "difficulty": 1,
            "description": "下列关于二叉搜索树（BST）的描述，正确的是？",
            "options": [
                "左子树所有节点值大于根节点值",
                "中序遍历得到递减序列",
                "任意节点的左子树值 < 该节点值 < 右子树值",
                "BST一定是平衡的"
            ],
            "answer": "任意节点的左子树值 < 该节点值 < 右子树值",
            "explanation": "BST的定义性质：对任意节点，左子树所有节点值 < 该节点值 < 右子树所有节点值。中序遍历得到递增序列。BST不一定是平衡的（如插入有序序列会退化为链表）。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "bst_classic_2",
            "type": "fill_blank",
            "level": 2,
            "difficulty": 2,
            "description": "二叉搜索树的中序遍历结果是____序列。（填'递增的'或'递减的'或'无序的'）",
            "answer": "递增的",
            "explanation": "二叉搜索树的性质：左子树节点值 < 根节点值 < 右子树节点值，因此中序遍历（左→根→右）得到递增序列。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "bst_classic_3",
            "type": "analysis",
            "level": 2,
            "difficulty": 3,
            "description": "给定以下序列依次插入一个空的二叉搜索树：[5, 3, 7, 1, 4, 6, 8]。请画出最终的BST结构，并说明删除节点5后（用右子树最小值替代），新的根节点是什么？",
            "answer": "删除5后，找到右子树最小值6替代，新根节点为6。结构：根6，左子树为[3(左1,右4)]，右子树为[7(左None,右8)]。",
            "explanation": "BST删除的三种情况：叶子节点直接删、单子节点用子节点替代、双子节点用右子树最小值或左子树最大值替代。",
            "classic": True,
            "source": "教材习题",
        },
        {
            "id": "bst_classic_4",
            "type": "judge",
            "level": 2,
            "difficulty": 2,
            "description": "二叉搜索树的查找效率总是O(log n)，与树的形态无关。",
            "answer": "错误",
            "explanation": "BST的查找效率取决于树的高度。平衡BST的查找为O(log n)，但最坏情况下（如插入有序序列），BST退化为链表，查找效率变为O(n)。因此才有了AVL树、红黑树等平衡二叉搜索树。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "bst_classic_5",
            "type": "code",
            "level": 3,
            "difficulty": 4,
            "description": "给你一个二叉树的根节点root，判断其是否是一个有效的二叉搜索树。有效BST定义：节点的左子树只包含小于当前节点的数，右子树只包含大于当前节点的数，且所有左子树和右子树自身也是BST。",
            "answer": "见测试用例",
            "starter_code": "class TreeNode:\n    def __init__(self, val=0, left=None, right=None):\n        self.val = val\n        self.left = left\n        self.right = right\n\ndef isValidBST(root):\n    pass",
            "test_cases": [
                {"input": "root=[2,1,3]", "expected": "True"},
                {"input": "root=[5,1,4,null,null,3,6]", "expected": "False（根5的右子树中4<5）"},
            ],
            "explanation": "LeetCode 98，不仅需要检查每个节点的左右子节点，还要确保整棵子树的值都在合法范围内。使用递归时传递上下界（lower, upper），或利用BST中序遍历递增的性质。",
            "classic": True,
            "source": "LeetCode 98",
        },
    ],
    "bubble_sort": [
        {
            "id": "bubble_sort_classic_1",
            "type": "choice",
            "level": 1,
            "difficulty": 1,
            "description": "冒泡排序的基本思想是？",
            "options": [
                "每次从未排序部分选最小值放到已排序末尾",
                "相邻元素两两比较，逆序则交换，每轮将最大元素'冒泡'到末尾",
                "将数组分成两部分，递归排序后合并",
                "选一个基准元素，将数组分成小于和大于基准的两部分"
            ],
            "answer": "相邻元素两两比较，逆序则交换，每轮将最大元素'冒泡'到末尾",
            "explanation": "冒泡排序的核心是重复走访要排序的数列，一次比较两个相邻元素，如果顺序错误就交换。每一轮遍历会将未排序部分的最大值浮到最右端（就像气泡浮出水面）。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "bubble_sort_classic_2",
            "type": "fill_blank",
            "level": 2,
            "difficulty": 1,
            "description": "冒泡排序的最坏时间复杂度是____，最好时间复杂度是____（假设已优化提前终止）。",
            "answer": "O(n^2), O(n)",
            "explanation": "最坏情况（逆序）：每轮都要比较n-i次，共n轮，O(n^2)。最好情况（已有序）：第一轮无交换即提前终止，O(n)。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "bubble_sort_classic_3",
            "type": "judge",
            "level": 2,
            "difficulty": 2,
            "description": "冒泡排序是稳定的排序算法，即相等元素的相对顺序在排序后保持不变。",
            "answer": "正确",
            "explanation": "冒泡排序在相邻元素相等时不进行交换，因此保持了相等元素的原有相对顺序，是稳定排序。常见的稳定排序还有插入排序、归并排序；不稳定排序有快速排序、堆排序、选择排序。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "bubble_sort_classic_4",
            "type": "code",
            "level": 3,
            "difficulty": 2,
            "description": "请实现冒泡排序算法bubbleSort(arr)，对整数数组进行升序排列。要求加入提前终止优化：如果在某一轮遍历中没有发生任何交换，则说明数组已有序，提前结束。",
            "answer": "见测试用例",
            "starter_code": "def bubbleSort(arr):\n    pass",
            "test_cases": [
                {"input": "arr=[64, 34, 25, 12, 22, 11, 90]", "expected": "[11, 12, 22, 25, 34, 64, 90]"},
                {"input": "arr=[1, 2, 3, 4, 5]", "expected": "[1, 2, 3, 4, 5]"},
            ],
            "explanation": "双循环实现：外层控制轮数，内层进行相邻比较和交换。优化点是用一个flag标记本轮是否有交换，若无则break。时间复杂度最优O(n)，最坏O(n^2)，空间O(1)。",
            "classic": True,
            "source": "教材习题",
        },
    ],
    "binary_search": [
        {
            "id": "binary_search_classic_1",
            "type": "choice",
            "level": 1,
            "difficulty": 2,
            "description": "二分查找的前提条件是？",
            "options": ["数组必须有序", "数组必须无序", "必须用链表存储", "必须用树存储"],
            "answer": "数组必须有序",
            "explanation": "二分查找依赖有序性来每次排除一半的搜索空间，因此要求数据有序且支持随机访问（通常用数组）。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "binary_search_classic_2",
            "type": "analysis",
            "level": 2,
            "difficulty": 3,
            "description": "二分查找中，循环条件写成 `while left <= right` 与 `while left < right` 有什么区别？返回值应如何对应？请举例说明两种写法分别适用于什么场景。",
            "answer": "`while left <= right`：搜索区间为[left, right]闭区间，当left>right时退出。退出时left指向第一个大于target的位置，right指向最后一个小于target的位置。适用于需要精确找到target的场景。`while left < right`：搜索区间为[left, right)左闭右开，退出时left==right。常用于找边界（如第一个>=target的位置、第一个>target的位置）。经典场景：LeetCode 34在排序数组中查找元素的第一个和最后一个位置。",
            "explanation": "两种写法的本质区别在于搜索区间的定义。闭区间写法更直观，适合精确查找；左闭右开写法适合查找边界。理解这两种写法是掌握二分查找的关键。",
            "classic": True,
            "source": "408真题",
        },
        {
            "id": "binary_search_classic_3",
            "type": "fill_blank",
            "level": 2,
            "difficulty": 2,
            "description": "二分查找的变体：查找第一个值等于给定值的元素、查找最后一个值等于给定值的元素、查找第一个大于等于给定值的元素、查找最后一个____给定值的元素。这些变体的关键区别在于nums[mid]与target相等时的____策略。",
            "answer": "小于等于, 区间收缩",
            "explanation": "二分查找的四种经典变体都基于相同框架，区别在于当nums[mid]==target时：是收缩右边界找第一个、还是收缩左边界找最后一个。理解区间收缩方向是掌握变体的核心。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "binary_search_classic_4",
            "type": "code",
            "level": 3,
            "difficulty": 3,
            "description": "给定一个排序数组nums和一个目标值target，如果target存在则返回下标，否则返回它应该插入的位置下标。请以O(log n)时间复杂度实现。",
            "answer": "见测试用例",
            "starter_code": "def searchInsert(nums, target):\n    pass",
            "test_cases": [
                {"input": "nums=[1,3,5,6], target=5", "expected": "2"},
                {"input": "nums=[1,3,5,6], target=2", "expected": "1"},
                {"input": "nums=[1,3,5,6], target=7", "expected": "4"},
            ],
            "explanation": "LeetCode 35，二分查找变体。标准二分查找找target，未找到时left就是插入位置。",
            "classic": True,
            "source": "LeetCode 35",
        },
        {
            "id": "binary_search_classic_5",
            "type": "code",
            "level": 3,
            "difficulty": 4,
            "description": "整数数组nums按升序排列，但在某个未知下标处进行了旋转（如[0,1,2,4,5,6,7]变为[4,5,6,7,0,1,2]）。给定旋转后的数组和一个目标值target，如果nums中存在target则返回下标，否则返回-1。要求O(log n)时间复杂度。",
            "answer": "见测试用例",
            "starter_code": "def search(nums, target):\n    pass",
            "test_cases": [
                {"input": "nums=[4,5,6,7,0,1,2], target=0", "expected": "4"},
                {"input": "nums=[4,5,6,7,0,1,2], target=3", "expected": "-1"},
                {"input": "nums=[1], target=0", "expected": "-1"},
            ],
            "explanation": "LeetCode 33，二分查找进阶。旋转数组的关键是判断mid落在左半有序段还是右半有序段，然后判断target在哪个区间，收缩搜索范围。",
            "classic": True,
            "source": "LeetCode 33",
        },
    ],
    "recursion": [
        {
            "id": "recursion_classic_1",
            "type": "choice",
            "level": 1,
            "difficulty": 1,
            "description": "下列关于递归的描述，正确的是？",
            "options": [
                "递归函数必须有一个终止条件（基线条件）",
                "递归可以无限调用自身",
                "递归一定比迭代效率高",
                "递归不能用于树结构"
            ],
            "answer": "递归函数必须有一个终止条件（基线条件）",
            "explanation": "递归必须有基线条件来停止递归调用，否则会导致栈溢出。递归不一定比迭代快（有函数调用开销），但递归非常适合处理树和图等具有自相似结构的问题。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "recursion_classic_2",
            "type": "analysis",
            "level": 2,
            "difficulty": 3,
            "description": "分析以下递归函数的时间复杂度：`def fib(n): return 1 if n <= 1 else fib(n-1) + fib(n-2)`。写出递推公式，并说明为什么这个实现效率低。",
            "answer": "递推公式：T(n) = T(n-1) + T(n-2) + O(1)，解为O(2^n)。效率低的原因是大量重复计算——fib(5)会计算fib(4)和fib(3)，而fib(4)又会重新计算fib(3)。优化方法：记忆化搜索(O(n))或动态规划(O(n))。",
            "explanation": "这是指数级复杂度的经典案例，展示了朴素递归的问题和记忆化/DP的价值。",
            "classic": True,
            "source": "教材习题",
        },
        {
            "id": "recursion_classic_3",
            "type": "judge",
            "level": 2,
            "difficulty": 2,
            "description": "递归调用本质上是通过系统调用栈来实现的，每次递归调用都会在栈上分配一个新的栈帧。因此递归深度过大可能导致栈溢出（Stack Overflow）。",
            "answer": "正确",
            "explanation": "递归的底层机制就是系统调用栈：每次函数调用会压入栈帧（保存参数、局部变量、返回地址），递归返回时弹出。递归深度过大时栈空间耗尽导致Stack Overflow。这也是为什么有些递归可以改写为迭代来避免栈溢出，或者使用尾递归优化（部分语言支持）。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "recursion_classic_4",
            "type": "code",
            "level": 3,
            "difficulty": 3,
            "description": "汉诺塔问题：有三根柱子A、B、C，A柱上有n个大小不等的圆盘（大的在下，小的在上）。请将所有圆盘从A柱移动到C柱，移动过程中可以借助B柱，但每次只能移动一个圆盘，且大盘不能放在小盘上面。请实现hanoi(n, source, target, auxiliary)函数，打印移动步骤。",
            "answer": "见测试用例",
            "starter_code": "def hanoi(n, source, target, auxiliary):\n    pass",
            "test_cases": [
                {"input": "n=1, A→C", "expected": "A → C"},
                {"input": "n=2, A→C", "expected": "A→B, A→C, B→C"},
                {"input": "n=3, A→C", "expected": "共7步"},
            ],
            "explanation": "递归经典问题。递推思想：将n-1个盘从A借助C移到B，将第n个盘从A移到C，再将n-1个盘从B借助A移到C。移动次数为2^n - 1。时间复杂度O(2^n)。",
            "classic": True,
            "source": "教材习题",
        },
        {
            "id": "recursion_classic_5",
            "type": "code",
            "level": 3,
            "difficulty": 4,
            "description": "给定一个不含重复数字的数组nums，返回其所有可能的全排列。你可以按任意顺序返回答案。",
            "answer": "见测试用例",
            "starter_code": "def permute(nums):\n    pass",
            "test_cases": [
                {"input": "nums=[1,2,3]", "expected": "[[1,2,3],[1,3,2],[2,1,3],[2,3,1],[3,1,2],[3,2,1]]"},
                {"input": "nums=[0,1]", "expected": "[[0,1],[1,0]]"},
            ],
            "explanation": "LeetCode 46，回溯法（递归+撤销）的经典问题。每次选择一个未使用的数字加入当前路径，递归到底后回溯（撤销选择）。时间复杂度O(n × n!)，空间O(n)递归栈。",
            "classic": True,
            "source": "LeetCode 46",
        },
    ],
    "dynamic_programming": [
        {
            "id": "dp_classic_1",
            "type": "choice",
            "level": 1,
            "difficulty": 2,
            "description": "动态规划（DP）的两个核心要素是？",
            "options": [
                "贪心选择和最优子结构",
                "最优子结构和重叠子问题",
                "分治和归并",
                "状态转移和广度优先搜索"
            ],
            "answer": "最优子结构和重叠子问题",
            "explanation": "DP适用于具有最优子结构（问题的最优解包含子问题的最优解）和重叠子问题（子问题被重复计算）的场景。通过记忆化存储子问题结果，避免重复计算，将指数级复杂度降为多项式级。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "dp_classic_2",
            "type": "fill_blank",
            "level": 2,
            "difficulty": 2,
            "description": "动态规划与分治法的核心区别在于：分治法将问题分解为____的子问题，而DP解决的问题具有____子问题，因此使用表格存储子问题结果避免重复计算。",
            "answer": "互不相交（独立）, 重叠",
            "explanation": "分治法（如归并排序）分解的子问题互不重叠，直接递归解决即可。DP（如斐波那契）的子问题有大量重叠，不存储结果会导致指数级复杂度。这是DP需要引入备忘录/DP表的根本原因。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "dp_classic_3",
            "type": "analysis",
            "level": 2,
            "difficulty": 4,
            "description": "请分析0/1背包问题的DP解法。给定n个物品，重量w[i]，价值v[i]，背包容量W，每个物品只能选或不选（0/1）。写出状态定义、状态转移方程和最终答案的位置。并说明时间复杂度与空间复杂度。",
            "answer": "状态定义：dp[i][j]表示前i个物品放入容量j的背包的最大价值。转移方程：dp[i][j] = max(dp[i-1][j], dp[i-1][j-w[i]] + v[i])（当j >= w[i]时），否则dp[i][j] = dp[i-1][j]。最终答案：dp[n][W]。时间复杂度O(nW)，空间可优化为O(W)（一维滚动数组，但需倒序遍历）。",
            "explanation": "0/1背包是DP的经典入门问题。关键理解：每个物品选或不选对应两个子问题，取最大值。空间优化时反向遍历是为了防止同一物品被重复使用（那会变成完全背包）。",
            "classic": True,
            "source": "教材习题",
        },
        {
            "id": "dp_classic_4",
            "type": "code",
            "level": 3,
            "difficulty": 3,
            "description": "假设你正在爬楼梯，需要n阶才能到达楼顶。每次你可以爬1或2个台阶，有多少种不同的方法爬到楼顶？",
            "answer": "见测试用例",
            "starter_code": "def climbStairs(n):\n    pass",
            "test_cases": [
                {"input": "n=2", "expected": "2"},
                {"input": "n=3", "expected": "3"},
            ],
            "explanation": "LeetCode 70，经典DP入门。dp[i] = dp[i-1] + dp[i-2]，可优化为O(1)空间。",
            "classic": True,
            "source": "LeetCode 70",
        },
        {
            "id": "dp_classic_5",
            "type": "code",
            "level": 3,
            "difficulty": 4,
            "description": "给定一个整数数组nums，请找出一个具有最大和的连续子数组（子数组最少包含一个元素），返回其最大和。",
            "answer": "见测试用例",
            "starter_code": "def maxSubArray(nums):\n    pass",
            "test_cases": [
                {"input": "nums=[-2,1,-3,4,-1,2,1,-5,4]", "expected": "6（子数组[4,-1,2,1]）"},
                {"input": "nums=[1]", "expected": "1"},
                {"input": "nums=[5,4,-1,7,8]", "expected": "23"},
            ],
            "explanation": "LeetCode 53，Kadane算法。dp[i]表示以i结尾的最大子数组和。dp[i] = max(dp[i-1] + nums[i], nums[i])。可优化为O(1)空间：用cur代替dp数组，cur = max(cur + num, num)。",
            "classic": True,
            "source": "LeetCode 53",
        },
    ],
    "queue": [
        {
            "id": "queue_classic_1",
            "type": "choice",
            "level": 1,
            "difficulty": 1,
            "description": "下列关于队列的描述，正确的是？",
            "options": [
                "队列是后进先出(LIFO)的数据结构",
                "队列支持在两端进行插入和删除",
                "队列是先进先出(FIFO)的数据结构，插入在一端，删除在另一端",
                "队列的插入和删除都在同一端进行"
            ],
            "answer": "队列是先进先出(FIFO)的数据结构，插入在一端，删除在另一端",
            "explanation": "队列是FIFO结构：元素从队尾(rear)入队，从队首(front)出队。与栈(LIFO)形成对比。双端队列(deque)才支持两端操作，普通队列只能在指定端操作。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "queue_classic_2",
            "type": "analysis",
            "level": 2,
            "difficulty": 3,
            "description": "循环队列中用数组Q[0..M-1]存储，设front指向队首元素，rear指向队尾元素的下一个位置。请分析如何判断队空和队满的条件？并说明为什么循环队列要牺牲一个存储单元来区分空和满。",
            "answer": "队空条件：front == rear。队满条件：(rear + 1) % M == front。牺牲一个单元的原因：如果不牺牲，队满时也是front==rear，与队空无法区分。牺牲一个单元后，队满时rear指向的单元不可用，队列最多存M-1个元素。另一种方案：使用size计数变量，则队列可存M个元素，队空size==0，队满size==M。",
            "explanation": "循环队列是408考研高频考点。理解取模运算在循环队列中的作用，以及判空判满条件的推导，是掌握循环队列的关键。",
            "classic": True,
            "source": "408真题",
        },
        {
            "id": "queue_classic_3",
            "type": "fill_blank",
            "level": 2,
            "difficulty": 2,
            "description": "队列在计算机科学中广泛应用，请列举三个典型场景：____、____、____。",
            "answer": "广度优先搜索(BFS), 消息队列, 打印任务队列",
            "explanation": "队列的FIFO特性使其适合按序处理的场景。BFS用队列逐层扩展；消息队列实现异步解耦；打印队列按提交顺序打印任务。其他应用：操作系统的进程调度就绪队列、网络数据包缓冲等。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "queue_classic_4",
            "type": "code",
            "level": 3,
            "difficulty": 4,
            "description": "请你仅使用两个栈实现一个先入先出的队列MyQueue。实现push(x)、pop()、peek()、empty()四个方法。你只能使用栈的标准操作（push to top, peek/pop from top, size, is empty）。",
            "answer": "见测试用例",
            "starter_code": "class MyQueue:\n    def __init__(self):\n        pass\n    def push(self, x):\n        pass\n    def pop(self):\n        pass\n    def peek(self):\n        pass\n    def empty(self):\n        pass",
            "test_cases": [
                {"input": "push(1),push(2),peek(),pop(),empty()", "expected": "peek返回1, pop返回1, empty返回False"},
            ],
            "explanation": "LeetCode 232，用两个栈模拟队列。栈1用于入队(push直接入栈1)，栈2用于出队。当pop/peek时，若栈2为空，则将栈1所有元素弹出并压入栈2（此时顺序反转，实现FIFO）。均摊时间复杂度O(1)。",
            "classic": True,
            "source": "LeetCode 232",
        },
    ],
    "hash_table": [
        {
            "id": "hash_table_classic_1",
            "type": "choice",
            "level": 1,
            "difficulty": 1,
            "description": "哈希表（散列表）在理想情况下查找元素的时间复杂度是？",
            "options": ["O(1)", "O(n)", "O(log n)", "O(n log n)"],
            "answer": "O(1)",
            "explanation": "哈希表通过哈希函数将键映射到数组下标，理想情况下（无冲突或冲突少）插入、删除、查找均为O(1)。但在哈希冲突严重时可能退化到O(n)。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "hash_table_classic_2",
            "type": "analysis",
            "level": 2,
            "difficulty": 3,
            "description": "请分析哈希冲突的两种主要解决方法：开放地址法和链地址法。比较它们的原理、优缺点和适用场景。",
            "answer": "链地址法（拉链法）：每个哈希桶维护一个链表，冲突的元素挂在链表上。优点：实现简单，装填因子可大于1，删除方便。缺点：需要额外指针空间，缓存不友好。开放地址法：冲突时按某种探测序列（线性探测、二次探测、双重哈希）寻找下一个空位。优点：所有数据存在数组内，缓存友好，无指针开销。缺点：装填因子必须小于1，删除麻烦（需标记删除），可能有聚集问题。Java HashMap使用链地址法+红黑树优化；Python dict使用开放地址法。",
            "explanation": "这是哈希表设计的核心问题。链地址法在JDK中演进为链表转红黑树（长度>8时），结合了两者优势。理解两种方法的权衡是设计高效哈希表的基础。",
            "classic": True,
            "source": "408真题",
        },
        {
            "id": "hash_table_classic_3",
            "type": "fill_blank",
            "level": 2,
            "difficulty": 2,
            "description": "一个好的哈希函数应满足两个基本要求：计算____和分布____。常用的哈希函数设计方法有直接定址法、____、平方取中法等。",
            "answer": "简单快速, 均匀, 除留余数法",
            "explanation": "哈希函数需要计算快速（O(1)）且尽可能均匀分布以减少冲突。除留余数法是最常用的方法：H(key) = key % p，其中p通常取不大于表长的质数，以减少冲突概率。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "hash_table_classic_4",
            "type": "code",
            "level": 3,
            "difficulty": 3,
            "description": "给定一个整数数组nums和一个整数目标值target，请在该数组中找出和为目标值target的两个整数，并返回它们的数组下标。假设每种输入只对应一个答案，且不能使用同一个元素两次。",
            "answer": "见测试用例",
            "starter_code": "def twoSum(nums, target):\n    pass",
            "test_cases": [
                {"input": "nums=[2,7,11,15], target=9", "expected": "[0,1]"},
                {"input": "nums=[3,2,4], target=6", "expected": "[1,2]"},
                {"input": "nums=[3,3], target=6", "expected": "[0,1]"},
            ],
            "explanation": "LeetCode 1，哈希表的经典应用。遍历数组，对每个nums[i]，检查target-nums[i]是否在哈希表中。若在则返回两个下标，若不在则将(nums[i], i)存入哈希表。时间复杂度O(n)，空间O(n)。",
            "classic": True,
            "source": "LeetCode 1",
        },
    ],
    "binary_tree": [
        {
            "id": "binary_tree_classic_1",
            "type": "choice",
            "level": 1,
            "difficulty": 1,
            "description": "二叉树的四种遍历方式中，哪种遍历可以得到从根到叶子的路径序列？",
            "options": [
                "前序遍历（根→左→右）",
                "中序遍历（左→根→右）",
                "后序遍历（左→右→根）",
                "层序遍历（逐层从左到右）"
            ],
            "answer": "前序遍历（根→左→右）",
            "explanation": "前序遍历先访问根节点再访问子树，因此路径上从根到叶子按访问顺序出现。中序遍历得到有序序列（BST）。后序遍历常用于先处理子树再处理根的场景（如计算树高、删除树）。层序遍历用于按层处理。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "binary_tree_classic_2",
            "type": "judge",
            "level": 1,
            "difficulty": 2,
            "description": "满二叉树一定是完全二叉树，完全二叉树也一定是满二叉树。",
            "answer": "错误",
            "explanation": "满二叉树一定是完全二叉树（满二叉树的每一层都满了，自然满足完全二叉树的定义）。但完全二叉树不一定是满二叉树：完全二叉树只要求除最后一层外其他层都满，且最后一层节点从左到右连续排列，最后一层可以不满。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "binary_tree_classic_3",
            "type": "analysis",
            "level": 2,
            "difficulty": 3,
            "description": "已知一棵二叉树的前序遍历序列为[A, B, D, E, C, F, G]，中序遍历序列为[D, B, E, A, F, C, G]。请重建这棵二叉树并写出后序遍历序列。说明重建的原理。",
            "answer": "重建原理：前序第一个A是根，在中序中找到A，左边[D,B,E]是左子树，右边[F,C,G]是右子树。递归处理：左子树前序[B,D,E]中序[D,B,E]→根B，左D右E；右子树前序[C,F,G]中序[F,C,G]→根C，左F右G。最终树：A(左B(左D,右E), 右C(左F,右G))。后序遍历：D, E, B, F, G, C, A。",
            "explanation": "此题的经典结论：给定前序+中序（或后序+中序）可以唯一确定一棵二叉树。但仅有前序+后序无法唯一确定。重建的关键是利用前序/后序确定根，利用中序划分左右子树。",
            "classic": True,
            "source": "408真题",
        },
        {
            "id": "binary_tree_classic_4",
            "type": "code",
            "level": 3,
            "difficulty": 3,
            "description": "给定一个二叉树，找出其最大深度。二叉树的深度为根节点到最远叶子节点的最长路径上的节点数。",
            "answer": "见测试用例",
            "starter_code": "class TreeNode:\n    def __init__(self, val=0, left=None, right=None):\n        self.val = val\n        self.left = left\n        self.right = right\n\ndef maxDepth(root):\n    pass",
            "test_cases": [
                {"input": "root=[3,9,20,null,null,15,7]", "expected": "3"},
                {"input": "root=[1,null,2]", "expected": "2"},
            ],
            "explanation": "LeetCode 104，二叉树基础题。递归法：maxDepth(root) = 1 + max(maxDepth(left), maxDepth(right))，空节点深度为0。也可用层序遍历(BFS)统计层数。",
            "classic": True,
            "source": "LeetCode 104",
        },
        {
            "id": "binary_tree_classic_5",
            "type": "code",
            "level": 3,
            "difficulty": 4,
            "description": "给定一个二叉树的根节点root，检查它是否轴对称（即是否是其镜像）。",
            "answer": "见测试用例",
            "starter_code": "class TreeNode:\n    def __init__(self, val=0, left=None, right=None):\n        self.val = val\n        self.left = left\n        self.right = right\n\ndef isSymmetric(root):\n    pass",
            "test_cases": [
                {"input": "root=[1,2,2,3,4,4,3]", "expected": "True"},
                {"input": "root=[1,2,2,null,3,null,3]", "expected": "False"},
            ],
            "explanation": "LeetCode 101，判断对称二叉树。递归法：比较左右子树是否为镜像——左子树的左子节点与右子树的右子节点比较，左子树的右子节点与右子树的左子节点比较。也可用迭代法（队列）。",
            "classic": True,
            "source": "LeetCode 101",
        },
    ],
    "quick_sort": [
        {
            "id": "quick_sort_classic_1",
            "type": "choice",
            "level": 1,
            "difficulty": 1,
            "description": "快速排序的核心思想是？",
            "options": [
                "每次选出最小元素放到前面",
                "相邻元素两两比较交换",
                "选一个基准元素，将数组划分为两部分，分别递归排序",
                "将数组分成两半，分别排序后再合并"
            ],
            "answer": "选一个基准元素，将数组划分为两部分，分别递归排序",
            "explanation": "快速排序采用分治策略：选择一个基准(pivot)，通过一趟排序将数组分为两部分——左边元素≤pivot，右边≥pivot，然后递归地对两部分排序。归并排序也是分治，但它是先分后合；快排是先分区再递归。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "quick_sort_classic_2",
            "type": "analysis",
            "level": 2,
            "difficulty": 4,
            "description": "请分析快速排序的时间复杂度。为什么最好情况是O(n log n)，最坏情况是O(n^2)？什么情况下会出现最坏情况？如何避免？",
            "answer": "最好情况：每次分区都均匀地将数组分成两半，递归树高度log n，每层分区需O(n)，总O(n log n)。最坏情况：每次分区极不均匀（如数组已有序且选择第一个元素为pivot），一侧n-1个元素，一侧0个，递归树退化为链表，高度n，总O(n^2)。避免方法：随机选择pivot、三数取中法选pivot、使用IntroSort（递归深度超阈值切换堆排序）。",
            "explanation": "快排的时间复杂度依赖于pivot的选择。虽然最坏是O(n^2)，但通过随机化等优化，实际表现通常非常好，是实际应用中最常用的排序算法之一。C++ std::sort使用IntroSort。",
            "classic": True,
            "source": "408真题",
        },
        {
            "id": "quick_sort_classic_3",
            "type": "fill_blank",
            "level": 2,
            "difficulty": 2,
            "description": "快速排序中基准元素(pivot)的选择策略有：____（可能导致最坏情况）、随机选择、____。其中____策略可以有效避免在已有序数组上退化为O(n^2)。",
            "answer": "固定选择第一个/最后一个, 三数取中法, 三数取中法",
            "explanation": "固定选择第一个元素为pivot在数组已有序时导致最坏O(n^2)。随机选择降低了最坏概率。三数取中法（取首、尾、中间三个元素的中位数作为pivot）在实际中表现最好。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "quick_sort_classic_4",
            "type": "code",
            "level": 3,
            "difficulty": 4,
            "description": "请实现快速排序算法quickSort(arr)。要求使用三数取中法选择基准元素，对整数数组进行升序排列。",
            "answer": "见测试用例",
            "starter_code": "def quickSort(arr):\n    pass",
            "test_cases": [
                {"input": "arr=[3,6,8,10,1,2,1]", "expected": "[1,1,2,3,6,8,10]"},
                {"input": "arr=[5,4,3,2,1]", "expected": "[1,2,3,4,5]"},
                {"input": "arr=[1]", "expected": "[1]"},
            ],
            "explanation": "三数取中法：比较left、right、mid三个位置的值，取中位数作为pivot并交换到合适位置。分区时使用双指针：左指针找>=pivot的，右指针找<=pivot的，交换后继续。递归排序左右两部分。",
            "classic": True,
            "source": "教材习题",
        },
    ],
    "merge_sort": [
        {
            "id": "merge_sort_classic_1",
            "type": "choice",
            "level": 1,
            "difficulty": 1,
            "description": "归并排序的核心思想是？",
            "options": [
                "相邻元素两两比较交换",
                "每次选最小元素放到前面",
                "将数组递归分成两半，分别排序后再合并为一个有序数组",
                "选基准元素，将数组分成大小两部分递归排序"
            ],
            "answer": "将数组递归分成两半，分别排序后再合并为一个有序数组",
            "explanation": "归并排序是典型的分治算法：分解(Divide)——将数组分成两半；解决(Conquer)——递归排序两半；合并(Merge)——将两个有序子数组合并为一个有序数组。与快排不同，归并排序的合并是明确的O(n)操作。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "merge_sort_classic_2",
            "type": "analysis",
            "level": 2,
            "difficulty": 3,
            "description": "归并排序为什么是稳定的？请从归并过程的实现分析。同时给出归并排序的时间复杂度、空间复杂度和稳定性的完整分析。",
            "answer": "稳定性分析：在合并两个有序子数组时，当左子数组和右子数组出现相等元素时，优先取左子数组的元素，这样就保持了相等元素的原相对顺序，因此归并排序是稳定的。时间复杂度：总是O(n log n)——分解log n层，每层合并O(n)，与输入是否有序无关。空间复杂度：O(n)，合并时需要临时数组。归并排序是外部排序的基础（适合处理大数据量磁盘文件排序）。",
            "explanation": "归并排序的三个特点：1)稳定排序；2)总是O(n log n)，无最好最坏之分；3)需要O(n)额外空间。它也是链表排序的首选（链表归并不需要额外空间）。在Java中，Arrays.sort(Object[])使用的是归并排序的变体TimSort。",
            "classic": True,
            "source": "408真题",
        },
        {
            "id": "merge_sort_classic_3",
            "type": "judge",
            "level": 2,
            "difficulty": 2,
            "description": "归并排序的空间复杂度是O(1)，因为它是原地排序算法。",
            "answer": "错误",
            "explanation": "归并排序需要O(n)的额外空间来存储合并过程中的临时数组（除非使用原地归并，但那会极大增加实现复杂度和时间开销）。相比之下，快速排序、堆排序是原地排序（递归栈不算的话空间O(1)）。但对于链表归并排序，由于可以修改指针，空间可以为O(1)。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "merge_sort_classic_4",
            "type": "code",
            "level": 3,
            "difficulty": 4,
            "description": "请实现归并排序算法mergeSort(arr)，对整数数组进行升序排列。",
            "answer": "见测试用例",
            "starter_code": "def mergeSort(arr):\n    pass",
            "test_cases": [
                {"input": "arr=[38,27,43,3,9,82,10]", "expected": "[3,9,10,27,38,43,82]"},
                {"input": "arr=[5,4,3,2,1]", "expected": "[1,2,3,4,5]"},
                {"input": "arr=[2]", "expected": "[2]"},
            ],
            "explanation": "实现分为两步：1)mergeSort递归分解：找到中点mid，递归排序左右两部分；2)merge合并：用双指针i、j分别遍历左右有序子数组，取较小值放入结果。注意用临时数组存储合并结果再复制回原数组。",
            "classic": True,
            "source": "教材习题",
        },
    ],
    "graph_basics": [
        {
            "id": "graph_basics_classic_1",
            "type": "choice",
            "level": 1,
            "difficulty": 1,
            "description": "图的两种主要存储方式是？",
            "options": [
                "邻接矩阵和邻接表",
                "顺序存储和链式存储",
                "数组和链表",
                "栈和队列"
            ],
            "answer": "邻接矩阵和邻接表",
            "explanation": "邻接矩阵：用二维数组G[i][j]表示顶点i到j是否有边。空间O(V^2)，适合稠密图。邻接表：每个顶点维护一个链表（或列表）存储其邻居。空间O(V+E)，适合稀疏图。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "graph_basics_classic_2",
            "type": "judge",
            "level": 1,
            "difficulty": 2,
            "description": "有向图中顶点的度等于入度和出度之和，无向图中顶点的度就是与该顶点相连的边数。",
            "answer": "正确",
            "explanation": "无向图中，顶点v的度deg(v) = 与v关联的边数。有向图中，出度outdeg(v) = 从v出发的边数，入度indeg(v) = 指向v的边数，总度 = outdeg(v) + indeg(v)。度是图论中最基本的概念。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "graph_basics_classic_3",
            "type": "analysis",
            "level": 2,
            "difficulty": 3,
            "description": "请从数据结构、遍历顺序、应用场景三个维度，全面比较图的深度优先搜索(DFS)和广度优先搜索(BFS)。",
            "answer": "数据结构：DFS使用栈（递归隐式栈或显式栈），BFS使用队列。遍历顺序：DFS沿一条路径深入到底再回溯，类似走迷宫；BFS逐层扩展，类似水波扩散。应用场景：DFS——拓扑排序、找连通分量、检测环、回溯法；BFS——最短路径（无权图）、层级遍历、社交网络中的N度人脉。在树中，DFS对应前/中/后序遍历，BFS对应层序遍历。",
            "explanation": "DFS和BFS是图算法的基础。DFS适合探索所有可能路径的场景（如回溯法），BFS适合逐层扩展找最短路径。实际中很多算法（如Dijkstra）可视为带权BFS的变体。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "graph_basics_classic_4",
            "type": "code",
            "level": 3,
            "difficulty": 4,
            "description": "给定有n个节点的无向图（编号0到n-1），以邻接表形式graph表示。请实现深度优先搜索遍历图，返回从节点0出发的DFS遍历序列。使用visited数组避免重复访问。",
            "answer": "见测试用例",
            "starter_code": "def dfs_traversal(graph):\n    pass",
            "test_cases": [
                {"input": "graph=[[1,2],[0,3],[0,3],[1,2]]（4个节点0-1-3和0-2-3）", "expected": "[0, 1, 3, 2]（或其他合法DFS序）"},
                {"input": "graph=[[1],[0]]（2个节点相连）", "expected": "[0, 1]"},
            ],
            "explanation": "DFS实现方式：递归或显式栈。visited数组标记已访问节点，每次从当前节点出发访问所有未访问的邻居。时间复杂度O(V+E)，空间O(V)（visited数组+递归栈）。如果是非连通图，需要从每个未访问节点出发执行DFS。",
            "classic": True,
            "source": "教材习题",
        },
    ],
    "heap": [
        {
            "id": "heap_classic_1",
            "type": "choice",
            "level": 1,
            "difficulty": 1,
            "description": "下列关于堆（Heap）的描述，正确的是？",
            "options": [
                "堆是一种无序的数据结构",
                "小顶堆中，任意节点的值都小于等于其子节点的值",
                "堆中的元素是按升序排列的",
                "堆不支持插入和删除操作"
            ],
            "answer": "小顶堆中，任意节点的值都小于等于其子节点的值",
            "explanation": "堆是一棵完全二叉树，且满足堆序性质：大顶堆(max-heap)中父节点 ≥ 子节点，小顶堆(min-heap)中父节点 ≤ 子节点。堆不是有序的，只保证父子之间的大小关系。堆支持O(log n)的插入和删除。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "heap_classic_2",
            "type": "analysis",
            "level": 2,
            "difficulty": 3,
            "description": "请详细描述在小顶堆中插入一个元素和删除堆顶元素的操作过程（上滤和下滤），并分析各自的时间复杂度。",
            "answer": "插入（上滤/Percolate Up）：将新元素放在堆的末尾（完全二叉树的最后一个位置），然后与父节点比较，若小于父节点则交换，重复直到满足堆序。时间复杂度O(log n)。删除堆顶（下滤/Percolate Down）：将堆顶元素取出，用最后一个元素替换堆顶，然后与两个子节点中较小的比较，若大于子节点则交换，重复直到满足堆序。时间复杂度O(log n)。建堆：从最后一个非叶节点开始向前做下滤，时间复杂度O(n)（不是O(n log n)，这是经典的堆排序分析结论）。",
            "explanation": "上滤和下滤是堆操作的核心。理解这两个操作是掌握优先队列、堆排序、TopK问题的基础。注意建堆的O(n)分析：虽然看起来每个节点下滤O(log n)，但不同高度的节点数量不同，求和后为O(n)。",
            "classic": True,
            "source": "教材习题",
        },
        {
            "id": "heap_classic_3",
            "type": "fill_blank",
            "level": 2,
            "difficulty": 2,
            "description": "堆排序的基本步骤：首先____（时间复杂度____），然后依次将堆顶元素与末尾元素交换并____，重复n-1次。堆排序的时间复杂度为____，空间复杂度为____，是____（填'稳定'或'不稳定'）排序。",
            "answer": "建堆, O(n), 下滤调整, O(n log n), O(1), 不稳定",
            "explanation": "堆排序的过程：1)建堆O(n)；2)重复n-1次：交换堆顶和末尾元素（将最大值放到末尾），然后对堆顶做下滤O(log n)，共O(n log n)。堆排序原地排序但交换会破坏稳定性。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "heap_classic_4",
            "type": "code",
            "level": 3,
            "difficulty": 4,
            "description": "给定整数数组nums和整数k，请返回数组中第k个最大的元素。注意是排序后的第k个最大元素，而不是第k个不同的元素。请使用堆的方法实现。",
            "answer": "见测试用例",
            "starter_code": "def findKthLargest(nums, k):\n    pass",
            "test_cases": [
                {"input": "nums=[3,2,1,5,6,4], k=2", "expected": "5"},
                {"input": "nums=[3,2,3,1,2,4,5,5,6], k=4", "expected": "4"},
            ],
            "explanation": "LeetCode 215，TopK经典题。小顶堆法：维护大小为k的小顶堆，遍历数组，若当前元素>堆顶则替换并调整。最终堆顶就是第k大。时间复杂度O(n log k)，空间O(k)。也可用快速选择算法达到平均O(n)。",
            "classic": True,
            "source": "LeetCode 215",
        },
    ],
    "avl": [
        {
            "id": "avl_classic_1",
            "type": "choice",
            "level": 1,
            "difficulty": 2,
            "description": "AVL树的定义是？",
            "options": [
                "一棵二叉搜索树，其中每个节点的左右子树高度差不超过1",
                "一棵二叉搜索树，其中根节点是整棵树中值最大的节点",
                "一棵任意二叉树，满足红黑性质",
                "一棵完全二叉树，满足堆序性质"
            ],
            "answer": "一棵二叉搜索树，其中每个节点的左右子树高度差不超过1",
            "explanation": "AVL树是最早发明的自平衡二叉搜索树（1962年，Adelson-Velsky和Landis）。平衡因子 = 左子树高度 - 右子树高度，AVL树要求所有节点的平衡因子绝对值≤1（即-1、0、1）。这保证了树的高度为O(log n)。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "avl_classic_2",
            "type": "analysis",
            "level": 2,
            "difficulty": 4,
            "description": "AVL树的旋转操作有哪四种？请分别描述每种旋转的触发条件（即不平衡的形态）和旋转步骤。以LL型（右旋）为例画图说明。",
            "answer": "四种旋转：(1)LL型（左子树的左子树插入导致）→ 右旋(Right Rotate)：将失衡节点的左孩子提升为新根，原失衡节点成为新根的右孩子。(2)RR型（右子树的右子树插入导致）→ 左旋(Left Rotate)：与LL对称。(3)LR型（左子树的右子树插入导致）→ 先左旋失衡节点的左子树，再右旋失衡节点。(4)RL型（右子树的左子树插入导致）→ 先右旋失衡节点的右子树，再左旋失衡节点。判断方法：从插入节点向上找到第一个失衡节点，看插入路径上是LL/LR/RR/RL哪种形态。",
            "explanation": "AVL旋转是平衡二叉树的核心机制。理解四种旋转的触发条件（看插入路径上是LL还是LR等）比记忆步骤更重要。掌握了就理解了为什么搜索树能保持O(log n)。",
            "classic": True,
            "source": "408真题",
        },
        {
            "id": "avl_classic_3",
            "type": "fill_blank",
            "level": 2,
            "difficulty": 2,
            "description": "AVL树中节点的平衡因子定义为____减去____。平衡因子只能取____、____、____三个值。当某节点平衡因子超出此范围时，需要通过____操作恢复平衡。",
            "answer": "左子树高度, 右子树高度, -1, 0, 1, 旋转",
            "explanation": "平衡因子 = 左子树高度 - 右子树高度。AVL树要求-1≤平衡因子≤1。插入或删除节点后可能导致某个祖先节点平衡因子变为±2，需要旋转调整。插入最多只需一次旋转（或双旋即两次），删除可能需要多次旋转向上传播。",
            "classic": True,
            "source": "教材基础",
        },
        {
            "id": "avl_classic_4",
            "type": "code",
            "level": 3,
            "difficulty": 3,
            "description": "给定一个二叉树，判断它是否是高度平衡的二叉树（AVL树）。高度平衡的二叉树定义为：每个节点的左右子树高度差的绝对值不超过1。",
            "answer": "见测试用例",
            "starter_code": "class TreeNode:\n    def __init__(self, val=0, left=None, right=None):\n        self.val = val\n        self.left = left\n        self.right = right\n\ndef isBalanced(root):\n    pass",
            "test_cases": [
                {"input": "root=[3,9,20,null,null,15,7]", "expected": "True"},
                {"input": "root=[1,2,2,3,3,null,null,4,4]", "expected": "False"},
                {"input": "root=[]", "expected": "True"},
            ],
            "explanation": "LeetCode 110，自底向上递归。helper函数返回(height, isBalanced)：空节点返回(0, True)；递归得到左右子树结果，当前高度=max(lh,rh)+1，平衡性=lBalanced && rBalanced && abs(lh-rh)≤1。时间复杂度O(n)，避免了自顶向下重复计算高度的O(n^2)做法。",
            "classic": True,
            "source": "LeetCode 110",
        },
    ],
}


# ===== 题库服务主类 =====

class QuestionService:
    """题库生成服务（MySQL持久化）"""

    # ---- 经典题入库 ----

    def ensure_classic_in_db(self, db: Session):
        """确保经典题已入库（幂等：重复调用自动跳过已有题）

        首次启动时自动将 CLASSIC_QUESTIONS 写入 MySQL，
        后续重启时自动跳过。
        """
        from app.models.profile import QuestionModel

        for kp, questions in CLASSIC_QUESTIONS.items():
            for q in questions:
                existing = db.query(QuestionModel).filter(
                    QuestionModel.id == q["id"]
                ).first()
                if existing:
                    continue
                model = QuestionModel(
                    id=q["id"],
                    knowledge_point=kp,
                    type=q["type"],
                    level=q["level"],
                    difficulty=q.get("difficulty", q["level"]),
                    description=q["description"],
                    options_json=json.dumps(q.get("options", []), ensure_ascii=False),
                    answer=q.get("answer", ""),
                    explanation=q.get("explanation", ""),
                    starter_code=q.get("starter_code", ""),
                    test_cases_json=json.dumps(q.get("test_cases", []), ensure_ascii=False),
                    classic=True,
                    source=q.get("source", ""),
                )
                db.add(model)
        db.commit()
        logger.info("经典题库已同步到MySQL")

    # ---- 获取下一题 ----

    def get_next_question(
        self,
        user_id: str,
        knowledge_point: str,
        db: Session,
        profile = None,
        current_level: Optional[int] = None,
    ) -> dict:
        """获取下一道题（画像驱动 + MySQL持久化）

        流程：
        1. 确定难度等级（mastery优先 → 冷启动兜底）
        2. 画像感知决定题型权重
        3. 查MySQL经典题库 → 不够 → LLM动态生成并入库
        """
        from app.models.profile import QuestionModel

        mastery = 0.5
        is_cold_start = True  # 是否冷启动（知识树为空）

        if profile:
            m = profile.get_knowledge_mastery(knowledge_point)
            if profile.knowledge_tree:
                mastery = m
                is_cold_start = False
            # knowledge_tree 为空 → 冷启动

        if current_level is None:
            if is_cold_start:
                level = get_cold_start_level(profile)
            else:
                level = get_starting_level(mastery)
        else:
            level = current_level

        type_weights = self._get_type_weights(profile, level)

        # 查MySQL（有db时）或字典兜底（无db时）
        db_questions = None
        sample_question = None

        if db:
            db_questions = db.query(QuestionModel).filter(
                QuestionModel.knowledge_point == knowledge_point,
                QuestionModel.level == level,
            ).all()

        if db_questions:
            question = random.choice(db_questions)
            return {
                "question": self._model_to_dict(question),
                "level": level,
                "source": "classic" if question.classic else "generated",
                "is_cold_start": is_cold_start,
            }

        # 字典兜底：查经典题
        classic_list = CLASSIC_QUESTIONS.get(knowledge_point, [])
        classic_for_level = [q for q in classic_list if q["level"] == level]
        if classic_for_level:
            question = random.choice(classic_for_level)
            return {
                "question": question,
                "level": level,
                "source": "classic",
                "is_cold_start": is_cold_start,
            }

        # 没有匹配 → 查同一知识点其他级别的经典题作为样例
        if db:
            sample_question = db.query(QuestionModel).filter(
                QuestionModel.knowledge_point == knowledge_point,
                QuestionModel.classic == True,
            ).first()

        if not sample_question:
            sample = self._find_sample_question(knowledge_point)
        else:
            sample = self._model_to_dict(sample_question)

        chosen_type = random.choices(
            list(type_weights.keys()),
            weights=list(type_weights.values()),
            k=1,
        )[0]

        question = self._generate_question(
            knowledge_point=knowledge_point,
            level=level,
            question_type=chosen_type,
            sample=sample,
            mastery=mastery,
            db=db,
        )

        if question is None:
            # 降级：返回同一知识点任意级别题目（优先MySQL，其次字典）
            fallback = None
            if db:
                fallback = db.query(QuestionModel).filter(
                    QuestionModel.knowledge_point == knowledge_point,
                ).first()
            if fallback:
                return {
                    "question": self._model_to_dict(fallback),
                    "level": level,
                    "source": "classic",
                    "is_cold_start": is_cold_start,
                }
            # 字典兜底
            if classic_list:
                return {
                    "question": random.choice(classic_list),
                    "level": level,
                    "source": "classic",
                    "is_cold_start": is_cold_start,
                }
            return {
                "question": {
                    "id": f"fallback_{knowledge_point}",
                    "type": "choice",
                    "level": level,
                    "description": f"关于{knowledge_point}的基础概念题暂未准备好，请尝试其他知识点。",
                    "options": [],
                    "answer": "",
                    "explanation": "",
                },
                "level": level,
                "source": "fallback",
                "is_cold_start": is_cold_start,
            }

        return {
            "question": question,
            "level": level,
            "source": "generated",
            "is_cold_start": is_cold_start,
        }

    # ---- 保存答案 ----

    def record_answer(
        self,
        user_id: str,
        question_id: str,
        knowledge_point: str,
        user_answer: str,
        is_correct: bool,
        db: Session,
        level: int = 1,
        time_spent: int = 0,
    ) -> dict:
        """记录答题结果到MySQL

        Returns:
            {"consecutive_correct": int, "consecutive_wrong": int, "next_level": int}
        """
        from app.models.profile import AnswerRecordModel

        record = AnswerRecordModel(
            user_id=user_id,
            question_id=question_id,
            knowledge_point=knowledge_point,
            user_answer=user_answer,
            is_correct=is_correct,
            time_spent=time_spent,
            level_at_question=level,
        )
        db.add(record)
        db.commit()

        # 统计连续正确/错误
        records = db.query(AnswerRecordModel).filter(
            AnswerRecordModel.user_id == user_id,
            AnswerRecordModel.knowledge_point == knowledge_point,
        ).order_by(AnswerRecordModel.created_at.desc()).limit(10).all()

        consecutive_correct = 0
        consecutive_wrong = 0
        for r in records:
            if r.is_correct:
                if consecutive_wrong > 0:
                    break
                consecutive_correct += 1
            else:
                if consecutive_correct > 0:
                    break
                consecutive_wrong += 1

        # 确定下一题等级
        if consecutive_correct >= 2:
            next_level = min(level + 1, 3)
        elif consecutive_wrong >= 2:
            next_level = max(level - 1, 1)
        else:
            next_level = level

        return {
            "consecutive_correct": consecutive_correct,
            "consecutive_wrong": consecutive_wrong,
            "next_level": next_level,
        }

    @staticmethod
    def _model_to_dict(model) -> dict:
        """QuestionModel → dict"""
        return {
            "id": model.id,
            "type": model.type,
            "level": model.level,
            "difficulty": model.difficulty,
            "description": model.description,
            "options": json.loads(model.options_json) if model.options_json else [],
            "answer": model.answer,
            "explanation": model.explanation,
            "starter_code": model.starter_code,
            "test_cases": json.loads(model.test_cases_json) if model.test_cases_json else [],
            "classic": model.classic,
            "source": model.source,
            "knowledge_point": model.knowledge_point,
        }

    def _get_type_weights(self, profile, level: int) -> dict:
        """画像感知：根据画像调整题型权重

        ai_architecture_plan.md 画像感知映射：
        - 难度偏好=基础   → 概念题(choice/judge)权重×2
        - 难度偏好=进阶   → 分析题(analysis)权重×2
        - 难度偏好=挑战   → 编程题(code)权重×2
        - 认知风格=实践型 → 编程题占比50%+
        - 认知风格=视觉型 → 分析题占比提高
        - 认知风格=文字型 → 概念题为主
        - 当前阶段=备考   → 综合题型为主
        - 薄弱环节命中     → 概念题优先
        """
        weights = {t: 1.0 for t in LEVEL_CONFIG[level]["types"]}

        if profile is None:
            return weights

        # 安全解值
        def _safe_val(field, fallback=""):
            return field.value if hasattr(field, 'value') else str(field)

        diff = _safe_val(profile.difficulty_level)
        style = _safe_val(profile.cognitive_style)
        stage = _safe_val(profile.stage)
        weak_kps = [wp.knowledge_point for wp in (profile.weak_points or [])]

        # 1. 难度偏好 → 题型侧重
        if diff == "basic":
            for t in ("choice", "judge"):
                if t in weights:
                    weights[t] *= 2.0
        elif diff == "advanced":
            for t in ("analysis", "code"):
                if t in weights:
                    weights[t] *= 2.0
        # moderate/balanced: 不做调整，保持均衡

        # 2. 认知风格 → 题型侧重
        if style == "practical":
            if "code" in weights:
                weights["code"] *= 2.5  # 目标50%+
        elif style == "visual":
            if "analysis" in weights:
                weights["analysis"] *= 2.0
        elif style == "textual":
            if "choice" in weights:
                weights["choice"] *= 2.0

        # 3. 当前阶段 → 题型侧重
        if stage in ("review", "exam_prep"):
            # 备考模式：综合型为主
            for t in ("analysis", "code"):
                if t in weights:
                    weights[t] *= 1.8

        # 4. 薄弱环节 → 从概念题切入
        if weak_kps:
            for t in ("choice", "judge"):
                if t in weights:
                    weights[t] *= 1.5

        return weights

    def _get_profile_kp_strategy(self, profile, knowledge_point: str) -> dict:
        """画像驱动的知识点选择策略

        返回用于 batch 出题的知识点分配比例：
        {
            "primary_kp": str,           # 当前知识点（主出题方向）
            "weak_kps": list[str],       # 薄弱知识点（60%覆盖）
            "consolidated_kps": list[str],  # 已巩固知识点（10%间隔复习）
            "ratios": {"primary": 0.3, "weak": 0.6, "consolidated": 0.1}
        }
        """
        result = {
            "primary_kp": knowledge_point,
            "weak_kps": [],
            "consolidated_kps": [],
            "ratios": {"primary": 1.0, "weak": 0.0, "consolidated": 0.0},
        }

        if profile is None:
            return result

        # 薄弱知识点
        weak_kps = [wp.knowledge_point for wp in (profile.weak_points or [])]
        # 去掉当前知识点（避免重复）
        weak_kps = [kp for kp in weak_kps if kp != knowledge_point]
        result["weak_kps"] = weak_kps[:3]  # 最多取3个

        # 已巩固知识点（mastery > 0.7 且不在薄弱列表）
        if profile.knowledge_tree:
            consolidated = []
            for kp, node in profile.knowledge_tree.items():
                mastery = node.get("mastery", node) if isinstance(node, dict) else node
                if isinstance(mastery, (int, float)) and mastery > 0.7 and kp != knowledge_point and kp not in weak_kps:
                    consolidated.append(kp)
            result["consolidated_kps"] = consolidated[:2]  # 最多取2个

        # 动态计算比例
        has_weak = len(result["weak_kps"]) > 0
        has_consolidated = len(result["consolidated_kps"]) > 0

        if has_weak and has_consolidated:
            result["ratios"] = {"primary": 0.3, "weak": 0.6, "consolidated": 0.1}
        elif has_weak:
            result["ratios"] = {"primary": 0.4, "weak": 0.6, "consolidated": 0.0}
        elif has_consolidated:
            result["ratios"] = {"primary": 0.7, "weak": 0.0, "consolidated": 0.3}
        # else: 100% primary

        return result

    def _find_sample_question(self, knowledge_point: str) -> Optional[dict]:
        """找一个相近知识点的题目作为LLM生成的样例"""
        # 尝试找同一分类的其他题
        for kp, questions in CLASSIC_QUESTIONS.items():
            if questions:
                return questions[0]
        return None

    def _generate_question(
        self,
        knowledge_point: str,
        level: int,
        question_type: str,
        sample: Optional[dict],
        mastery: float,
        db: Session = None,
    ) -> Optional[dict]:
        """LLM动态生成题目 + 交叉验证

        最多重试3次，校验不通过则丢弃。
        """
        texts = get_all_knowledge_texts()
        kp_text = texts.get(knowledge_point, f"关于{knowledge_point}的知识点")
        node = get_knowledge_node(knowledge_point)
        kp_name = node.name if node else knowledge_point

        level_desc = LEVEL_CONFIG[level]

        sample_str = ""
        if sample:
            sample_str = f"""
## 参考样例（请模仿格式但生成不同题目）
{json.dumps(sample, ensure_ascii=False, indent=2)}
"""

        type_instructions = {
            "choice": "生成一道选择题。必须包含4个选项（options数组），其中只有1个正确答案。选项要有迷惑性。",
            "judge": "生成一道判断题。描述一句话，答案为正确或错误，需有解释。",
            "fill_blank": "生成一道填空题。用填空方式考察关键知识点，答案简短明确。",
            "analysis": "生成一道分析题。考察学生的理解深度，需要文字分析回答。答案要详细。",
            "code": "生成一道编程题。包含starter_code和至少2组test_cases。答案用解题思路描述。",
        }

        for attempt in range(3):
            try:
                prompt = f"""你是一个出题专家。请生成一道高质量的{kp_name}练习题。

## 题目要求
- 知识点：{kp_name}（ID: {knowledge_point}）
- 难度等级：{level_desc['name']}（Level {level}）
- 题目类型：{question_type}
- 学生掌握度：{mastery:.0%}
- {type_instructions.get(question_type, type_instructions['choice'])}

## 知识点背景
{kp_text[:800]}

{sample_str}

## 输出格式（严格JSON）
```json
{{
    "type": "{question_type}",
    "level": {level},
    "difficulty": {level},
    "description": "题目描述",
    "options": ["A", "B", "C", "D"],
    "answer": "正确答案",
    "explanation": "详细解析",
    "starter_code": "（仅编程题）",
    "test_cases": [{{"input": "", "expected": ""}}]
}}
```

只输出JSON，不要其他内容。"""

                result = llm_client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=2000,
                )

                # 尝试解析JSON
                result = result.strip()
                if result.startswith("```json"):
                    result = result[7:]
                if result.startswith("```"):
                    result = result[3:]
                if result.endswith("```"):
                    result = result[:-3]

                question = json.loads(result.strip())

                # 1. 格式校验
                if not self._validate_question(question, question_type):
                    logger.warning(f"题目格式校验失败（第{attempt+1}次），重新生成")
                    continue

                # 2. 交叉验证（第二个LLM独立作答）
                if not self._cross_validate_question(question, question_type):
                    logger.warning(f"题目交叉验证不通过（第{attempt+1}次），重新生成")
                    continue

                question["generated"] = True
                question["classic"] = False
                qid = f"gen_{knowledge_point}_{level}_{uuid.uuid4().hex[:8]}"
                question["id"] = qid
                # 写入MySQL
                if db:
                    self._save_question_to_db(db, question, knowledge_point)
                return question

            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析失败（第{attempt+1}次）: {e}")
            except Exception as e:
                logger.warning(f"LLM生成题目失败（第{attempt+1}次）: {e}")

        logger.error(f"3次重试均失败，无法生成{kp_name}的题目")
        return None

    def _validate_question(self, question: dict, question_type: str) -> bool:
        """格式校验：检查生成的题目结构是否合格

        返回True表示题目格式合格（字段完整、选项数正确等）。
        注意：格式校验通过后，还需交叉验证（第二个LLM独立作答）。
        """
        # 基本必填字段
        required = ["type", "description", "answer", "explanation"]
        for field in required:
            if field not in question or not str(question[field]).strip():
                logger.warning(f"缺少必填字段: {field}")
                return False

        # 选择题必须至少2个选项（allow 2 for T/F variants）and answer must be in options
        if question_type == "choice":
            options = question.get("options", [])
            if len(options) < 2:
                logger.warning(f"选择题选项数不足: {len(options)}")
                return False
            # 答案必须在选项中（精确匹配或去标点后匹配）
            answer_clean = str(question["answer"]).strip()
            if answer_clean not in options:
                # 去标点后再试
                found = False
                for opt in options:
                    if answer_clean.replace('，', '').replace('。', '').strip() == \
                       str(opt).replace('，', '').replace('。', '').strip():
                        found = True
                        question["answer"] = opt  # 标准化答案
                        break
                if not found:
                    logger.warning(f"选择题答案不在选项中: answer={answer_clean}, options={options}")
                    return False

        # 判断题答案必须是"正确"或"错误"
        if question_type == "judge":
            answer = str(question["answer"]).strip()
            if answer.startswith("正") or answer.startswith("True") or answer.startswith("true"):
                question["answer"] = "正确"
            elif answer.startswith("错") or answer.startswith("False") or answer.startswith("false"):
                question["answer"] = "错误"
            else:
                logger.warning(f"判断题答案格式不正确: {answer}")
                return False

        # 编程题必须有starter_code和test_cases
        if question_type == "code":
            if not question.get("starter_code"):
                logger.warning("编程题缺少starter_code")
                return False
            test_cases = question.get("test_cases", [])
            if len(test_cases) < 2:
                logger.warning(f"编程题测试用例不足: {len(test_cases)}")
                return False

        # description不能太短
        if len(str(question["description"])) < 10:
            logger.warning(f"题目描述太短")
            return False

        # explanation不能太短
        if len(str(question["explanation"])) < 20:
            logger.warning(f"题目解析太短")
            return False

        return True

    def _cross_validate_question(self, question: dict, question_type: str) -> bool:
        """交叉验证：第二个LLM独立作答，检查答案是否正确

        对照 ai_architecture_plan.md：
        - 选择/判断/填空：第二个LLM独立作答，比对答案
        - 编程题：暂不交叉验证（留待Phase 5沙箱执行）

        Returns:
            True: 交叉验证通过（LLM答案与题目答案一致）
            False: 交叉验证失败（LLM答案不一致或调用失败）
        """
        if question_type == "code":
            return True  # 编程题暂不交叉验证，Phase 5 沙箱执行

        # 构建不带答案的题目文本
        q_text = f"题目：{question['description']}"
        if question_type == "choice" and question.get("options"):
            labels = "ABCDEFGH"
            opts_str = "\n".join([f"{labels[i]}. {o}" for i, o in enumerate(question["options"])])
            q_text += f"\n选项：\n{opts_str}"
            q_text += "\n\n请选出正确答案，只输出选项字母或完整的选项文本。"

        elif question_type == "judge":
            q_text += '\n\n请判断对错，只输出\u201c正确\u201d或\u201c错误\u201d。'

        elif question_type == "fill_blank":
            q_text += "\n\n请填空，只输出答案内容。"

        elif question_type == "analysis":
            q_text += "\n\n请简要分析并给出答案，不超过200字。"

        try:
            validator_prompt = f"""你是一位助教，请回答以下题目。只输出答案，不要解释。

{q_text}"""

            llm_answer = llm_client.chat(
                messages=[{"role": "user", "content": validator_prompt}],
                temperature=0.1,  # 低温度，稳定输出
                max_tokens=300,
            )
            llm_answer = llm_answer.strip()

            if not llm_answer:
                logger.warning("交叉验证LLM返回空")
                return False

            # 比对答案
            stored_answer = str(question["answer"]).strip()

            if question_type == "choice":
                # 选项文本包含匹配
                if llm_answer == stored_answer:
                    return True
                if stored_answer in llm_answer or llm_answer in stored_answer:
                    return True
                # 去标点匹配
                if llm_answer.replace('，', '').replace('。', '').strip() == \
                   stored_answer.replace('，', '').replace('。', '').strip():
                    return True
                logger.warning(f"交叉验证不通过(choice): LLM={llm_answer[:50]}, Stored={stored_answer[:50]}")

            elif question_type == "judge":
                if llm_answer.startswith("正") and stored_answer.startswith("正"):
                    return True
                if llm_answer.startswith("错") and stored_answer.startswith("错"):
                    return True
                logger.warning(f"交叉验证不通过(judge): LLM={llm_answer}, Stored={stored_answer}")

            else:
                # 填空/分析题：关键词匹配
                llm_clean = llm_answer.lower().replace(' ', '')
                stored_clean = stored_answer.lower().replace(' ', '')
                if llm_clean == stored_clean:
                    return True
                if llm_clean in stored_clean or stored_clean in llm_clean:
                    return True
                # 关键词重叠率 > 50%
                stored_words = set(stored_clean.split(',')[0].split('，')[0].split())
                if stored_words:
                    match_count = sum(1 for w in stored_words if w in llm_clean)
                    if match_count >= len(stored_words) * 0.5:
                        return True
                logger.warning(f"交叉验证不通过(fill/analysis): LLM={llm_answer[:60]}, Stored={stored_answer[:60]}")

            return False

        except Exception as e:
            logger.warning(f"交叉验证LLM调用失败: {e}")
            return True  # 宽容策略：LLM调用失败时放行（避免阻塞）

    def _save_question_to_db(self, db: Session, question: dict, knowledge_point: str):
        """将生成的题目保存到MySQL"""
        from app.models.profile import QuestionModel
        try:
            model = QuestionModel(
                id=question["id"],
                knowledge_point=knowledge_point,
                type=question["type"],
                level=question["level"],
                difficulty=question.get("difficulty", question["level"]),
                description=question["description"],
                options_json=json.dumps(question.get("options", []), ensure_ascii=False),
                answer=question.get("answer", ""),
                explanation=question.get("explanation", ""),
                starter_code=question.get("starter_code", ""),
                test_cases_json=json.dumps(question.get("test_cases", []), ensure_ascii=False),
                classic=False,
                source="LLM生成",
            )
            db.add(model)
            db.commit()
        except Exception as e:
            logger.error(f"保存题目到MySQL失败: {e}")
            db.rollback()

    def get_answer(self, knowledge_point: str, question_id: str, db: Session = None) -> dict:
        """获取指定题目的答案和解析（从MySQL）"""
        if db:
            from app.models.profile import QuestionModel
            q = db.query(QuestionModel).filter(QuestionModel.id == question_id).first()
            if q:
                return {
                    "question_id": question_id,
                    "answer": q.answer,
                    "explanation": q.explanation,
                    "test_cases": json.loads(q.test_cases_json) if q.test_cases_json else [],
                }

        # 无db或找不到 → 查经典题字典兜底
        for qs in CLASSIC_QUESTIONS.values():
            for q in qs:
                if q["id"] == question_id:
                    return {
                        "question_id": question_id,
                        "answer": q.get("answer", ""),
                        "explanation": q.get("explanation", ""),
                        "test_cases": q.get("test_cases", []),
                    }

        return {
            "question_id": question_id,
            "answer": "",
            "explanation": "未找到该题目的答案",
        }

    def get_questions_by_level(
        self,
        knowledge_point: str,
        level: int,
        count: int = 3,
        db: Session = None,
    ) -> list[dict]:
        """获取指定知识点和难度等级的题目列表（从MySQL）"""
        if db:
            from app.models.profile import QuestionModel
            db_questions = db.query(QuestionModel).filter(
                QuestionModel.knowledge_point == knowledge_point,
                QuestionModel.level == level,
            ).limit(count).all()
            if len(db_questions) >= count:
                return [self._model_to_dict(q) for q in db_questions]

        # 经典题字典兜底
        classic = CLASSIC_QUESTIONS.get(knowledge_point, [])
        classic_for_level = [q for q in classic if q["level"] == level]
        questions = classic_for_level[:count]

        # 经典题不够 → LLM补充
        while len(questions) < count:
            q = self._generate_question(
                knowledge_point=knowledge_point,
                level=level,
                question_type=random.choice(LEVEL_CONFIG[level]["types"]),
                sample=classic[0] if classic else None,
                mastery=0.5,
                db=db,
            )
            if q:
                questions.append(q)
            else:
                break

        return questions[:count]

    def get_question_batch(
        self,
        user_id: str,
        knowledge_point: str,
        db: Session,
        profile = None,
        batch_size: int = 5,
    ) -> dict:
        """批量加载题目 + 画像驱动知识面分配

        画像策略（ai_architecture_plan.md）：
        - 60% 题目覆盖薄弱知识点
        - 10% 题目做已巩固知识点的间隔复习
        - 30% 当前知识点

        Returns:
            {
                "questions": [...],
                "total": int,
                "level": int,
                "source_summary": dict,
                "is_cold_start": bool,
                "strategy": dict,       # 画像策略元信息
            }
        """
        from app.models.profile import QuestionModel

        # 确定等级（同 get_next_question 的逻辑）
        is_cold_start = True
        mastery = 0.5
        level = 1

        if profile:
            m = profile.get_knowledge_mastery(knowledge_point)
            if profile.knowledge_tree:
                mastery = m
                is_cold_start = False

        if is_cold_start:
            level = get_cold_start_level(profile)
        else:
            level = get_starting_level(mastery)

        # 画像驱动的知识点分配策略
        kp_strategy = self._get_profile_kp_strategy(profile, knowledge_point)
        ratios = kp_strategy["ratios"]

        # 计算各来源的题目数
        primary_count = max(1, round(batch_size * ratios["primary"]))
        weak_count = round(batch_size * ratios["weak"])
        consolidated_count = batch_size - primary_count - weak_count

        questions = []
        source_summary = {"classic": 0, "generated": 0}

        def _fetch_from_kp(target_kp: str, target_level: int, needed: int) -> list:
            """从指定知识点取题"""
            fetched = []
            if not db or needed <= 0:
                return fetched

            db_qs = db.query(QuestionModel).filter(
                QuestionModel.knowledge_point == target_kp,
                QuestionModel.level == target_level,
            ).all()

            classic_qs = [q for q in db_qs if q.classic]
            generated_qs = [q for q in db_qs if not q.classic]
            random.shuffle(classic_qs)
            random.shuffle(generated_qs)

            for q in classic_qs:
                if len(fetched) >= needed:
                    break
                fetched.append(self._model_to_dict(q))
                source_summary["classic"] += 1
            for q in generated_qs:
                if len(fetched) >= needed:
                    break
                fetched.append(self._model_to_dict(q))
                source_summary["generated"] += 1

            # 还不够 → 字典兜底
            if len(fetched) < needed:
                classic_list = CLASSIC_QUESTIONS.get(target_kp, [])
                for q in classic_list:
                    if len(fetched) >= needed:
                        break
                    if q["level"] == target_level:
                        fetched.append(q)
                        source_summary["classic"] += 1

            return fetched

        # 1. 当前知识点题目
        primary_qs = _fetch_from_kp(knowledge_point, level, primary_count)
        questions.extend(primary_qs)

        # 不足 → LLM生成补充
        type_weights = self._get_type_weights(profile, level)
        db_questions = db.query(QuestionModel).filter(
            QuestionModel.knowledge_point == knowledge_point,
            QuestionModel.level == level,
        ).all() if db else []
        classic_qs_for_sample = [q for q in db_questions if q.classic]
        sample = self._model_to_dict(classic_qs_for_sample[0]) if classic_qs_for_sample else self._find_sample_question(knowledge_point)

        while len([q for q in questions if q.get("knowledge_point", knowledge_point) == knowledge_point]) < primary_count:
            chosen_type = random.choices(
                list(type_weights.keys()),
                weights=list(type_weights.values()),
                k=1,
            )[0]
            q = self._generate_question(
                knowledge_point=knowledge_point,
                level=level,
                question_type=chosen_type,
                sample=sample,
                mastery=mastery,
                db=db,
            )
            if q:
                q["knowledge_point"] = knowledge_point
                questions.append(q)
                source_summary["generated"] += 1
            else:
                break

        # 2. 薄弱知识点题目（60%）
        for wk in kp_strategy["weak_kps"]:
            if weak_count <= 0:
                break
            # 薄弱点从L1开始
            wk_qs = _fetch_from_kp(wk, 1, min(weak_count, 3))
            for q in wk_qs:
                q["knowledge_point"] = wk
                q["from_strategy"] = "weak"
            questions.extend(wk_qs)
            weak_count -= len(wk_qs)

        # 3. 已巩固知识点间隔复习（10%）
        for ck in kp_strategy["consolidated_kps"]:
            if consolidated_count <= 0:
                break
            # 复习用较低难度（L2或L1）
            ck_qs = _fetch_from_kp(ck, 2, min(consolidated_count, 2))
            if not ck_qs:
                ck_qs = _fetch_from_kp(ck, 1, min(consolidated_count, 2))
            for q in ck_qs:
                q["knowledge_point"] = ck
                q["from_strategy"] = "review"
            questions.extend(ck_qs)
            consolidated_count -= len(ck_qs)

        # 限制总量
        questions = questions[:batch_size]

        return {
            "questions": questions,
            "total": len(questions),
            "level": level,
            "source_summary": source_summary,
            "is_cold_start": is_cold_start,
            "strategy": {
                "ratios": ratios,
                "weak_kps": kp_strategy["weak_kps"],
                "consolidated_kps": kp_strategy["consolidated_kps"],
                "primary_count": primary_count,
                "weak_count": sum(1 for q in questions if q.get("from_strategy") == "weak"),
                "review_count": sum(1 for q in questions if q.get("from_strategy") == "review"),
            },
        }


# 全局单例
question_service = QuestionService()
