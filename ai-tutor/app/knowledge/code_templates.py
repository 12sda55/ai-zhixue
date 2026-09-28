CODE_TEMPLATES = {
    "array": [
        {
            "id": "array_template_1",
            "title": "数组基本操作",
            "description": "实现数组的插入、删除、查找操作",
            "code": (
                "class MyArray:\n"
                "    def __init__(self):\n"
                "        self.data = []\n"
                "\n"
                "    def insert(self, index, value):\n"
                "        # 在指定位置插入元素\n"
                "        self.data.insert(index, value)\n"
                "\n"
                "    def delete(self, index):\n"
                "        # 删除指定位置的元素并返回\n"
                "        return self.data.pop(index)\n"
                "\n"
                "    def search(self, value):\n"
                "        # 查找元素，返回索引，不存在则返回-1\n"
                "        try:\n"
                "            return self.data.index(value)\n"
                "        except ValueError:\n"
                "            return -1\n"
                "\n"
                "    def get_size(self):\n"
                "        return len(self.data)\n"
            ),
            "test_cases": [
                {"input": "arr=MyArray(); arr.insert(0,1); arr.insert(1,2); arr.search(2)", "expected": "1"},
                {"input": "arr=MyArray(); arr.insert(0,1); arr.insert(1,2); arr.delete(0); arr.search(1)", "expected": "0"},
                {"input": "arr=MyArray(); arr.insert(0,5); arr.search(3)", "expected": "-1"},
            ],
            "difficulty": 1,
            "blanks": [
                {"line": 6, "hint": "使用list的insert方法在指定位置插入元素"},
                {"line": 10, "hint": "使用list的pop方法删除并返回指定位置元素"},
                {"line": 14, "hint": "使用list的index方法查找元素索引"},
            ],
        },
        {
            "id": "array_template_2",
            "title": "双指针删除有序数组重复项",
            "description": "使用双指针技巧原地删除有序数组中的重复元素，返回新长度",
            "code": (
                "def remove_duplicates(nums):\n"
                "    # 如果数组为空，直接返回0\n"
                "    if not nums:\n"
                "        return 0\n"
                "    # 慢指针，指向不重复元素的最后位置\n"
                "    slow = 0\n"
                "    # 快指针遍历数组\n"
                "    for fast in range(1, len(nums)):\n"
                "        # 当快指针发现不同元素时\n"
                "        if nums[fast] != nums[slow]:\n"
                "            # 慢指针前移，并将新元素放入\n"
                "            slow += 1\n"
                "            nums[slow] = nums[fast]\n"
                "    # 返回不重复元素的长度\n"
                "    return slow + 1\n"
            ),
            "test_cases": [
                {"input": "nums=[1,1,2]; remove_duplicates(nums)", "expected": "2"},
                {"input": "nums=[0,0,1,1,1,2,2,3,3,4]; remove_duplicates(nums)", "expected": "5"},
                {"input": "nums=[1]; remove_duplicates(nums)", "expected": "1"},
            ],
            "difficulty": 2,
            "blanks": [
                {"line": 9, "hint": "比较快指针和慢指针位置的元素是否不同"},
                {"line": 12, "hint": "慢指针先前移一位"},
                {"line": 13, "hint": "将快指针处的新元素赋值到慢指针位置"},
            ],
        },
        {
            "id": "array_template_3",
            "title": "滑动窗口求最大子数组和",
            "description": "使用滑动窗口技巧求固定大小k的子数组的最大和",
            "code": (
                "def max_subarray_sum(nums, k):\n"
                "    # 如果数组长度小于k，返回None\n"
                "    if len(nums) < k:\n"
                "        return None\n"
                "    # 计算第一个窗口的和\n"
                "    window_sum = sum(nums[:k])\n"
                "    max_sum = window_sum\n"
                "    # 滑动窗口，每次移除左边元素，加入右边元素\n"
                "    for i in range(k, len(nums)):\n"
                "        # 窗口滑动：减去离开窗口的元素，加上新进入窗口的元素\n"
                "        window_sum = window_sum - nums[i - k] + nums[i]\n"
                "        # 更新最大和\n"
                "        if window_sum > max_sum:\n"
                "            max_sum = window_sum\n"
                "    return max_sum\n"
            ),
            "test_cases": [
                {"input": "max_subarray_sum([2,1,5,1,3,2], 3)", "expected": "9"},
                {"input": "max_subarray_sum([2,3,4,1,5], 2)", "expected": "7"},
                {"input": "max_subarray_sum([1,2], 3)", "expected": "None"},
            ],
            "difficulty": 3,
            "blanks": [
                {"line": 10, "hint": "窗口滑动时减去离开的元素，加上新进入的元素"},
                {"line": 12, "hint": "如果当前窗口和更大，则更新最大值"},
            ],
        },
    ],

    "linked_list": [
        {
            "id": "linked_list_template_1",
            "title": "单链表基本操作",
            "description": "实现单链表的创建、插入、删除和查找操作",
            "code": (
                "class ListNode:\n"
                "    def __init__(self, val=0, next=None):\n"
                "        self.val = val\n"
                "        self.next = next\n"
                "\n"
                "class MyLinkedList:\n"
                "    def __init__(self):\n"
                "        self.head = None\n"
                "        self.size = 0\n"
                "\n"
                "    def add_at_head(self, val):\n"
                "        # 在头部插入节点\n"
                "        new_node = ListNode(val)\n"
                "        new_node.next = self.head\n"
                "        self.head = new_node\n"
                "        self.size += 1\n"
                "\n"
                "    def add_at_tail(self, val):\n"
                "        # 在尾部插入节点\n"
                "        new_node = ListNode(val)\n"
                "        if not self.head:\n"
                "            self.head = new_node\n"
                "        else:\n"
                "            cur = self.head\n"
                "            while cur.next:\n"
                "                cur = cur.next\n"
                "            cur.next = new_node\n"
                "        self.size += 1\n"
                "\n"
                "    def search(self, val):\n"
                "        # 查找值为val的节点，返回索引\n"
                "        cur = self.head\n"
                "        index = 0\n"
                "        while cur:\n"
                "            if cur.val == val:\n"
                "                return index\n"
                "            cur = cur.next\n"
                "            index += 1\n"
                "        return -1\n"
            ),
            "test_cases": [
                {"input": "ll=MyLinkedList(); ll.add_at_head(1); ll.add_at_head(2); ll.search(1)", "expected": "1"},
                {"input": "ll=MyLinkedList(); ll.add_at_tail(3); ll.add_at_tail(5); ll.search(5)", "expected": "1"},
                {"input": "ll=MyLinkedList(); ll.search(1)", "expected": "-1"},
            ],
            "difficulty": 2,
            "blanks": [
                {"line": 13, "hint": "新节点的next指向当前头节点"},
                {"line": 14, "hint": "更新头节点为新节点"},
                {"line": 21, "hint": "遍历到链表末尾，cur.next为None时停止"},
                {"line": 30, "hint": "比较当前节点值与目标值"},
            ],
        },
        {
            "id": "linked_list_template_2",
            "title": "反转链表",
            "description": "迭代法反转单链表",
            "code": (
                "class ListNode:\n"
                "    def __init__(self, val=0, next=None):\n"
                "        self.val = val\n"
                "        self.next = next\n"
                "\n"
                "def reverse_list(head):\n"
                "    # 前驱节点，初始为None\n"
                "    prev = None\n"
                "    curr = head\n"
                "    while curr:\n"
                "        # 暂存当前节点的下一个节点\n"
                "        next_node = curr.next\n"
                "        # 反转：当前节点指向前驱\n"
                "        curr.next = prev\n"
                "        # 前驱和当前指针后移\n"
                "        prev = curr\n"
                "        curr = next_node\n"
                "    # 返回新的头节点\n"
                "    return prev\n"
                "\n"
                "def list_to_linked(lst):\n"
                "    dummy = ListNode(0)\n"
                "    cur = dummy\n"
                "    for v in lst:\n"
                "        cur.next = ListNode(v)\n"
                "        cur = cur.next\n"
                "    return dummy.next\n"
                "\n"
                "def linked_to_list(head):\n"
                "    result = []\n"
                "    while head:\n"
                "        result.append(head.val)\n"
                "        head = head.next\n"
                "    return result\n"
            ),
            "test_cases": [
                {"input": "linked_to_list(reverse_list(list_to_linked([1,2,3,4,5])))", "expected": "[5, 4, 3, 2, 1]"},
                {"input": "linked_to_list(reverse_list(list_to_linked([1,2])))", "expected": "[2, 1]"},
                {"input": "linked_to_list(reverse_list(list_to_linked([])))", "expected": "[]"},
            ],
            "difficulty": 2,
            "blanks": [
                {"line": 12, "hint": "暂存当前节点的下一个节点，防止断链"},
                {"line": 14, "hint": "将当前节点的next指向前驱节点，完成反转"},
                {"line": 16, "hint": "前驱指针后移到当前节点"},
                {"line": 17, "hint": "当前指针后移到暂存的下一个节点"},
            ],
        },
        {
            "id": "linked_list_template_3",
            "title": "链表环检测",
            "description": "使用快慢指针检测链表中是否存在环",
            "code": (
                "class ListNode:\n"
                "    def __init__(self, val=0, next=None):\n"
                "        self.val = val\n"
                "        self.next = next\n"
                "\n"
                "def has_cycle(head):\n"
                "    # 快慢指针都从头部开始\n"
                "    slow = head\n"
                "    fast = head\n"
                "    # 快指针每次走两步，慢指针每次走一步\n"
                "    while fast and fast.next:\n"
                "        slow = slow.next\n"
                "        # 快指针走两步\n"
                "        fast = fast.next.next\n"
                "        # 如果快慢指针相遇，说明有环\n"
                "        if slow == fast:\n"
                "            return True\n"
                "    # 快指针到达末尾，无环\n"
                "    return False\n"
            ),
            "test_cases": [
                {"input": "n1=ListNode(1); n2=ListNode(2); n1.next=n2; n2.next=n1; has_cycle(n1)", "expected": "True"},
                {"input": "n1=ListNode(1); n2=ListNode(2); n1.next=n2; has_cycle(n1)", "expected": "False"},
                {"input": "has_cycle(None)", "expected": "False"},
            ],
            "difficulty": 3,
            "blanks": [
                {"line": 12, "hint": "慢指针每次走一步"},
                {"line": 14, "hint": "快指针每次走两步"},
                {"line": 16, "hint": "如果快慢指针相遇，说明存在环"},
            ],
        },
    ],

    "stack": [
        {
            "id": "stack_template_1",
            "title": "栈的基本操作",
            "description": "实现栈的入栈、出栈、查看栈顶和判空操作",
            "code": (
                "class MyStack:\n"
                "    def __init__(self):\n"
                "        self.items = []\n"
                "\n"
                "    def push(self, item):\n"
                "        # 入栈：将元素添加到列表末尾\n"
                "        self.items.append(item)\n"
                "\n"
                "    def pop(self):\n"
                "        # 出栈：移除并返回栈顶元素\n"
                "        if self.is_empty():\n"
                "            return None\n"
                "        return self.items.pop()\n"
                "\n"
                "    def peek(self):\n"
                "        # 查看栈顶元素但不移除\n"
                "        if self.is_empty():\n"
                "            return None\n"
                "        return self.items[-1]\n"
                "\n"
                "    def is_empty(self):\n"
                "        return len(self.items) == 0\n"
                "\n"
                "    def size(self):\n"
                "        return len(self.items)\n"
            ),
            "test_cases": [
                {"input": "s=MyStack(); s.push(1); s.push(2); s.pop()", "expected": "2"},
                {"input": "s=MyStack(); s.push(3); s.peek()", "expected": "3"},
                {"input": "s=MyStack(); s.is_empty()", "expected": "True"},
            ],
            "difficulty": 1,
            "blanks": [
                {"line": 6, "hint": "使用append方法将元素添加到栈顶"},
                {"line": 12, "hint": "使用pop方法移除并返回栈顶元素"},
                {"line": 18, "hint": "使用负索引-1获取栈顶元素"},
            ],
        },
        {
            "id": "stack_template_2",
            "title": "有效的括号",
            "description": "判断一个只包含括号的字符串是否有效，括号必须正确配对和嵌套",
            "code": (
                "def is_valid_parentheses(s):\n"
                "    # 使用栈来匹配括号\n"
                "    stack = []\n"
                "    # 括号配对映射\n"
                "    mapping = {')': '(', ']': '[', '}': '{'}\n"
                "    for char in s:\n"
                "        if char in mapping:\n"
                "            # 如果是右括号，检查栈顶是否匹配\n"
                "            top = stack.pop() if stack else '#'\n"
                "            if mapping[char] != top:\n"
                "                return False\n"
                "        else:\n"
                "            # 如果是左括号，入栈\n"
                "            stack.append(char)\n"
                "    # 栈为空说明所有括号都匹配\n"
                "    return not stack\n"
            ),
            "test_cases": [
                {"input": "is_valid_parentheses('()')", "expected": "True"},
                {"input": "is_valid_parentheses('()[]{}')", "expected": "True"},
                {"input": "is_valid_parentheses('(]')", "expected": "False"},
                {"input": "is_valid_parentheses('([)]')", "expected": "False"},
            ],
            "difficulty": 2,
            "blanks": [
                {"line": 5, "hint": "建立右括号到左括号的映射字典"},
                {"line": 9, "hint": "弹出栈顶元素，如果栈为空则用占位符"},
                {"line": 10, "hint": "检查栈顶元素是否与当前右括号匹配"},
                {"line": 14, "hint": "左括号入栈等待匹配"},
            ],
        },
        {
            "id": "stack_template_3",
            "title": "逆波兰表达式求值",
            "description": "使用栈计算逆波兰表达式（后缀表达式）的值",
            "code": (
                "def eval_rpn(tokens):\n"
                "    stack = []\n"
                "    for token in tokens:\n"
                "        if token in '+-*/':\n"
                "            # 遇到运算符，弹出两个操作数\n"
                "            b = stack.pop()\n"
                "            a = stack.pop()\n"
                "            # 根据运算符进行计算\n"
                "            if token == '+':\n"
                "                stack.append(a + b)\n"
                "            elif token == '-':\n"
                "                stack.append(a - b)\n"
                "            elif token == '*':\n"
                "                stack.append(a * b)\n"
                "            elif token == '/':\n"
                "                # 整数除法向零取整\n"
                "                stack.append(int(a / b))\n"
                "        else:\n"
                "            # 遇到数字，入栈\n"
                "            stack.append(int(token))\n"
                "    return stack[0]\n"
            ),
            "test_cases": [
                {"input": "eval_rpn(['2','1','+','3','*'])", "expected": "9"},
                {"input": "eval_rpn(['4','13','5','/','+'])", "expected": "6"},
                {"input": "eval_rpn(['10','6','9','3','+','-11','*','/','*','17','+','5','+'])", "expected": "22"},
            ],
            "difficulty": 3,
            "blanks": [
                {"line": 6, "hint": "先弹出的是右操作数"},
                {"line": 7, "hint": "后弹出的是左操作数"},
                {"line": 17, "hint": "整数除法需要向零取整，使用int(a/b)"},
            ],
        },
    ],

    "queue": [
        {
            "id": "queue_template_1",
            "title": "队列基本操作",
            "description": "实现队列的入队、出队、查看队首和判空操作",
            "code": (
                "class MyQueue:\n"
                "    def __init__(self):\n"
                "        self.items = []\n"
                "\n"
                "    def enqueue(self, item):\n"
                "        # 入队：元素添加到队尾\n"
                "        self.items.append(item)\n"
                "\n"
                "    def dequeue(self):\n"
                "        # 出队：移除并返回队首元素\n"
                "        if self.is_empty():\n"
                "            return None\n"
                "        return self.items.pop(0)\n"
                "\n"
                "    def front(self):\n"
                "        # 查看队首元素\n"
                "        if self.is_empty():\n"
                "            return None\n"
                "        return self.items[0]\n"
                "\n"
                "    def is_empty(self):\n"
                "        return len(self.items) == 0\n"
                "\n"
                "    def size(self):\n"
                "        return len(self.items)\n"
            ),
            "test_cases": [
                {"input": "q=MyQueue(); q.enqueue(1); q.enqueue(2); q.dequeue()", "expected": "1"},
                {"input": "q=MyQueue(); q.enqueue(3); q.front()", "expected": "3"},
                {"input": "q=MyQueue(); q.is_empty()", "expected": "True"},
            ],
            "difficulty": 1,
            "blanks": [
                {"line": 6, "hint": "使用append方法将元素添加到队尾"},
                {"line": 12, "hint": "使用pop(0)移除队首元素"},
                {"line": 18, "hint": "使用索引0获取队首元素"},
            ],
        },
        {
            "id": "queue_template_2",
            "title": "循环队列",
            "description": "使用固定大小数组实现循环队列",
            "code": (
                "class CircularQueue:\n"
                "    def __init__(self, k):\n"
                "        self.capacity = k\n"
                "        self.data = [None] * k\n"
                "        self.front = 0\n"
                "        self.rear = 0\n"
                "        self.size = 0\n"
                "\n"
                "    def enqueue(self, value):\n"
                "        # 队列满时返回False\n"
                "        if self.size == self.capacity:\n"
                "            return False\n"
                "        # 在rear位置插入元素\n"
                "        self.data[self.rear] = value\n"
                "        # rear循环后移\n"
                "        self.rear = (self.rear + 1) % self.capacity\n"
                "        self.size += 1\n"
                "        return True\n"
                "\n"
                "    def dequeue(self):\n"
                "        # 队列空时返回False\n"
                "        if self.size == 0:\n"
                "            return False\n"
                "        # front循环后移\n"
                "        self.front = (self.front + 1) % self.capacity\n"
                "        self.size -= 1\n"
                "        return True\n"
                "\n"
                "    def get_front(self):\n"
                "        if self.size == 0:\n"
                "            return -1\n"
                "        return self.data[self.front]\n"
                "\n"
                "    def get_rear(self):\n"
                "        if self.size == 0:\n"
                "            return -1\n"
                "        return self.data[(self.rear - 1) % self.capacity]\n"
            ),
            "test_cases": [
                {"input": "cq=CircularQueue(3); cq.enqueue(1); cq.enqueue(2); cq.get_front()", "expected": "1"},
                {"input": "cq=CircularQueue(3); cq.enqueue(1); cq.enqueue(2); cq.enqueue(3); cq.enqueue(4)", "expected": "False"},
                {"input": "cq=CircularQueue(3); cq.enqueue(1); cq.enqueue(2); cq.dequeue(); cq.get_front()", "expected": "2"},
            ],
            "difficulty": 2,
            "blanks": [
                {"line": 14, "hint": "在rear位置放入新元素"},
                {"line": 16, "hint": "rear循环后移，使用取模运算实现循环"},
                {"line": 24, "hint": "front循环后移，使用取模运算实现循环"},
            ],
        },
    ],

    "hash_table": [
        {
            "id": "hash_table_template_1",
            "title": "哈希表实现（链地址法）",
            "description": "使用链地址法解决哈希冲突，实现哈希表的插入、查找和删除",
            "code": (
                "class MyHashTable:\n"
                "    def __init__(self, capacity=10):\n"
                "        self.capacity = capacity\n"
                "        # 每个桶是一个列表，用于链地址法\n"
                "        self.buckets = [[] for _ in range(capacity)]\n"
                "\n"
                "    def _hash(self, key):\n"
                "        # 计算哈希值\n"
                "        return hash(key) % self.capacity\n"
                "\n"
                "    def put(self, key, value):\n"
                "        # 插入或更新键值对\n"
                "        index = self._hash(key)\n"
                "        for i, (k, v) in enumerate(self.buckets[index]):\n"
                "            if k == key:\n"
                "                # 键已存在，更新值\n"
                "                self.buckets[index][i] = (key, value)\n"
                "                return\n"
                "        # 键不存在，添加新键值对\n"
                "        self.buckets[index].append((key, value))\n"
                "\n"
                "    def get(self, key):\n"
                "        # 查找键对应的值\n"
                "        index = self._hash(key)\n"
                "        for k, v in self.buckets[index]:\n"
                "            if k == key:\n"
                "                return v\n"
                "        return None\n"
                "\n"
                "    def remove(self, key):\n"
                "        # 删除键值对\n"
                "        index = self._hash(key)\n"
                "        for i, (k, v) in enumerate(self.buckets[index]):\n"
                "            if k == key:\n"
                "                del self.buckets[index][i]\n"
                "                return True\n"
                "        return False\n"
            ),
            "test_cases": [
                {"input": "ht=MyHashTable(); ht.put('a',1); ht.put('b',2); ht.get('a')", "expected": "1"},
                {"input": "ht=MyHashTable(); ht.put('a',1); ht.put('a',3); ht.get('a')", "expected": "3"},
                {"input": "ht=MyHashTable(); ht.put('a',1); ht.remove('a'); ht.get('a')", "expected": "None"},
            ],
            "difficulty": 2,
            "blanks": [
                {"line": 9, "hint": "使用hash函数和取模计算桶索引"},
                {"line": 16, "hint": "键已存在时更新对应的值"},
                {"line": 19, "hint": "键不存在时将新键值对追加到桶中"},
                {"line": 26, "hint": "在桶中遍历查找匹配的键"},
            ],
        },
        {
            "id": "hash_table_template_2",
            "title": "两数之和",
            "description": "使用哈希表在数组中找到两个数使其和等于目标值",
            "code": (
                "def two_sum(nums, target):\n"
                "    # 哈希表存储：值->索引\n"
                "    hash_map = {}\n"
                "    for i, num in enumerate(nums):\n"
                "        # 计算需要的补数\n"
                "        complement = target - num\n"
                "        # 检查补数是否已在哈希表中\n"
                "        if complement in hash_map:\n"
                "            return [hash_map[complement], i]\n"
                "        # 将当前数及其索引存入哈希表\n"
                "        hash_map[num] = i\n"
                "    return []\n"
            ),
            "test_cases": [
                {"input": "two_sum([2,7,11,15], 9)", "expected": "[0, 1]"},
                {"input": "two_sum([3,2,4], 6)", "expected": "[1, 2]"},
                {"input": "two_sum([3,3], 6)", "expected": "[0, 1]"},
            ],
            "difficulty": 2,
            "blanks": [
                {"line": 6, "hint": "补数 = 目标值 - 当前数"},
                {"line": 8, "hint": "检查补数是否已在哈希表中"},
                {"line": 9, "hint": "返回补数的索引和当前索引"},
                {"line": 11, "hint": "将当前数及其索引存入哈希表"},
            ],
        },
    ],

    "binary_tree": [
        {
            "id": "binary_tree_template_1",
            "title": "二叉树遍历",
            "description": "实现二叉树的前序、中序、后序遍历",
            "code": (
                "class TreeNode:\n"
                "    def __init__(self, val=0, left=None, right=None):\n"
                "        self.val = val\n"
                "        self.left = left\n"
                "        self.right = right\n"
                "\n"
                "def preorder(root):\n"
                "    # 前序遍历：根->左->右\n"
                "    result = []\n"
                "    def traverse(node):\n"
                "        if not node:\n"
                "            return\n"
                "        result.append(node.val)\n"
                "        traverse(node.left)\n"
                "        traverse(node.right)\n"
                "    traverse(root)\n"
                "    return result\n"
                "\n"
                "def inorder(root):\n"
                "    # 中序遍历：左->根->右\n"
                "    result = []\n"
                "    def traverse(node):\n"
                "        if not node:\n"
                "            return\n"
                "        traverse(node.left)\n"
                "        result.append(node.val)\n"
                "        traverse(node.right)\n"
                "    traverse(root)\n"
                "    return result\n"
                "\n"
                "def postorder(root):\n"
                "    # 后序遍历：左->右->根\n"
                "    result = []\n"
                "    def traverse(node):\n"
                "        if not node:\n"
                "            return\n"
                "        traverse(node.left)\n"
                "        traverse(node.right)\n"
                "        result.append(node.val)\n"
                "    traverse(root)\n"
                "    return result\n"
            ),
            "test_cases": [
                {"input": "root=TreeNode(1,TreeNode(2,TreeNode(4),TreeNode(5)),TreeNode(3)); preorder(root)", "expected": "[1, 2, 4, 5, 3]"},
                {"input": "root=TreeNode(1,TreeNode(2,TreeNode(4),TreeNode(5)),TreeNode(3)); inorder(root)", "expected": "[4, 2, 5, 1, 3]"},
                {"input": "root=TreeNode(1,TreeNode(2,TreeNode(4),TreeNode(5)),TreeNode(3)); postorder(root)", "expected": "[4, 5, 2, 3, 1]"},
            ],
            "difficulty": 2,
            "blanks": [
                {"line": 13, "hint": "前序遍历先访问根节点"},
                {"line": 14, "hint": "然后递归遍历左子树"},
                {"line": 15, "hint": "最后递归遍历右子树"},
                {"line": 27, "hint": "中序遍历在遍历左子树后访问根节点"},
                {"line": 40, "hint": "后序遍历在遍历左右子树后访问根节点"},
            ],
        },
        {
            "id": "binary_tree_template_2",
            "title": "二叉树层序遍历",
            "description": "使用队列实现二叉树的层序遍历（BFS）",
            "code": (
                "from collections import deque\n"
                "\n"
                "class TreeNode:\n"
                "    def __init__(self, val=0, left=None, right=None):\n"
                "        self.val = val\n"
                "        self.left = left\n"
                "        self.right = right\n"
                "\n"
                "def level_order(root):\n"
                "    if not root:\n"
                "        return []\n"
                "    result = []\n"
                "    # 使用双端队列进行BFS\n"
                "    queue = deque([root])\n"
                "    while queue:\n"
                "        level_size = len(queue)\n"
                "        current_level = []\n"
                "        # 遍历当前层的所有节点\n"
                "        for _ in range(level_size):\n"
                "            node = queue.popleft()\n"
                "            current_level.append(node.val)\n"
                "            # 将子节点加入队列\n"
                "            if node.left:\n"
                "                queue.append(node.left)\n"
                "            if node.right:\n"
                "                queue.append(node.right)\n"
                "        result.append(current_level)\n"
                "    return result\n"
            ),
            "test_cases": [
                {"input": "root=TreeNode(3,TreeNode(9),TreeNode(20,TreeNode(15),TreeNode(7))); level_order(root)", "expected": "[[3], [9, 20], [15, 7]]"},
                {"input": "root=TreeNode(1); level_order(root)", "expected": "[[1]]"},
                {"input": "level_order(None)", "expected": "[]"},
            ],
            "difficulty": 2,
            "blanks": [
                {"line": 14, "hint": "使用deque初始化队列，将根节点入队"},
                {"line": 20, "hint": "从队列左端弹出节点"},
                {"line": 24, "hint": "将左子节点加入队列"},
                {"line": 26, "hint": "将右子节点加入队列"},
            ],
        },
    ],

    "bst": [
        {
            "id": "bst_template_1",
            "title": "二叉搜索树的插入与查找",
            "description": "实现BST的插入和查找操作",
            "code": (
                "class TreeNode:\n"
                "    def __init__(self, val=0, left=None, right=None):\n"
                "        self.val = val\n"
                "        self.left = left\n"
                "        self.right = right\n"
                "\n"
                "class BST:\n"
                "    def __init__(self):\n"
                "        self.root = None\n"
                "\n"
                "    def insert(self, val):\n"
                "        # 插入新值到BST中\n"
                "        self.root = self._insert(self.root, val)\n"
                "\n"
                "    def _insert(self, node, val):\n"
                "        if not node:\n"
                "            return TreeNode(val)\n"
                "        if val < node.val:\n"
                "            # 值小于当前节点，插入左子树\n"
                "            node.left = self._insert(node.left, val)\n"
                "        elif val > node.val:\n"
                "            # 值大于当前节点，插入右子树\n"
                "            node.right = self._insert(node.right, val)\n"
                "        return node\n"
                "\n"
                "    def search(self, val):\n"
                "        # 在BST中查找值\n"
                "        return self._search(self.root, val)\n"
                "\n"
                "    def _search(self, node, val):\n"
                "        if not node:\n"
                "            return False\n"
                "        if val == node.val:\n"
                "            return True\n"
                "        elif val < node.val:\n"
                "            # 值小于当前节点，在左子树中查找\n"
                "            return self._search(node.left, val)\n"
                "        else:\n"
                "            # 值大于当前节点，在右子树中查找\n"
                "            return self._search(node.right, val)\n"
            ),
            "test_cases": [
                {"input": "bst=BST(); bst.insert(5); bst.insert(3); bst.insert(7); bst.search(3)", "expected": "True"},
                {"input": "bst=BST(); bst.insert(5); bst.insert(3); bst.insert(7); bst.search(4)", "expected": "False"},
                {"input": "bst=BST(); bst.search(1)", "expected": "False"},
            ],
            "difficulty": 2,
            "blanks": [
                {"line": 20, "hint": "值小于当前节点时，递归插入左子树"},
                {"line": 23, "hint": "值大于当前节点时，递归插入右子树"},
                {"line": 35, "hint": "值等于当前节点，查找成功"},
                {"line": 38, "hint": "值小于当前节点，在左子树中继续查找"},
            ],
        },
        {
            "id": "bst_template_2",
            "title": "二叉搜索树的删除",
            "description": "实现BST的删除操作，处理叶子节点、单子节点和双子节点三种情况",
            "code": (
                "class TreeNode:\n"
                "    def __init__(self, val=0, left=None, right=None):\n"
                "        self.val = val\n"
                "        self.left = left\n"
                "        self.right = right\n"
                "\n"
                "def delete_node(root, key):\n"
                "    if not root:\n"
                "        return None\n"
                "    # 查找要删除的节点\n"
                "    if key < root.val:\n"
                "        root.left = delete_node(root.left, key)\n"
                "    elif key > root.val:\n"
                "        root.right = delete_node(root.right, key)\n"
                "    else:\n"
                "        # 找到要删除的节点\n"
                "        # 情况1：叶子节点或只有一个子节点\n"
                "        if not root.left:\n"
                "            return root.right\n"
                "        if not root.right:\n"
                "            return root.left\n"
                "        # 情况2：有两个子节点\n"
                "        # 找右子树的最小值节点（后继节点）\n"
                "        min_node = find_min(root.right)\n"
                "        root.val = min_node.val\n"
                "        # 删除右子树中的最小值节点\n"
                "        root.right = delete_node(root.right, min_node.val)\n"
                "    return root\n"
                "\n"
                "def find_min(node):\n"
                "    # 找到BST中的最小值节点（最左节点）\n"
                "    while node.left:\n"
                "        node = node.left\n"
                "    return node\n"
            ),
            "test_cases": [
                {"input": "root=TreeNode(5,TreeNode(3),TreeNode(6,None,TreeNode(7))); r=delete_node(root,3); (r.left is None, r.val)", "expected": "(True, 5)"},
                {"input": "root=TreeNode(5,TreeNode(3),TreeNode(6,None,TreeNode(7))); r=delete_node(root,6); (r.right.val, r.val)", "expected": "(7, 5)"},
            ],
            "difficulty": 3,
            "blanks": [
                {"line": 18, "hint": "没有左子节点时，直接返回右子节点"},
                {"line": 20, "hint": "没有右子节点时，直接返回左子节点"},
                {"line": 24, "hint": "找到右子树的最小值节点作为替代"},
                {"line": 25, "hint": "用后继节点的值替换当前节点"},
                {"line": 27, "hint": "删除右子树中已替换的后继节点"},
            ],
        },
    ],

    "avl": [
        {
            "id": "avl_template_1",
            "title": "AVL树的旋转操作",
            "description": "实现AVL树的四种旋转操作：左旋、右旋、左右旋、右左旋",
            "code": (
                "class TreeNode:\n"
                "    def __init__(self, val=0, left=None, right=None):\n"
                "        self.val = val\n"
                "        self.left = left\n"
                "        self.right = right\n"
                "        self.height = 1\n"
                "\n"
                "def get_height(node):\n"
                "    if not node:\n"
                "        return 0\n"
                "    return node.height\n"
                "\n"
                "def get_balance(node):\n"
                "    # 计算平衡因子\n"
                "    if not node:\n"
                "        return 0\n"
                "    return get_height(node.left) - get_height(node.right)\n"
                "\n"
                "def right_rotate(y):\n"
                "    # 右旋：y为失衡节点，x为y的左子节点\n"
                "    x = y.left\n"
                "    T2 = x.right\n"
                "    # 执行旋转\n"
                "    x.right = y\n"
                "    y.left = T2\n"
                "    # 更新高度\n"
                "    y.height = 1 + max(get_height(y.left), get_height(y.right))\n"
                "    x.height = 1 + max(get_height(x.left), get_height(x.right))\n"
                "    return x\n"
                "\n"
                "def left_rotate(x):\n"
                "    # 左旋：x为失衡节点，y为x的右子节点\n"
                "    y = x.right\n"
                "    T2 = y.left\n"
                "    # 执行旋转\n"
                "    y.left = x\n"
                "    x.right = T2\n"
                "    # 更新高度\n"
                "    x.height = 1 + max(get_height(x.left), get_height(x.right))\n"
                "    y.height = 1 + max(get_height(y.left), get_height(y.right))\n"
                "    return y\n"
            ),
            "test_cases": [
                {"input": "y=TreeNode(30,TreeNode(20,TreeNode(10))); r=right_rotate(y); (r.val, r.right.val, r.left.val)", "expected": "(20, 30, 10)"},
                {"input": "x=TreeNode(10,None,TreeNode(20,None,TreeNode(30))); r=left_rotate(x); (r.val, r.left.val, r.right.val)", "expected": "(20, 10, 30)"},
            ],
            "difficulty": 4,
            "blanks": [
                {"line": 17, "hint": "平衡因子 = 左子树高度 - 右子树高度"},
                {"line": 25, "hint": "右旋：x的右子节点变为y的左子节点"},
                {"line": 26, "hint": "右旋：y成为x的右子节点"},
                {"line": 38, "hint": "左旋：y的左子节点变为x的右子节点"},
                {"line": 39, "hint": "左旋：x成为y的左子节点"},
            ],
        },
        {
            "id": "avl_template_2",
            "title": "AVL树的插入",
            "description": "实现AVL树的插入操作，插入后自动平衡",
            "code": (
                "class TreeNode:\n"
                "    def __init__(self, val=0, left=None, right=None):\n"
                "        self.val = val\n"
                "        self.left = left\n"
                "        self.right = right\n"
                "        self.height = 1\n"
                "\n"
                "def get_height(node):\n"
                "    if not node:\n"
                "        return 0\n"
                "    return node.height\n"
                "\n"
                "def get_balance(node):\n"
                "    if not node:\n"
                "        return 0\n"
                "    return get_height(node.left) - get_height(node.right)\n"
                "\n"
                "def left_rotate(z):\n"
                "    y = z.right\n"
                "    T2 = y.left\n"
                "    y.left = z\n"
                "    z.right = T2\n"
                "    z.height = 1 + max(get_height(z.left), get_height(z.right))\n"
                "    y.height = 1 + max(get_height(y.left), get_height(y.right))\n"
                "    return y\n"
                "\n"
                "def right_rotate(z):\n"
                "    y = z.left\n"
                "    T3 = y.right\n"
                "    y.right = z\n"
                "    z.left = T3\n"
                "    z.height = 1 + max(get_height(z.left), get_height(z.right))\n"
                "    y.height = 1 + max(get_height(y.left), get_height(y.right))\n"
                "    return y\n"
                "\n"
                "def insert(node, val):\n"
                "    # 1. 标准BST插入\n"
                "    if not node:\n"
                "        return TreeNode(val)\n"
                "    if val < node.val:\n"
                "        node.left = insert(node.left, val)\n"
                "    elif val > node.val:\n"
                "        node.right = insert(node.right, val)\n"
                "    else:\n"
                "        return node\n"
                "    # 2. 更新高度\n"
                "    node.height = 1 + max(get_height(node.left), get_height(node.right))\n"
                "    # 3. 获取平衡因子\n"
                "    balance = get_balance(node)\n"
                "    # 4. 根据失衡类型进行旋转\n"
                "    # 左左情况（LL）\n"
                "    if balance > 1 and val < node.left.val:\n"
                "        return right_rotate(node)\n"
                "    # 右右情况（RR）\n"
                "    if balance < -1 and val > node.right.val:\n"
                "        return left_rotate(node)\n"
                "    # 左右情况（LR）\n"
                "    if balance > 1 and val > node.left.val:\n"
                "        node.left = left_rotate(node.left)\n"
                "        return right_rotate(node)\n"
                "    # 右左情况（RL）\n"
                "    if balance < -1 and val < node.right.val:\n"
                "        node.right = right_rotate(node.right)\n"
                "        return left_rotate(node)\n"
                "    return node\n"
            ),
            "test_cases": [
                {"input": "root=None; root=insert(root,10); root=insert(root,20); root=insert(root,30); root.val", "expected": "20"},
                {"input": "root=None; root=insert(root,30); root=insert(root,20); root=insert(root,10); root.val", "expected": "20"},
                {"input": "root=None; root=insert(root,10); root=insert(root,30); root=insert(root,20); root.val", "expected": "20"},
            ],
            "difficulty": 5,
            "blanks": [
                {"line": 58, "hint": "LL情况：右旋即可恢复平衡"},
                {"line": 61, "hint": "RR情况：左旋即可恢复平衡"},
                {"line": 64, "hint": "LR情况：先对左子节点左旋，再对根节点右旋"},
                {"line": 68, "hint": "RL情况：先对右子节点右旋，再对根节点左旋"},
            ],
        },
    ],

    "heap": [
        {
            "id": "heap_template_1",
            "title": "最小堆实现",
            "description": "实现最小堆的插入和提取最小值操作",
            "code": (
                "class MinHeap:\n"
                "    def __init__(self):\n"
                "        self.heap = []\n"
                "\n"
                "    def push(self, val):\n"
                "        # 插入元素到堆末尾，然后上浮\n"
                "        self.heap.append(val)\n"
                "        self._sift_up(len(self.heap) - 1)\n"
                "\n"
                "    def pop(self):\n"
                "        # 弹出堆顶最小元素\n"
                "        if not self.heap:\n"
                "            return None\n"
                "        if len(self.heap) == 1:\n"
                "            return self.heap.pop()\n"
                "        # 保存堆顶元素\n"
                "        min_val = self.heap[0]\n"
                "        # 将末尾元素移到堆顶\n"
                "        self.heap[0] = self.heap.pop()\n"
                "        # 下沉调整\n"
                "        self._sift_down(0)\n"
                "        return min_val\n"
                "\n"
                "    def _sift_up(self, i):\n"
                "        # 上浮：与父节点比较并交换\n"
                "        parent = (i - 1) // 2\n"
                "        while i > 0 and self.heap[i] < self.heap[parent]:\n"
                "            self.heap[i], self.heap[parent] = self.heap[parent], self.heap[i]\n"
                "            i = parent\n"
                "            parent = (i - 1) // 2\n"
                "\n"
                "    def _sift_down(self, i):\n"
                "        # 下沉：与较小子节点比较并交换\n"
                "        n = len(self.heap)\n"
                "        while True:\n"
                "            smallest = i\n"
                "            left = 2 * i + 1\n"
                "            right = 2 * i + 2\n"
                "            if left < n and self.heap[left] < self.heap[smallest]:\n"
                "                smallest = left\n"
                "            if right < n and self.heap[right] < self.heap[smallest]:\n"
                "                smallest = right\n"
                "            if smallest == i:\n"
                "                break\n"
                "            self.heap[i], self.heap[smallest] = self.heap[smallest], self.heap[i]\n"
                "            i = smallest\n"
                "\n"
                "    def peek(self):\n"
                "        return self.heap[0] if self.heap else None\n"
            ),
            "test_cases": [
                {"input": "h=MinHeap(); h.push(3); h.push(1); h.push(2); h.pop()", "expected": "1"},
                {"input": "h=MinHeap(); h.push(5); h.push(3); h.push(4); h.push(1); h.pop()", "expected": "1"},
                {"input": "h=MinHeap(); h.push(2); h.peek()", "expected": "2"},
            ],
            "difficulty": 3,
            "blanks": [
                {"line": 7, "hint": "插入后调用上浮操作维护堆性质"},
                {"line": 19, "hint": "将末尾元素移到堆顶"},
                {"line": 21, "hint": "对堆顶元素执行下沉操作"},
                {"line": 28, "hint": "如果当前节点比父节点小，则交换"},
                {"line": 40, "hint": "如果左子节点更小，更新smallest"},
                {"line": 42, "hint": "如果右子节点更小，更新smallest"},
            ],
        },
        {
            "id": "heap_template_2",
            "title": "堆排序",
            "description": "使用最大堆实现堆排序算法",
            "code": (
                "def heap_sort(arr):\n"
                "    n = len(arr)\n"
                "    # 建堆：从最后一个非叶子节点开始下沉\n"
                "    for i in range(n // 2 - 1, -1, -1):\n"
                "        _sift_down(arr, n, i)\n"
                "    # 逐个提取堆顶元素（最大值）放到末尾\n"
                "    for i in range(n - 1, 0, -1):\n"
                "        # 交换堆顶和当前末尾元素\n"
                "        arr[0], arr[i] = arr[i], arr[0]\n"
                "        # 对剩余堆进行下沉调整\n"
                "        _sift_down(arr, i, 0)\n"
                "    return arr\n"
                "\n"
                "def _sift_down(arr, n, i):\n"
                "    # 最大堆下沉操作\n"
                "    largest = i\n"
                "    left = 2 * i + 1\n"
                "    right = 2 * i + 2\n"
                "    if left < n and arr[left] > arr[largest]:\n"
                "        largest = left\n"
                "    if right < n and arr[right] > arr[largest]:\n"
                "        largest = right\n"
                "    if largest != i:\n"
                "        arr[i], arr[largest] = arr[largest], arr[i]\n"
                "        _sift_down(arr, n, largest)\n"
            ),
            "test_cases": [
                {"input": "heap_sort([4,10,3,5,1])", "expected": "[1, 3, 4, 5, 10]"},
                {"input": "heap_sort([1])", "expected": "[1]"},
                {"input": "heap_sort([5,4,3,2,1])", "expected": "[1, 2, 3, 4, 5]"},
            ],
            "difficulty": 3,
            "blanks": [
                {"line": 4, "hint": "从最后一个非叶子节点开始，自底向上建堆"},
                {"line": 9, "hint": "将堆顶最大元素交换到数组末尾"},
                {"line": 11, "hint": "对缩小后的堆重新下沉调整"},
                {"line": 19, "hint": "如果左子节点更大，更新largest"},
                {"line": 21, "hint": "如果右子节点更大，更新largest"},
            ],
        },
        {
            "id": "heap_template_3",
            "title": "Top K问题",
            "description": "使用最小堆找出数组中前K个最大的元素",
            "code": (
                "import heapq\n"
                "\n"
                "def top_k_largest(nums, k):\n"
                "    # 使用最小堆维护前K个最大元素\n"
                "    heap = []\n"
                "    for num in nums:\n"
                "        if len(heap) < k:\n"
                "            # 堆未满，直接加入\n"
                "            heapq.heappush(heap, num)\n"
                "        elif num > heap[0]:\n"
                "            # 当前元素大于堆顶，替换堆顶\n"
                "            heapq.heapreplace(heap, num)\n"
                "    # 返回结果，按从大到小排序\n"
                "    return sorted(heap, reverse=True)\n"
            ),
            "test_cases": [
                {"input": "top_k_largest([3,2,1,5,6,4], 2)", "expected": "[6, 5]"},
                {"input": "top_k_largest([3,2,3,1,2,4,5,5,6], 4)", "expected": "[6, 5, 5, 4]"},
                {"input": "top_k_largest([1], 1)", "expected": "[1]"},
            ],
            "difficulty": 3,
            "blanks": [
                {"line": 8, "hint": "堆未满时，直接将元素加入最小堆"},
                {"line": 10, "hint": "当前元素比堆顶大时，替换堆顶元素"},
                {"line": 11, "hint": "使用heapreplace替换堆顶（弹出最小并插入新元素）"},
            ],
        },
    ],

    "bubble_sort": [
        {
            "id": "bubble_sort_template_1",
            "title": "冒泡排序",
            "description": "实现基本的冒泡排序算法",
            "code": (
                "def bubble_sort(arr):\n"
                "    n = len(arr)\n"
                "    # 外层循环控制排序轮数\n"
                "    for i in range(n - 1):\n"
                "        # 内层循环进行相邻元素比较和交换\n"
                "        for j in range(n - 1 - i):\n"
                "            # 如果前一个元素大于后一个元素，交换\n"
                "            if arr[j] > arr[j + 1]:\n"
                "                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n"
                "    return arr\n"
            ),
            "test_cases": [
                {"input": "bubble_sort([64,34,25,12,22,11,90])", "expected": "[11, 12, 22, 25, 34, 64, 90]"},
                {"input": "bubble_sort([5,1,4,2,8])", "expected": "[1, 2, 4, 5, 8]"},
                {"input": "bubble_sort([1])", "expected": "[1]"},
            ],
            "difficulty": 1,
            "blanks": [
                {"line": 6, "hint": "内层循环范围逐轮缩小，因为末尾已排好序"},
                {"line": 8, "hint": "如果前一个元素更大，则交换相邻元素"},
                {"line": 9, "hint": "使用Python元组交换语法交换两个元素"},
            ],
        },
        {
            "id": "bubble_sort_template_2",
            "title": "优化冒泡排序",
            "description": "添加提前终止标志的冒泡排序优化版本",
            "code": (
                "def bubble_sort_optimized(arr):\n"
                "    n = len(arr)\n"
                "    for i in range(n - 1):\n"
                "        # 标志位：本轮是否发生交换\n"
                "        swapped = False\n"
                "        for j in range(n - 1 - i):\n"
                "            if arr[j] > arr[j + 1]:\n"
                "                # 交换相邻元素\n"
                "                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n"
                "                swapped = True\n"
                "        # 如果本轮没有交换，说明已排好序\n"
                "        if not swapped:\n"
                "            break\n"
                "    return arr\n"
            ),
            "test_cases": [
                {"input": "bubble_sort_optimized([1,2,3,4,5])", "expected": "[1, 2, 3, 4, 5]"},
                {"input": "bubble_sort_optimized([5,4,3,2,1])", "expected": "[1, 2, 3, 4, 5]"},
                {"input": "bubble_sort_optimized([3,1,4,1,5])", "expected": "[1, 1, 3, 4, 5]"},
            ],
            "difficulty": 2,
            "blanks": [
                {"line": 5, "hint": "初始化交换标志为False"},
                {"line": 10, "hint": "发生交换时将标志设为True"},
                {"line": 12, "hint": "如果本轮没有交换，提前终止排序"},
            ],
        },
    ],

    "quick_sort": [
        {
            "id": "quick_sort_template_1",
            "title": "快速排序",
            "description": "实现快速排序算法，选择最右元素作为基准",
            "code": (
                "def quick_sort(arr):\n"
                "    if len(arr) <= 1:\n"
                "        return arr\n"
                "    # 选择最后一个元素作为基准\n"
                "    pivot = arr[-1]\n"
                "    # 分区：小于基准、等于基准、大于基准\n"
                "    left = [x for x in arr[:-1] if x < pivot]\n"
                "    middle = [x for x in arr if x == pivot]\n"
                "    right = [x for x in arr[:-1] if x > pivot]\n"
                "    # 递归排序左右分区并合并\n"
                "    return quick_sort(left) + middle + quick_sort(right)\n"
            ),
            "test_cases": [
                {"input": "quick_sort([3,6,8,10,1,2,1])", "expected": "[1, 1, 2, 3, 6, 8, 10]"},
                {"input": "quick_sort([5,4,3,2,1])", "expected": "[1, 2, 3, 4, 5]"},
                {"input": "quick_sort([])", "expected": "[]"},
            ],
            "difficulty": 2,
            "blanks": [
                {"line": 5, "hint": "选择基准元素（pivot）"},
                {"line": 7, "hint": "将小于基准的元素放入左分区"},
                {"line": 9, "hint": "将大于基准的元素放入右分区"},
                {"line": 11, "hint": "递归排序左右分区，合并结果"},
            ],
        },
        {
            "id": "quick_sort_template_2",
            "title": "原地快速排序",
            "description": "使用Lomuto分区方案实现原地快速排序",
            "code": (
                "def quick_sort_inplace(arr, low, high):\n"
                "    if low < high:\n"
                "        # 分区并获取基准位置\n"
                "        pi = partition(arr, low, high)\n"
                "        # 递归排序基准左侧\n"
                "        quick_sort_inplace(arr, low, pi - 1)\n"
                "        # 递归排序基准右侧\n"
                "        quick_sort_inplace(arr, pi + 1, high)\n"
                "\n"
                "def partition(arr, low, high):\n"
                "    # 选择最右元素作为基准\n"
                "    pivot = arr[high]\n"
                "    # i指向小于基准区域的右边界\n"
                "    i = low - 1\n"
                "    for j in range(low, high):\n"
                "        # 如果当前元素小于等于基准\n"
                "        if arr[j] <= pivot:\n"
                "            i += 1\n"
                "            # 交换arr[i]和arr[j]\n"
                "            arr[i], arr[j] = arr[j], arr[i]\n"
                "    # 将基准放到正确位置\n"
                "    arr[i + 1], arr[high] = arr[high], arr[i + 1]\n"
                "    return i + 1\n"
            ),
            "test_cases": [
                {"input": "arr=[10,7,8,9,1,5]; quick_sort_inplace(arr,0,5); arr", "expected": "[1, 5, 7, 8, 9, 10]"},
                {"input": "arr=[3,2,1]; quick_sort_inplace(arr,0,2); arr", "expected": "[1, 2, 3]"},
            ],
            "difficulty": 3,
            "blanks": [
                {"line": 4, "hint": "调用分区函数获取基准的最终位置"},
                {"line": 6, "hint": "递归排序基准左侧的子数组"},
                {"line": 8, "hint": "递归排序基准右侧的子数组"},
                {"line": 17, "hint": "当前元素小于等于基准时，扩展小元素区域并交换"},
                {"line": 22, "hint": "将基准元素放到正确位置（i+1）"},
            ],
        },
    ],

    "merge_sort": [
        {
            "id": "merge_sort_template_1",
            "title": "归并排序",
            "description": "实现归并排序算法：分治、递归、合并",
            "code": (
                "def merge_sort(arr):\n"
                "    # 基准条件：数组长度为1或0时直接返回\n"
                "    if len(arr) <= 1:\n"
                "        return arr\n"
                "    # 分：找到中点，分成两半\n"
                "    mid = len(arr) // 2\n"
                "    left = merge_sort(arr[:mid])\n"
                "    right = merge_sort(arr[mid:])\n"
                "    # 治：合并两个有序数组\n"
                "    return merge(left, right)\n"
                "\n"
                "def merge(left, right):\n"
                "    result = []\n"
                "    i = j = 0\n"
                "    # 双指针比较两个数组的元素\n"
                "    while i < len(left) and j < len(right):\n"
                "        if left[i] <= right[j]:\n"
                "            result.append(left[i])\n"
                "            i += 1\n"
                "        else:\n"
                "            result.append(right[j])\n"
                "            j += 1\n"
                "    # 将剩余元素加入结果\n"
                "    result.extend(left[i:])\n"
                "    result.extend(right[j:])\n"
                "    return result\n"
            ),
            "test_cases": [
                {"input": "merge_sort([38,27,43,3,9,82,10])", "expected": "[3, 9, 10, 27, 38, 43, 82]"},
                {"input": "merge_sort([5,4,3,2,1])", "expected": "[1, 2, 3, 4, 5]"},
                {"input": "merge_sort([])", "expected": "[]"},
            ],
            "difficulty": 2,
            "blanks": [
                {"line": 6, "hint": "计算数组中点，将数组一分为二"},
                {"line": 7, "hint": "递归排序左半部分"},
                {"line": 8, "hint": "递归排序右半部分"},
                {"line": 17, "hint": "比较左右指针元素，取较小者加入结果"},
                {"line": 25, "hint": "将左数组剩余元素加入结果"},
                {"line": 26, "hint": "将右数组剩余元素加入结果"},
            ],
        },
        {
            "id": "merge_sort_template_2",
            "title": "归并排序求逆序对",
            "description": "在归并排序过程中统计数组中的逆序对数量",
            "code": (
                "def count_inversions(arr):\n"
                "    # 使用归并排序统计逆序对\n"
                "    if len(arr) <= 1:\n"
                "        return arr, 0\n"
                "    mid = len(arr) // 2\n"
                "    left, left_count = count_inversions(arr[:mid])\n"
                "    right, right_count = count_inversions(arr[mid:])\n"
                "    merged, merge_count = _merge_and_count(left, right)\n"
                "    total = left_count + right_count + merge_count\n"
                "    return merged, total\n"
                "\n"
                "def _merge_and_count(left, right):\n"
                "    result = []\n"
                "    i = j = 0\n"
                "    inv_count = 0\n"
                "    while i < len(left) and j < len(right):\n"
                "        if left[i] <= right[j]:\n"
                "            result.append(left[i])\n"
                "            i += 1\n"
                "        else:\n"
                "            # left[i] > right[j]，产生逆序对\n"
                "            # left中i及之后的所有元素都与right[j]构成逆序对\n"
                "            result.append(right[j])\n"
                "            inv_count += len(left) - i\n"
                "            j += 1\n"
                "    result.extend(left[i:])\n"
                "    result.extend(right[j:])\n"
                "    return result, inv_count\n"
            ),
            "test_cases": [
                {"input": "count_inversions([2,4,1,3,5])[1]", "expected": "3"},
                {"input": "count_inversions([5,4,3,2,1])[1]", "expected": "10"},
                {"input": "count_inversions([1,2,3,4,5])[1]", "expected": "0"},
            ],
            "difficulty": 3,
            "blanks": [
                {"line": 9, "hint": "总逆序对 = 左半逆序对 + 右半逆序对 + 跨越逆序对"},
                {"line": 22, "hint": "当左元素大于右元素时，左数组剩余元素都与右元素构成逆序对"},
            ],
        },
    ],

    "binary_search": [
        {
            "id": "binary_search_template_1",
            "title": "二分查找",
            "description": "在有序数组中查找目标值，返回索引，不存在则返回-1",
            "code": (
                "def binary_search(arr, target):\n"
                "    left = 0\n"
                "    right = len(arr) - 1\n"
                "    while left <= right:\n"
                "        # 计算中间索引（避免整数溢出）\n"
                "        mid = left + (right - left) // 2\n"
                "        if arr[mid] == target:\n"
                "            # 找到目标，返回索引\n"
                "            return mid\n"
                "        elif arr[mid] < target:\n"
                "            # 目标在右半部分\n"
                "            left = mid + 1\n"
                "        else:\n"
                "            # 目标在左半部分\n"
                "            right = mid - 1\n"
                "    # 未找到目标\n"
                "    return -1\n"
            ),
            "test_cases": [
                {"input": "binary_search([-1,0,3,5,9,12], 9)", "expected": "4"},
                {"input": "binary_search([-1,0,3,5,9,12], 2)", "expected": "-1"},
                {"input": "binary_search([1,2,3,4,5], 1)", "expected": "0"},
            ],
            "difficulty": 1,
            "blanks": [
                {"line": 6, "hint": "计算中间索引，使用left+(right-left)//2避免溢出"},
                {"line": 8, "hint": "中间值等于目标值，查找成功"},
                {"line": 11, "hint": "中间值小于目标值，搜索右半部分"},
                {"line": 14, "hint": "中间值大于目标值，搜索左半部分"},
            ],
        },
        {
            "id": "binary_search_template_2",
            "title": "搜索插入位置",
            "description": "在有序数组中查找目标值，如果不存在则返回应插入的位置",
            "code": (
                "def search_insert(arr, target):\n"
                "    left = 0\n"
                "    right = len(arr) - 1\n"
                "    while left <= right:\n"
                "        mid = left + (right - left) // 2\n"
                "        if arr[mid] == target:\n"
                "            return mid\n"
                "        elif arr[mid] < target:\n"
                "            # 目标在右半部分\n"
                "            left = mid + 1\n"
                "        else:\n"
                "            # 目标在左半部分\n"
                "            right = mid - 1\n"
                "    # left就是目标应插入的位置\n"
                "    return left\n"
            ),
            "test_cases": [
                {"input": "search_insert([1,3,5,6], 5)", "expected": "2"},
                {"input": "search_insert([1,3,5,6], 2)", "expected": "1"},
                {"input": "search_insert([1,3,5,6], 7)", "expected": "4"},
                {"input": "search_insert([1,3,5,6], 0)", "expected": "0"},
            ],
            "difficulty": 2,
            "blanks": [
                {"line": 10, "hint": "目标值大于中间值，在右半部分搜索"},
                {"line": 13, "hint": "目标值小于中间值，在左半部分搜索"},
                {"line": 15, "hint": "循环结束时left就是应插入的位置"},
            ],
        },
        {
            "id": "binary_search_template_3",
            "title": "查找第一个和最后一个位置",
            "description": "在有序数组中查找目标值的起始和结束位置，不存在返回[-1,-1]",
            "code": (
                "def search_range(nums, target):\n"
                "    # 查找左边界\n"
                "    left = find_left(nums, target)\n"
                "    if left == -1:\n"
                "        return [-1, -1]\n"
                "    # 查找右边界\n"
                "    right = find_right(nums, target)\n"
                "    return [left, right]\n"
                "\n"
                "def find_left(nums, target):\n"
                "    left, right = 0, len(nums) - 1\n"
                "    result = -1\n"
                "    while left <= right:\n"
                "        mid = left + (right - left) // 2\n"
                "        if nums[mid] == target:\n"
                "            result = mid\n"
                "            # 继续向左搜索更早出现的位置\n"
                "            right = mid - 1\n"
                "        elif nums[mid] < target:\n"
                "            left = mid + 1\n"
                "        else:\n"
                "            right = mid - 1\n"
                "    return result\n"
                "\n"
                "def find_right(nums, target):\n"
                "    left, right = 0, len(nums) - 1\n"
                "    result = -1\n"
                "    while left <= right:\n"
                "        mid = left + (right - left) // 2\n"
                "        if nums[mid] == target:\n"
                "            result = mid\n"
                "            # 继续向右搜索更晚出现的位置\n"
                "            right = mid + 1\n"
                "        elif nums[mid] < target:\n"
                "            left = mid + 1\n"
                "        else:\n"
                "            right = mid - 1\n"
                "    return result\n"
            ),
            "test_cases": [
                {"input": "search_range([5,7,7,8,8,10], 8)", "expected": "[3, 4]"},
                {"input": "search_range([5,7,7,8,8,10], 6)", "expected": "[-1, -1]"},
                {"input": "search_range([], 0)", "expected": "[-1, -1]"},
            ],
            "difficulty": 3,
            "blanks": [
                {"line": 17, "hint": "找到目标后继续向左搜索，寻找更早出现的位置"},
                {"line": 35, "hint": "找到目标后继续向右搜索，寻找更晚出现的位置"},
            ],
        },
    ],

    "recursion": [
        {
            "id": "recursion_template_1",
            "title": "斐波那契数列",
            "description": "使用递归和记忆化搜索实现斐波那契数列",
            "code": (
                "def fibonacci(n, memo=None):\n"
                "    if memo is None:\n"
                "        memo = {}\n"
                "    # 基准条件\n"
                "    if n <= 1:\n"
                "        return n\n"
                "    # 如果已计算过，直接返回缓存结果\n"
                "    if n in memo:\n"
                "        return memo[n]\n"
                "    # 递归计算并缓存结果\n"
                "    result = fibonacci(n - 1, memo) + fibonacci(n - 2, memo)\n"
                "    memo[n] = result\n"
                "    return result\n"
            ),
            "test_cases": [
                {"input": "fibonacci(0)", "expected": "0"},
                {"input": "fibonacci(1)", "expected": "1"},
                {"input": "fibonacci(10)", "expected": "55"},
                {"input": "fibonacci(20)", "expected": "6765"},
            ],
            "difficulty": 1,
            "blanks": [
                {"line": 5, "hint": "基准条件：n<=1时直接返回n"},
                {"line": 8, "hint": "检查缓存中是否已有计算结果"},
                {"line": 11, "hint": "递归关系：f(n)=f(n-1)+f(n-2)"},
                {"line": 12, "hint": "将计算结果存入缓存"},
            ],
        },
        {
            "id": "recursion_template_2",
            "title": "汉诺塔",
            "description": "使用递归解决汉诺塔问题，打印移动步骤",
            "code": (
                "def hanoi(n, source='A', auxiliary='B', target='C'):\n"
                "    if n == 1:\n"
                "        # 只有一个盘子，直接从源柱移到目标柱\n"
                "        return [(source, target)]\n"
                "    moves = []\n"
                "    # 第一步：将n-1个盘子从源柱移到辅助柱\n"
                "    moves += hanoi(n - 1, source, target, auxiliary)\n"
                "    # 第二步：将最大的盘子从源柱移到目标柱\n"
                "    moves.append((source, target))\n"
                "    # 第三步：将n-1个盘子从辅助柱移到目标柱\n"
                "    moves += hanoi(n - 1, auxiliary, source, target)\n"
                "    return moves\n"
            ),
            "test_cases": [
                {"input": "len(hanoi(1))", "expected": "1"},
                {"input": "len(hanoi(3))", "expected": "7"},
                {"input": "len(hanoi(5))", "expected": "31"},
                {"input": "hanoi(2)", "expected": "[('A', 'B'), ('A', 'C'), ('B', 'C')]"},
            ],
            "difficulty": 3,
            "blanks": [
                {"line": 2, "hint": "基准条件：只有一个盘子时直接移动"},
                {"line": 7, "hint": "递归：将n-1个盘子从源柱借助目标柱移到辅助柱"},
                {"line": 9, "hint": "将最大的盘子从源柱移到目标柱"},
                {"line": 11, "hint": "递归：将n-1个盘子从辅助柱借助源柱移到目标柱"},
            ],
        },
        {
            "id": "recursion_template_3",
            "title": "子集生成",
            "description": "使用递归回溯法生成集合的所有子集",
            "code": (
                "def subsets(nums):\n"
                "    result = []\n"
                "    # 回溯函数\n"
                "    def backtrack(start, path):\n"
                "        # 将当前子集加入结果\n"
                "        result.append(path[:])\n"
                "        # 从start开始遍历，避免重复\n"
                "        for i in range(start, len(nums)):\n"
                "            # 选择当前元素\n"
                "            path.append(nums[i])\n"
                "            # 递归处理后续元素\n"
                "            backtrack(i + 1, path)\n"
                "            # 撤销选择（回溯）\n"
                "            path.pop()\n"
                "    backtrack(0, [])\n"
                "    return result\n"
            ),
            "test_cases": [
                {"input": "subsets([1,2,3])", "expected": "[[], [1], [1, 2], [1, 2, 3], [1, 3], [2], [2, 3], [3]]"},
                {"input": "subsets([0])", "expected": "[[], [0]]"},
                {"input": "len(subsets([1,2,3,4]))", "expected": "16"},
            ],
            "difficulty": 3,
            "blanks": [
                {"line": 6, "hint": "将当前路径的副本加入结果集"},
                {"line": 10, "hint": "选择当前元素加入路径"},
                {"line": 12, "hint": "递归处理下一个位置的元素"},
                {"line": 14, "hint": "撤销选择，回溯到上一层"},
            ],
        },
    ],

    "dynamic_programming": [
        {
            "id": "dynamic_programming_template_1",
            "title": "爬楼梯",
            "description": "每次可以爬1或2阶台阶，求到达第n阶的方法数",
            "code": (
                "def climb_stairs(n):\n"
                "    if n <= 2:\n"
                "        return n\n"
                "    # dp[i]表示到达第i阶的方法数\n"
                "    dp = [0] * (n + 1)\n"
                "    dp[1] = 1\n"
                "    dp[2] = 2\n"
                "    for i in range(3, n + 1):\n"
                "        # 状态转移：从第i-1阶跨1步，或从第i-2阶跨2步\n"
                "        dp[i] = dp[i - 1] + dp[i - 2]\n"
                "    return dp[n]\n"
            ),
            "test_cases": [
                {"input": "climb_stairs(2)", "expected": "2"},
                {"input": "climb_stairs(3)", "expected": "3"},
                {"input": "climb_stairs(5)", "expected": "8"},
            ],
            "difficulty": 2,
            "blanks": [
                {"line": 6, "hint": "到达第1阶只有1种方法"},
                {"line": 7, "hint": "到达第2阶有2种方法"},
                {"line": 10, "hint": "状态转移方程：dp[i]=dp[i-1]+dp[i-2]"},
            ],
        },
        {
            "id": "dynamic_programming_template_2",
            "title": "0-1背包问题",
            "description": "给定物品重量和价值，在容量有限的背包中求最大价值",
            "code": (
                "def knapsack(weights, values, capacity):\n"
                "    n = len(weights)\n"
                "    # dp[i][w]表示前i个物品、容量为w时的最大价值\n"
                "    dp = [[0] * (capacity + 1) for _ in range(n + 1)]\n"
                "    for i in range(1, n + 1):\n"
                "        for w in range(capacity + 1):\n"
                "            # 不选第i个物品\n"
                "            dp[i][w] = dp[i - 1][w]\n"
                "            # 选第i个物品（如果放得下）\n"
                "            if w >= weights[i - 1]:\n"
                "                dp[i][w] = max(dp[i][w], dp[i - 1][w - weights[i - 1]] + values[i - 1])\n"
                "    return dp[n][capacity]\n"
            ),
            "test_cases": [
                {"input": "knapsack([1,3,4,5], [1,4,5,7], 7)", "expected": "9"},
                {"input": "knapsack([2,3,4,5], [3,4,5,6], 5)", "expected": "7"},
                {"input": "knapsack([1,2,3], [10,15,40], 6)", "expected": "65"},
            ],
            "difficulty": 3,
            "blanks": [
                {"line": 4, "hint": "初始化二维DP表，(n+1)x(capacity+1)大小"},
                {"line": 8, "hint": "不选第i个物品时，价值与前i-1个物品相同"},
                {"line": 11, "hint": "选第i个物品时，取不选和选两种情况的最大值"},
            ],
        },
        {
            "id": "dynamic_programming_template_3",
            "title": "最长公共子序列",
            "description": "求两个字符串的最长公共子序列的长度",
            "code": (
                "def longest_common_subsequence(text1, text2):\n"
                "    m, n = len(text1), len(text2)\n"
                "    # dp[i][j]表示text1前i个字符和text2前j个字符的LCS长度\n"
                "    dp = [[0] * (n + 1) for _ in range(m + 1)]\n"
                "    for i in range(1, m + 1):\n"
                "        for j in range(1, n + 1):\n"
                "            if text1[i - 1] == text2[j - 1]:\n"
                "                # 字符相同，LCS长度加1\n"
                "                dp[i][j] = dp[i - 1][j - 1] + 1\n"
                "            else:\n"
                "                # 字符不同，取上方或左方的较大值\n"
                "                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])\n"
                "    return dp[m][n]\n"
            ),
            "test_cases": [
                {"input": "longest_common_subsequence('abcde', 'ace')", "expected": "3"},
                {"input": "longest_common_subsequence('abc', 'abc')", "expected": "3"},
                {"input": "longest_common_subsequence('abc', 'def')", "expected": "0"},
            ],
            "difficulty": 4,
            "blanks": [
                {"line": 4, "hint": "初始化(m+1)x(n+1)的DP表"},
                {"line": 8, "hint": "字符相同时，LCS长度等于左上方值加1"},
                {"line": 11, "hint": "字符不同时，取上方和左方中的较大值"},
            ],
        },
    ],
}


def ensure_templates_in_db(db):
    """确保预制代码模板已入库（幂等：重复调用自动跳过已有模板）

    首次启动时自动将 CODE_TEMPLATES 写入 MySQL，
    后续重启时自动跳过。
    """
    import json
    import logging
    from app.models.profile import CodeTemplateModel

    logger = logging.getLogger(__name__)
    synced = 0
    skipped = 0

    for kp, templates in CODE_TEMPLATES.items():
        for t in templates:
            existing = db.query(CodeTemplateModel).filter(
                CodeTemplateModel.id == t["id"]
            ).first()
            if existing:
                skipped += 1
                continue
            model = CodeTemplateModel(
                id=t["id"],
                knowledge_point=kp,
                title=t["title"],
                description=t.get("description", ""),
                code=t["code"],
                test_cases_json=json.dumps(t.get("test_cases", []), ensure_ascii=False),
                difficulty=t.get("difficulty", 1),
                blanks_json=json.dumps(t.get("blanks", []), ensure_ascii=False),
                classic=True,
            )
            db.add(model)
            synced += 1

    db.commit()
    logger.info("代码模板同步到MySQL完成: 新增%d, 跳过%d", synced, skipped)
