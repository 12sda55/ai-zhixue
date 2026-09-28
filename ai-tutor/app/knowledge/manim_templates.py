"""Manim白板动画模板 - 11个核心概念动画脚本

对照 ai_architecture_plan.md Agent 5 第二层：
- 白底黑字简笔画风格
- 步骤动画带暂停
- 包含旁白文本注释（用于TTS）
- 使用Manim的Array、Arrow、Circle、Text等对象
- 渲染时长1-3分钟

使用方式: manim -pql script.py SceneName
"""

from __future__ import annotations

# ===== 模板注册表 =====
# key: 知识点ID -> value: (SceneClassName, script_content, narration_texts)
MANIM_TEMPLATES: dict[str, dict] = {}


def _register(key: str, scene_class: str, script: str, narrations: list[str]):
    MANIM_TEMPLATES[key] = {
        "scene_class": scene_class,
        "script": script,
        "narrations": narrations,
    }


# ===== 冒泡排序 =====

_BUBBLE_SORT_SCRIPT = '''from manim import *

class BubbleSortScene(Scene):
    def construct(self):
        self.camera.background_color = WHITE

        # === 段落0: 标题与概念引入 ===
        title = MarkupText("冒泡排序", font="Microsoft YaHei", color=BLACK, font_size=42).to_edge(UP)
        subtitle = MarkupText("相邻元素比较与交换", font="Microsoft YaHei", color=GRAY, font_size=22).next_to(title, DOWN)
        self.play(Write(title), FadeIn(subtitle))
        self.wait(#SEG_DUR_0#)

        # === 段落1: 初始数组展示 ===
        values = [5, 3, 8, 4, 2]
        n = len(values)
        squares = []
        texts = []
        for i, v in enumerate(values):
            sq = Square(side_length=0.9, color=BLACK, stroke_width=2)
            sq.shift(RIGHT * (i - n/2 + 0.5) * 1.2)
            tx = Text(str(v), color=BLACK, font_size=32).move_to(sq)
            squares.append(sq)
            texts.append(tx)

        arr_group = VGroup(*squares, *texts).shift(DOWN * 0.3)
        self.play(FadeIn(arr_group))
        self.wait(#SEG_DUR_1#)

        # === 段落2-5: 排序过程（每轮对应一段旁白） ===
        arr = values.copy()
        pass_label = MarkupText("第 1 轮", font="Microsoft YaHei", color=BLUE, font_size=24).to_edge(DOWN)
        self.play(Write(pass_label))

        # 第1轮
        i = 0
        new_label = MarkupText(f"第 {i+1} 轮", font="Microsoft YaHei", color=BLUE, font_size=24).to_edge(DOWN)
        self.play(Transform(pass_label, new_label))
        for j in range(n - 1 - i):
            self.play(
                squares[j].animate.set_fill(YELLOW, opacity=0.4),
                squares[j+1].animate.set_fill(YELLOW, opacity=0.4),
                run_time=0.3
            )
            self.wait(0.2)
            if arr[j] > arr[j+1]:
                self.play(
                    squares[j].animate.set_fill(RED, opacity=0.4),
                    squares[j+1].animate.set_fill(RED, opacity=0.4),
                    run_time=0.2
                )
                arr[j], arr[j+1] = arr[j+1], arr[j]
                new_tx_j = Text(str(arr[j]), color=BLACK, font_size=32).move_to(squares[j])
                new_tx_j1 = Text(str(arr[j+1]), color=BLACK, font_size=32).move_to(squares[j+1])
                self.play(
                    Transform(texts[j], new_tx_j),
                    Transform(texts[j+1], new_tx_j1),
                    run_time=0.5
                )
            self.play(
                squares[j].animate.set_fill(WHITE, opacity=0),
                squares[j+1].animate.set_fill(WHITE, opacity=0),
                run_time=0.2
            )
        self.play(squares[n-1-i].animate.set_fill(GREEN, opacity=0.3), run_time=0.3)
        self.wait(#SEG_DUR_2#)

        # 第2轮
        i = 1
        new_label = MarkupText(f"第 {i+1} 轮", font="Microsoft YaHei", color=BLUE, font_size=24).to_edge(DOWN)
        self.play(Transform(pass_label, new_label))
        for j in range(n - 1 - i):
            self.play(
                squares[j].animate.set_fill(YELLOW, opacity=0.4),
                squares[j+1].animate.set_fill(YELLOW, opacity=0.4),
                run_time=0.3
            )
            self.wait(0.2)
            if arr[j] > arr[j+1]:
                self.play(
                    squares[j].animate.set_fill(RED, opacity=0.4),
                    squares[j+1].animate.set_fill(RED, opacity=0.4),
                    run_time=0.2
                )
                arr[j], arr[j+1] = arr[j+1], arr[j]
                new_tx_j = Text(str(arr[j]), color=BLACK, font_size=32).move_to(squares[j])
                new_tx_j1 = Text(str(arr[j+1]), color=BLACK, font_size=32).move_to(squares[j+1])
                self.play(
                    Transform(texts[j], new_tx_j),
                    Transform(texts[j+1], new_tx_j1),
                    run_time=0.5
                )
            self.play(
                squares[j].animate.set_fill(WHITE, opacity=0),
                squares[j+1].animate.set_fill(WHITE, opacity=0),
                run_time=0.2
            )
        self.play(squares[n-1-i].animate.set_fill(GREEN, opacity=0.3), run_time=0.3)
        self.wait(#SEG_DUR_3#)

        # 第3轮
        i = 2
        new_label = MarkupText(f"第 {i+1} 轮", font="Microsoft YaHei", color=BLUE, font_size=24).to_edge(DOWN)
        self.play(Transform(pass_label, new_label))
        for j in range(n - 1 - i):
            self.play(
                squares[j].animate.set_fill(YELLOW, opacity=0.4),
                squares[j+1].animate.set_fill(YELLOW, opacity=0.4),
                run_time=0.3
            )
            self.wait(0.2)
            if arr[j] > arr[j+1]:
                self.play(
                    squares[j].animate.set_fill(RED, opacity=0.4),
                    squares[j+1].animate.set_fill(RED, opacity=0.4),
                    run_time=0.2
                )
                arr[j], arr[j+1] = arr[j+1], arr[j]
                new_tx_j = Text(str(arr[j]), color=BLACK, font_size=32).move_to(squares[j])
                new_tx_j1 = Text(str(arr[j+1]), color=BLACK, font_size=32).move_to(squares[j+1])
                self.play(
                    Transform(texts[j], new_tx_j),
                    Transform(texts[j+1], new_tx_j1),
                    run_time=0.5
                )
            self.play(
                squares[j].animate.set_fill(WHITE, opacity=0),
                squares[j+1].animate.set_fill(WHITE, opacity=0),
                run_time=0.2
            )
        self.play(squares[n-1-i].animate.set_fill(GREEN, opacity=0.3), run_time=0.3)
        self.wait(#SEG_DUR_4#)

        # 第4轮
        i = 3
        new_label = MarkupText(f"第 {i+1} 轮", font="Microsoft YaHei", color=BLUE, font_size=24).to_edge(DOWN)
        self.play(Transform(pass_label, new_label))
        for j in range(n - 1 - i):
            self.play(
                squares[j].animate.set_fill(YELLOW, opacity=0.4),
                squares[j+1].animate.set_fill(YELLOW, opacity=0.4),
                run_time=0.3
            )
            self.wait(0.2)
            if arr[j] > arr[j+1]:
                self.play(
                    squares[j].animate.set_fill(RED, opacity=0.4),
                    squares[j+1].animate.set_fill(RED, opacity=0.4),
                    run_time=0.2
                )
                arr[j], arr[j+1] = arr[j+1], arr[j]
                new_tx_j = Text(str(arr[j]), color=BLACK, font_size=32).move_to(squares[j])
                new_tx_j1 = Text(str(arr[j+1]), color=BLACK, font_size=32).move_to(squares[j+1])
                self.play(
                    Transform(texts[j], new_tx_j),
                    Transform(texts[j+1], new_tx_j1),
                    run_time=0.5
                )
            self.play(
                squares[j].animate.set_fill(WHITE, opacity=0),
                squares[j+1].animate.set_fill(WHITE, opacity=0),
                run_time=0.2
            )
        self.play(squares[n-1-i].animate.set_fill(GREEN, opacity=0.3), run_time=0.3)
        self.wait(#SEG_DUR_5#)

        # === 段落6: 排序完成 ===
        for sq in squares:
            sq.set_fill(GREEN, opacity=0.3)
        self.play(FadeOut(pass_label))
        result = MarkupText(f"排序完成: {arr}", font="Microsoft YaHei", color=BLACK, font_size=28).to_edge(DOWN)
        self.play(Write(result))
        self.wait(#SEG_DUR_6#)

        # === 段落7: 复杂度分析 ===
        self.play(FadeOut(arr_group), FadeOut(result), FadeOut(subtitle))
        complexity_title = MarkupText("复杂度分析", font="Microsoft YaHei", color=BLACK, font_size=36).to_edge(UP)
        self.play(Write(complexity_title))

        lines = [
            "时间复杂度: O(n²)",
            "空间复杂度: O(1)",
            "稳定性: 稳定",
            "特点: 简单直观，适合教学",
        ]
        complexity_group = VGroup()
        for line in lines:
            t = MarkupText(line, font="Microsoft YaHei", color=BLACK, font_size=24)
            complexity_group.add(t)
        complexity_group.arrange(DOWN, buff=0.4).next_to(complexity_title, DOWN, buff=0.8)
        self.play(Write(complexity_group))
        self.wait(#SEG_DUR_7#)
'''

_register("bubble_sort", "BubbleSortScene", _BUBBLE_SORT_SCRIPT, [
    "冒泡排序是一种简单的排序算法。",
    "它重复地遍历数组，比较相邻的两个元素。",
    "如果左边的元素大于右边的，就交换它们。",
    "每一轮遍历，最大的元素会像气泡一样浮到数组末尾。",
    "如果在某一轮中没有发生交换，说明数组已经有序，可以提前终止。",
    "冒泡排序的时间复杂度为O(n²)，空间复杂度为O(1)。",
])


# ===== 快速排序 =====

_QUICK_SORT_SCRIPT = '''from manim import *

class QuickSortScene(Scene):
    def construct(self):
        self.camera.background_color = WHITE

        title = Text("快速排序", color=BLACK, font_size=40).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        values = [5, 3, 8, 4, 2, 7, 1, 6]
        n = len(values)
        arr = values.copy()

        # 创建数组显示
        def create_array_display(data, y_pos=DOWN*0.5):
            squares = []
            texts = []
            for i, v in enumerate(data):
                sq = Square(side_length=0.6, color=BLACK, stroke_width=2)
                sq.shift(RIGHT * (i - len(data)/2 + 0.5) * 0.8)
                tx = Text(str(v), color=BLACK, font_size=22).move_to(sq)
                squares.append(sq)
                texts.append(tx)
            group = VGroup(*squares, *texts).shift(y_pos)
            return squares, texts, group

        squares, texts, arr_group = create_array_display(arr)
        self.play(FadeIn(arr_group))
        self.wait(0.5)

        # 简化展示：展示一次分区过程
        pivot_val = arr[-1]
        pivot_label = Text(f"pivot = {pivot_val}", color=RED, font_size=24).next_to(arr_group, UP)
        self.play(Write(pivot_label))
        # 高亮pivot
        self.play(squares[-1].animate.set_fill(RED, opacity=0.3), run_time=0.3)

        # 分区动画
        i = 0
        for j in range(len(arr) - 1):
            self.play(squares[j].animate.set_fill(YELLOW, opacity=0.3), run_time=0.2)
            if arr[j] <= pivot_val:
                if i != j:
                    arr[i], arr[j] = arr[j], arr[i]
                    new_tx_i = Text(str(arr[i]), color=BLACK, font_size=22).move_to(squares[i])
                    new_tx_j = Text(str(arr[j]), color=BLACK, font_size=22).move_to(squares[j])
                    self.play(
                        Transform(texts[i], new_tx_i),
                        Transform(texts[j], new_tx_j),
                        squares[i].animate.set_fill(BLUE, opacity=0.2),
                        run_time=0.5
                    )
                i += 1
            self.play(squares[j].animate.set_fill(WHITE, opacity=0), run_time=0.1)

        # pivot归位
        arr[i], arr[-1] = arr[-1], arr[i]
        self.play(squares[i].animate.set_fill(GREEN, opacity=0.3), run_time=0.3)

        # 递归说明
        note = Text("对左右子数组递归执行分区操作", color=BLACK, font_size=20).to_edge(DOWN)
        self.play(Write(note))
        self.wait(1)

        # 最终结果
        final_arr = sorted(values)
        result = Text(f"排序完成: {final_arr}", color=BLACK, font_size=24).next_to(note, UP)
        self.play(Write(result))
        self.wait(1)
'''

_register("quick_sort", "QuickSortScene", _QUICK_SORT_SCRIPT, [
    "快速排序是一种高效的分治排序算法。",
    "首先选择一个基准值pivot，通常选择最后一个元素。",
    "分区操作：将小于等于pivot的元素放左边，大于的放右边。",
    "然后pivot归位到正确的位置。",
    "递归地对左右两个子数组执行同样的操作。",
    "快速排序平均时间复杂度为O(n log n)，最坏O(n²)。",
])


# ===== 链表 =====

_LINKED_LIST_SCRIPT = '''from manim import *

class LinkedListScene(Scene):
    def construct(self):
        self.camera.background_color = WHITE

        title = Text("链表", color=BLACK, font_size=40).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # 创建链表节点
        node_values = [1, 2, 3, 4]
        nodes = []
        arrows = []
        x_start = -4

        for i, v in enumerate(node_values):
            # 节点：数据域 + 指针域
            data_rect = Rectangle(width=0.8, height=0.6, color=BLACK, stroke_width=2)
            ptr_rect = Rectangle(width=0.4, height=0.6, color=BLACK, stroke_width=2).next_to(data_rect, RIGHT, buff=0)
            data_text = Text(str(v), color=BLACK, font_size=22).move_to(data_rect)
            node_group = VGroup(data_rect, ptr_rect, data_text).shift(RIGHT * i * 1.8 + DOWN * 0.5)
            nodes.append(node_group)
            self.play(FadeIn(node_group), run_time=0.4)

            # 箭头指向下一个节点
            if i < len(node_values) - 1:
                arrow = Arrow(
                    node_group.get_right() + RIGHT * 0.05,
                    nodes[i+1].get_left() + LEFT * 0.05 if i + 1 < len(nodes) else RIGHT * 1.5,
                    color=BLACK, stroke_width=2, buff=0.05
                )
                # 需要在下一个节点创建后添加箭头
                arrows.append(arrow)

        # 重新创建箭头（节点都已就位）
        for i in range(len(nodes) - 1):
            arrow = Arrow(
                nodes[i].get_right() + RIGHT * 0.05,
                nodes[i+1].get_left() + LEFT * 0.05,
                color=BLACK, stroke_width=2, buff=0.05
            )
            self.play(GrowArrow(arrow), run_time=0.3)

        # NULL指针
        null_text = Text("NULL", color=RED, font_size=20).next_to(nodes[-1], RIGHT, buff=0.3)
        self.play(Write(null_text))
        self.wait(0.5)

        # 头指针
        head_arrow = Arrow(UP * 1.2 + nodes[0].get_top(), nodes[0].get_top(), color=BLUE, buff=0.1)
        head_label = Text("head", color=BLUE, font_size=20).next_to(head_arrow, UP, buff=0.1)
        self.play(GrowArrow(head_arrow), Write(head_label))
        self.wait(0.5)

        # 插入操作演示
        insert_label = Text("插入节点 5 到位置2", color=BLACK, font_size=22).to_edge(DOWN)
        self.play(Write(insert_label))

        # 新节点
        new_data = Rectangle(width=0.8, height=0.6, color=GREEN, stroke_width=3)
        new_ptr = Rectangle(width=0.4, height=0.6, color=GREEN, stroke_width=3).next_to(new_data, RIGHT, buff=0)
        new_text = Text("5", color=BLACK, font_size=22).move_to(new_data)
        new_node = VGroup(new_data, new_ptr, new_text).shift(UP * 1.5)
        self.play(FadeIn(new_node))
        self.wait(0.5)

        # 移动到位置
        self.play(new_node.animate.move_to(nodes[1].get_center() + DOWN * 1.5))
        self.wait(1)

        # 总结
        summary = Text("链表: 插入O(1) 查找O(n) 删除O(1)", color=BLACK, font_size=20).to_edge(DOWN)
        self.play(Transform(insert_label, summary))
        self.wait(1)
'''

_register("linked_list", "LinkedListScene", _LINKED_LIST_SCRIPT, [
    "链表是一种动态数据结构，每个节点包含数据域和指针域。",
    "通过指针将节点串联起来，不需要连续的内存空间。",
    "链表的插入和删除操作只需要修改指针，时间复杂度为O(1)。",
    "但查找需要从头遍历，时间复杂度为O(n)。",
    "常见的链表有单链表、双链表和循环链表。",
])


# ===== 栈 =====

_STACK_SCRIPT = '''from manim import *

class StackScene(Scene):
    def construct(self):
        self.camera.background_color = WHITE

        title = Text("栈 (Stack) - 后进先出", color=BLACK, font_size=36).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # 栈容器
        stack_bottom = Line(LEFT*1.5, RIGHT*1.5, color=BLACK, stroke_width=3).shift(DOWN*2)
        stack_left = Line(LEFT*1.5, LEFT*1.5 + UP*4, color=BLACK, stroke_width=3).shift(DOWN*2)
        stack_right = Line(RIGHT*1.5, RIGHT*1.5 + UP*4, color=BLACK, stroke_width=3).shift(DOWN*2)
        stack_frame = VGroup(stack_bottom, stack_left, stack_right).shift(DOWN*0.3)
        self.play(Create(stack_frame))

        top_label = Text("栈顶 top →", color=RED, font_size=20).next_to(stack_right, RIGHT, buff=0.2).shift(DOWN*0.3)
        self.play(Write(top_label))

        # Push操作
        elements = [1, 2, 3]
        stack_items = []
        for i, v in enumerate(elements):
            rect = Rectangle(width=2.8, height=0.7, color=BLACK, stroke_width=2, fill_color=BLUE, fill_opacity=0.15)
            text = Text(str(v), color=BLACK, font_size=24).move_to(rect)
            item = VGroup(rect, text)

            # 从上方进入
            start_pos = UP * 2.5
            end_pos = DOWN * 0.3 + UP * (i * 0.75)
            item.move_to(start_pos)

            push_text = Text(f"push({v})", color=GREEN, font_size=20).to_edge(RIGHT).shift(UP * (1.5 - i * 0.5))
            self.play(FadeIn(item.copy().move_to(start_pos)), Write(push_text))
            self.play(item.animate.move_to(end_pos), run_time=0.5)
            stack_items.append(item)

            # 更新top指针
            self.play(top_label.animate.next_to(item, RIGHT, buff=0.2), run_time=0.2)
            self.wait(0.3)

        self.wait(0.5)

        # Pop操作
        pop_text = Text("pop() → 3", color=RED, font_size=20).to_edge(RIGHT).shift(DOWN * 0.5)
        self.play(Write(pop_text))
        top_item = stack_items.pop()
        self.play(top_item.animate.shift(UP * 2), run_time=0.5)
        self.play(FadeOut(top_item))

        if stack_items:
            self.play(top_label.animate.next_to(stack_items[-1], RIGHT, buff=0.2), run_time=0.2)

        # Peek操作
        peek_text = Text("peek() → 2", color=ORANGE, font_size=20).to_edge(RIGHT).shift(DOWN * 1.0)
        self.play(Write(peek_text))
        if stack_items:
            self.play(stack_items[-1][0].animate.set_fill(YELLOW, opacity=0.3), run_time=0.3)
            self.wait(0.5)
            self.play(stack_items[-1][0].animate.set_fill(BLUE, opacity=0.15), run_time=0.2)

        # 总结
        summary = Text("栈: push O(1)  pop O(1)  peek O(1)", color=BLACK, font_size=20).to_edge(DOWN)
        self.play(Write(summary))
        self.wait(1)
'''

_register("stack", "StackScene", _STACK_SCRIPT, [
    "栈是一种后进先出的数据结构，就像一摞盘子。",
    "push操作将元素压入栈顶，时间复杂度O(1)。",
    "pop操作弹出栈顶元素，时间复杂度O(1)。",
    "peek操作查看栈顶元素但不移除。",
    "栈常用于函数调用、表达式求值、括号匹配等场景。",
])


# ===== 队列 =====

_QUEUE_SCRIPT = '''from manim import *

class QueueScene(Scene):
    def construct(self):
        self.camera.background_color = WHITE

        title = Text("队列 (Queue) - 先进先出", color=BLACK, font_size=36).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # 队列容器
        queue_left = Line(DOWN*0.5, UP*0.5, color=BLACK, stroke_width=3).shift(LEFT*3.5)
        queue_right = Line(DOWN*0.5, UP*0.5, color=BLACK, stroke_width=3).shift(RIGHT*3.5)
        queue_bottom = Line(LEFT*3.5, RIGHT*3.5, color=BLACK, stroke_width=3).shift(DOWN*0.5)
        queue_top = Line(LEFT*3.5, RIGHT*3.5, color=BLACK, stroke_width=3).shift(UP*0.5)
        queue_frame = VGroup(queue_left, queue_right, queue_bottom, queue_top).shift(DOWN*0.3)
        self.play(Create(queue_frame))

        front_label = Text("队头 front", color=RED, font_size=18).next_to(queue_frame, LEFT, buff=0.2)
        rear_label = Text("队尾 rear", color=BLUE, font_size=18).next_to(queue_frame, RIGHT, buff=0.2)
        self.play(Write(front_label), Write(rear_label))

        # Enqueue操作
        elements = [1, 2, 3, 4]
        queue_items = []
        for i, v in enumerate(elements):
            rect = Rectangle(width=1.2, height=0.8, color=BLACK, stroke_width=2, fill_color=BLUE, fill_opacity=0.15)
            text = Text(str(v), color=BLACK, font_size=24).move_to(rect)
            item = VGroup(rect, text)

            x_pos = LEFT * 2.7 + RIGHT * i * 1.4
            item.move_to(x_pos + DOWN * 0.3)

            en_text = Text(f"enqueue({v})", color=GREEN, font_size=18).to_edge(DOWN).shift(LEFT * 2)
            self.play(Write(en_text), FadeIn(item, shift=RIGHT), run_time=0.5)
            queue_items.append(item)
            self.wait(0.3)

        self.wait(0.5)

        # Dequeue操作
        deq_text = Text("dequeue() → 1", color=RED, font_size=18).to_edge(DOWN).shift(RIGHT * 2)
        self.play(Write(deq_text))
        first = queue_items.pop(0)
        self.play(first.animate.shift(LEFT * 2), FadeOut(first), run_time=0.5)

        # 移动剩余元素
        for i, item in enumerate(queue_items):
            new_x = LEFT * 2.7 + RIGHT * i * 1.4 + DOWN * 0.3
            self.play(item.animate.move_to(new_x), run_time=0.3)

        self.wait(0.5)

        # 总结
        summary = Text("队列: enqueue O(1)  dequeue O(1)", color=BLACK, font_size=20).to_edge(DOWN)
        self.play(Write(summary))
        self.wait(1)
'''

_register("queue", "QueueScene", _QUEUE_SCRIPT, [
    "队列是一种先进先出的数据结构，就像排队买票。",
    "enqueue操作在队尾添加元素，时间复杂度O(1)。",
    "dequeue操作从队头移除元素，时间复杂度O(1)。",
    "队列常用于BFS遍历、任务调度、缓冲区管理等场景。",
])


# ===== 二叉树遍历 =====

_BINARY_TREE_SCRIPT = '''from manim import *

class BinaryTreeScene(Scene):
    def construct(self):
        self.camera.background_color = WHITE

        title = Text("二叉树遍历", color=BLACK, font_size=40).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # 构建二叉树
        def create_node(val, pos):
            circle = Circle(radius=0.35, color=BLACK, stroke_width=2, fill_color=WHITE, fill_opacity=1)
            text = Text(str(val), color=BLACK, font_size=20).move_to(circle)
            return VGroup(circle, text).move_to(pos)

        # 节点位置
        positions = {
            1: UP*1 + LEFT*0.5,
            2: UP*0.2 + LEFT*2,
            3: UP*0.2 + RIGHT*1,
            4: DOWN*0.6 + LEFT*3,
            5: DOWN*0.6 + LEFT*1,
        }
        values = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}

        nodes = {}
        for k, pos in positions.items():
            nodes[k] = create_node(values[k], pos)

        # 边
        edges = [(1, 2), (1, 3), (2, 4), (2, 5)]

        # 先显示树结构
        for parent_k, child_k in edges:
            edge = Line(nodes[parent_k].get_bottom(), nodes[child_k].get_top(), color=BLACK, stroke_width=2)
            self.play(Create(edge), run_time=0.3)

        for node in nodes.values():
            self.play(FadeIn(node), run_time=0.2)

        self.wait(0.5)

        # 前序遍历
        preorder_label = Text("前序遍历: 根→左→右", color=BLUE, font_size=22).to_edge(DOWN).shift(UP*0.5)
        self.play(Write(preorder_label))

        preorder = [1, 2, 4, 5, 3]
        result_text = "1 → 2 → 4 → 5 → 3"
        for k in preorder:
            self.play(nodes[k][0].animate.set_fill(YELLOW, opacity=0.4), run_time=0.3)
            self.wait(0.3)
            self.play(nodes[k][0].animate.set_fill(GREEN, opacity=0.2), run_time=0.2)

        result = Text(result_text, color=BLACK, font_size=20).next_to(preorder_label, DOWN)
        self.play(Write(result))
        self.wait(1)

        # 重置颜色
        for node in nodes.values():
            node[0].set_fill(WHITE, opacity=1)

        # 中序遍历
        inorder_label = Text("中序遍历: 左→根→右", color=BLUE, font_size=22).to_edge(DOWN).shift(UP*0.5)
        self.play(Transform(preorder_label, inorder_label), FadeOut(result))

        inorder = [4, 2, 5, 1, 3]
        result_text2 = "4 → 2 → 5 → 1 → 3"
        for k in inorder:
            self.play(nodes[k][0].animate.set_fill(YELLOW, opacity=0.4), run_time=0.3)
            self.wait(0.3)
            self.play(nodes[k][0].animate.set_fill(GREEN, opacity=0.2), run_time=0.2)

        result2 = Text(result_text2, color=BLACK, font_size=20).next_to(inorder_label, DOWN)
        self.play(Write(result2))
        self.wait(1)
'''

_register("binary_tree", "BinaryTreeScene", _BINARY_TREE_SCRIPT, [
    "二叉树是每个节点最多有两个子节点的树结构。",
    "前序遍历：先访问根节点，再遍历左子树，最后遍历右子树。",
    "中序遍历：先遍历左子树，再访问根节点，最后遍历右子树。",
    "后序遍历：先遍历左子树，再遍历右子树，最后访问根节点。",
    "层序遍历：按层从上到下，从左到右依次访问。",
])


# ===== BST =====

_BST_SCRIPT = '''from manim import *

class BSTScene(Scene):
    def construct(self):
        self.camera.background_color = WHITE

        # ===== 段落1: BST定义 (TTS~20s) =====
        title = MarkupText("二叉搜索树 BST", font="Microsoft YaHei", color=BLACK, font_size=40).to_edge(UP)
        self.play(Write(title), run_time=1.5)
        self.wait(3)

        def_text = MarkupText(
            "二叉搜索树(BST)是一种特殊的二叉树",
            font="Microsoft YaHei", color=BLACK, font_size=24
        ).next_to(title, DOWN, buff=0.6)
        self.play(Write(def_text), run_time=1.5)
        self.wait(4)

        # ===== 段落2: BST性质 (TTS~20s) =====
        prop1 = MarkupText(
            "性质：左子树所有节点值 &lt; 根节点值",
            font="Microsoft YaHei", color=BLUE, font_size=22
        ).next_to(def_text, DOWN, buff=0.4, aligned_edge=LEFT)
        self.play(Write(prop1), run_time=1)
        self.wait(2)

        prop2 = MarkupText(
            "      右子树所有节点值 &gt; 根节点值",
            font="Microsoft YaHei", color=BLUE, font_size=22
        ).next_to(prop1, DOWN, aligned_edge=LEFT)
        self.play(Write(prop2), run_time=1)
        self.wait(3)

        prop3 = MarkupText(
            "      递归定义：左右子树也是BST",
            font="Microsoft YaHei", color=BLUE, font_size=22
        ).next_to(prop2, DOWN, aligned_edge=LEFT)
        self.play(Write(prop3), run_time=1)
        self.wait(4)

        # 清屏准备构建BST
        self.play(*[FadeOut(m) for m in [title, def_text, prop1, prop2, prop3]], run_time=1)

        # ===== 段落3: 构建BST (TTS~25s) =====
        title2 = MarkupText("构建二叉搜索树", font="Microsoft YaHei", color=BLACK, font_size=36).to_edge(UP)
        self.play(Write(title2), run_time=1)

        def create_node(val, pos):
            circle = Circle(radius=0.35, color=BLACK, stroke_width=2, fill_color=WHITE, fill_opacity=1)
            text = Text(str(val), color=BLACK, font_size=20).move_to(circle)
            return VGroup(circle, text).move_to(pos)

        positions = {
            8: UP*0.8,
            3: DOWN*0.1 + LEFT*2.5,
            10: DOWN*0.1 + RIGHT*2.5,
            1: DOWN*1.2 + LEFT*4,
            6: DOWN*1.2 + LEFT*1,
            14: DOWN*1.2 + LEFT*0 + RIGHT*0,
            9: DOWN*1.2 + RIGHT*2,
        }

        nodes = {}
        insert_order = [8, 3, 10, 1, 6, 14, 9]
        parent_map = {3: 8, 10: 8, 1: 3, 6: 3, 14: 10, 9: 10}

        for val in insert_order:
            pos = positions[val]
            node = create_node(val, pos)
            nodes[val] = node

            if val in parent_map:
                parent_node = nodes[parent_map[val]]
                edge = Line(
                    parent_node.get_bottom() + DOWN*0.02,
                    node.get_top() + UP*0.02,
                    color=BLACK, stroke_width=2
                )
                self.play(Create(edge), FadeIn(node), run_time=0.8)
            else:
                self.play(FadeIn(node), run_time=1)

        self.wait(7)

        # 中序遍历标注
        inorder = MarkupText(
            "中序遍历：1 → 3 → 6 → 8 → 9 → 10 → 14",
            font="Microsoft YaHei", color=GREEN, font_size=20
        ).next_to(title2, DOWN, buff=0.5)
        self.play(Write(inorder), run_time=1.5)
        self.wait(6)

        self.play(FadeOut(inorder), run_time=0.5)

        # ===== 段落4: BST结构遍历 (TTS~20s) =====
        structure_title = MarkupText(
            "遍历BST - 验证有序性",
            font="Microsoft YaHei", color=BLACK, font_size=28
        ).to_edge(DOWN)

        self.play(FadeOut(title2), Write(structure_title), run_time=1)

        # 高亮左子树
        left_nodes = [nodes[1], nodes[3], nodes[6]]
        for n in left_nodes:
            self.play(n[0].animate.set_fill(BLUE, opacity=0.15), run_time=0.4)
        left_label = MarkupText(
            "左子树 (1,3,6) &lt; 8",
            font="Microsoft YaHei", color=BLUE, font_size=20
        ).to_edge(RIGHT).shift(UP*2)
        self.play(Write(left_label), run_time=1)
        self.wait(2)

        # 高亮右子树
        right_nodes = [nodes[9], nodes[10], nodes[14]]
        for n in right_nodes:
            self.play(n[0].animate.set_fill(RED, opacity=0.15), run_time=0.4)
        right_label = MarkupText(
            "右子树 (9,10,14) &gt; 8",
            font="Microsoft YaHei", color=RED, font_size=20
        ).next_to(left_label, DOWN, aligned_edge=LEFT)
        self.play(Write(right_label), run_time=1)
        self.wait(3)

        # 恢复颜色
        for n in list(nodes.values()):
            self.play(n[0].animate.set_fill(WHITE, opacity=1), run_time=0.2)
        self.play(FadeOut(left_label), FadeOut(right_label), run_time=1)
        self.wait(2)

        # ===== 段落5: 查找操作 (TTS~25s) =====
        self.play(FadeOut(structure_title), run_time=0.5)
        search_title = MarkupText(
            "查找操作 (search)",
            font="Microsoft YaHei", color=BLACK, font_size=30
        ).to_edge(UP)

        target = MarkupText(
            "目标值: 6",
            font="Microsoft YaHei", color=RED, font_size=22
        ).next_to(search_title, DOWN, buff=0.4)

        self.play(Write(search_title), Write(target), run_time=1)

        # 搜索路径: 8 → 3 → 6
        current = MarkupText("当前节点: 8", font="Microsoft YaHei", color=BLUE, font_size=20).to_edge(DOWN).shift(UP*0.5)
        self.play(Write(current), run_time=0.5)
        self.play(nodes[8][0].animate.set_fill(YELLOW, opacity=0.4), run_time=1)
        compare1 = MarkupText("6 &lt; 8 → 向左走", font="Microsoft YaHei", color=BLACK, font_size=18).next_to(current, DOWN)
        self.play(Write(compare1), run_time=1)
        self.wait(3)

        self.play(FadeOut(compare1), Transform(current,
            MarkupText("当前节点: 3", font="Microsoft YaHei", color=BLUE, font_size=20).to_edge(DOWN).shift(UP*0.5)),
            run_time=0.5)
        self.play(nodes[3][0].animate.set_fill(YELLOW, opacity=0.4), run_time=0.5)
        compare2 = MarkupText("6 &gt; 3 → 向右走", font="Microsoft YaHei", color=BLACK, font_size=18).next_to(current, DOWN)
        self.play(Write(compare2), run_time=1)
        self.wait(3)

        self.play(FadeOut(compare2), Transform(current,
            MarkupText("当前节点: 6 ✓", font="Microsoft YaHei", color=GREEN, font_size=20).to_edge(DOWN).shift(UP*0.5)),
            run_time=0.5)
        self.play(nodes[6][0].animate.set_fill(GREEN, opacity=0.3), run_time=1)
        self.wait(4)

        self.play(FadeOut(current), FadeOut(target),
            *[n[0].animate.set_fill(WHITE, opacity=1) for n in nodes.values()],
            run_time=1)
        self.wait(2)

        # ===== 段落6: 插入操作 (TTS~25s) =====
        self.play(FadeOut(search_title), run_time=0.5)
        insert_title = MarkupText(
            "插入操作 (insert)",
            font="Microsoft YaHei", color=BLACK, font_size=30
        ).to_edge(UP)
        insert_target = MarkupText(
            "插入值: 7",
            font="Microsoft YaHei", color=RED, font_size=22
        ).next_to(insert_title, DOWN, buff=0.4)
        self.play(Write(insert_title), Write(insert_target), run_time=1)

        insert_path = MarkupText(
            "8→3→6→右子(插入成功)",
            font="Microsoft YaHei", color=BLUE, font_size=20
        ).to_edge(DOWN).shift(UP*1)
        self.play(Write(insert_path), run_time=1)

        # 高亮搜索路径
        for val in [8, 3, 6]:
            self.play(nodes[val][0].animate.set_fill(YELLOW, opacity=0.3), run_time=0.5)
            self.wait(0.5)

        # 在6的右子位置插入7
        new_pos = nodes[6].get_bottom() + DOWN*1.0 + RIGHT*1.0
        new_node = create_node(7, new_pos)
        new_edge = Line(nodes[6].get_bottom()+DOWN*0.02, new_node.get_top()+UP*0.02,
                        color=GREEN, stroke_width=2)
        self.play(Create(new_edge), FadeIn(new_node), run_time=1)
        new_label = MarkupText("新节点: 7", font="Microsoft YaHei", color=GREEN, font_size=18).next_to(new_node, RIGHT)
        self.play(Write(new_label), run_time=1)
        self.wait(4)

        # 清理插入相关的标注
        self.play(FadeOut(new_label), FadeOut(insert_path), FadeOut(insert_target),
                  *[n[0].animate.set_fill(WHITE, opacity=1) for n in nodes.values()],
                  run_time=1)
        self.play(FadeOut(insert_title), run_time=0.5)
        self.wait(2)

        # ===== 段落7: 复杂度与平衡问题 (TTS~25s) =====
        # 展示平衡树vs退化树
        balance_title = MarkupText(
            "复杂度分析",
            font="Microsoft YaHei", color=BLACK, font_size=36
        ).to_edge(UP)
        self.play(Write(balance_title), run_time=1)

        # 平均情况
        avg_text = MarkupText(
            "平衡BST: 查找/插入/删除 O(log n)",
            font="Microsoft YaHei", color=GREEN, font_size=22
        ).next_to(balance_title, DOWN, buff=0.5)
        self.play(Write(avg_text), run_time=1)
        self.wait(3)

        # 最坏情况
        worst_text = MarkupText(
            "退化BST(链状): O(n)",
            font="Microsoft YaHei", color=RED, font_size=22
        ).next_to(avg_text, DOWN, buff=0.3)
        self.play(Write(worst_text), run_time=1)

        # 画一个退化链
        chain_nodes = []
        chain_vals = [1, 2, 3, 4, 5]
        for i, val in enumerate(chain_vals):
            pos = UP*2.5 + DOWN*(i*0.8) + RIGHT*4.5
            c = Circle(radius=0.25, color=RED, stroke_width=2, fill_color=WHITE, fill_opacity=1)
            t = Text(str(val), color=RED, font_size=16).move_to(c)
            gn = VGroup(c, t).move_to(pos)
            chain_nodes.append(gn)
            self.play(FadeIn(gn), run_time=0.3)
            if i > 0:
                e = Line(chain_nodes[i-1].get_bottom()+DOWN*0.02, gn.get_top()+UP*0.02,
                         color=RED, stroke_width=1.5)
                self.play(Create(e), run_time=0.2)

        chain_label = MarkupText(
            "退化为链表",
            font="Microsoft YaHei", color=RED, font_size=18
        ).next_to(chain_nodes[-1], DOWN, buff=0.3)
        self.play(Write(chain_label), run_time=1)
        self.wait(4)

        # ===== 段落8: 总结与应用 (TTS~30s) =====
        # 清屏
        self.play(*[FadeOut(m) for m in [balance_title, avg_text, worst_text,
            chain_label] + chain_nodes +
            [e for e in self.mobjects if hasattr(e, 'get_stroke_color')]],
            *[FadeOut(n) for n in nodes.values()],
            FadeOut(new_node), FadeOut(new_edge),
            run_time=1.5)

        summary_title = MarkupText(
            "总结",
            font="Microsoft YaHei", color=BLACK, font_size=36
        ).to_edge(UP)
        self.play(Write(summary_title), run_time=1)

        summaries = [
            ("定义", "左子树&lt;根&lt;右子树"),
            ("查找", "O(log n)平均 / O(n)最坏"),
            ("插入/删除", "先查找再操作, 时间复杂度同查找"),
            ("应用", "数据库索引、集合/映射、排序"),
            ("衍生", "AVL树、红黑树、B树等"),
        ]

        s_icons = []
        for i, (key, val) in enumerate(summaries):
            pos = UP*1.5 + DOWN*(i*0.7)
            key_icon = MarkupText(
                key + ":", font="Microsoft YaHei", color=BLUE, font_size=22
            ).move_to(pos + LEFT*3)
            val_text = MarkupText(
                val, font="Microsoft YaHei", color=BLACK, font_size=20
            ).next_to(key_icon, RIGHT, buff=0.3)
            self.play(Write(key_icon), Write(val_text), run_time=0.6)
            s_icons.extend([key_icon, val_text])

        self.wait(8)

        # 最终画面
        end_text = MarkupText(
            "下一讲：AVL树 - 自平衡二叉搜索树",
            font="Microsoft YaHei", color=GREEN, font_size=26
        ).to_edge(DOWN).shift(UP*0.5)
        self.play(Write(end_text), run_time=1.5)
        self.wait(10)
'''

_register("bst", "BSTScene", _BST_SCRIPT, [
    "二叉搜索树是一种特殊的二叉树，满足左子树所有值小于根，右子树所有值大于根。",
    "查找时，从根节点开始，目标值小于当前节点则向左，大于则向右。",
    "平均情况下查找时间复杂度为O(log n)。",
    "但如果树退化为链表，最坏情况为O(n)。",
    "插入和删除操作也基于查找，时间复杂度同理。",
])


# ===== AVL树 =====

_AVL_SCRIPT = '''from manim import *

class AVLScene(Scene):
    def construct(self):
        self.camera.background_color = WHITE

        title = Text("AVL树 - 自平衡二叉搜索树", color=BLACK, font_size=36).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # 平衡因子说明
        bf_text = Text("平衡因子 = 左子树高度 - 右子树高度", color=BLUE, font_size=20).next_to(title, DOWN)
        self.play(Write(bf_text))
        self.wait(0.5)

        # 展示不平衡的情况
        unbal_title = Text("不平衡BST:", color=RED, font_size=22).shift(LEFT*3 + UP*0.5)
        self.play(Write(unbal_title))

        # 链状BST
        def create_node(val, pos):
            circle = Circle(radius=0.3, color=BLACK, stroke_width=2, fill_color=WHITE, fill_opacity=1)
            text = Text(str(val), color=BLACK, font_size=18).move_to(circle)
            return VGroup(circle, text).move_to(pos)

        # 不平衡: 1->2->3->4
        unbal_nodes = []
        for i, v in enumerate([1, 2, 3, 4]):
            node = create_node(v, LEFT*3 + DOWN*0.3 + UP*(3-i)*0.8)
            unbal_nodes.append(node)

        for i in range(len(unbal_nodes)-1):
            edge = Line(unbal_nodes[i].get_bottom(), unbal_nodes[i+1].get_top(), color=BLACK, stroke_width=2)
            self.play(Create(edge), run_time=0.2)
        for node in unbal_nodes:
            self.play(FadeIn(node), run_time=0.2)

        bf_bad = Text("BF=3 不平衡!", color=RED, font_size=16).next_to(unbal_nodes[0], LEFT, buff=0.2)
        self.play(Write(bf_bad))
        self.wait(0.5)

        # 展示旋转后的平衡AVL
        bal_title = Text("AVL旋转后:", color=GREEN, font_size=22).shift(RIGHT*3 + UP*0.5)
        self.play(Write(bal_title))

        bal_positions = {
            2: RIGHT*3 + UP*0.8,
            1: RIGHT*1.5 + DOWN*0.3,
            3: RIGHT*4.5 + DOWN*0.3,
        }
        bal_nodes = {}
        for v, pos in bal_positions.items():
            bal_nodes[v] = create_node(v, pos)

        bal_edges = [(2, 1), (2, 3)]
        for pv, cv in bal_edges:
            edge = Line(bal_nodes[pv].get_bottom(), bal_nodes[cv].get_top(), color=BLACK, stroke_width=2)
            self.play(Create(edge), run_time=0.2)
        for node in bal_nodes.values():
            self.play(FadeIn(node), run_time=0.2)

        bf_good = Text("BF=0 平衡!", color=GREEN, font_size=16).next_to(bal_nodes[2], RIGHT, buff=0.3)
        self.play(Write(bf_good))
        self.wait(0.5)

        # 旋转类型
        rot_text = Text("四种旋转: LL右旋 RR左旋 LR先左后右 RL先右后左", color=BLACK, font_size=18).to_edge(DOWN)
        self.play(Write(rot_text))
        self.wait(1)
'''

_register("avl", "AVLScene", _AVL_SCRIPT, [
    "AVL树是一种自平衡二叉搜索树，任何节点的左右子树高度差不超过1。",
    "平衡因子等于左子树高度减去右子树高度，取值范围为-1、0、1。",
    "当插入或删除导致不平衡时，通过旋转操作恢复平衡。",
    "四种旋转类型：LL型右旋、RR型左旋、LR型先左旋再右旋、RL型先右旋再左旋。",
    "AVL树保证查找、插入、删除的时间复杂度均为O(log n)。",
])


# ===== 哈希表 =====

_HASH_TABLE_SCRIPT = '''from manim import *

class HashTableScene(Scene):
    def construct(self):
        self.camera.background_color = WHITE

        title = Text("哈希表", color=BLACK, font_size=40).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # 哈希函数说明
        hash_func = Text("hash(key) = key % 7", color=BLUE, font_size=22).next_to(title, DOWN)
        self.play(Write(hash_func))
        self.wait(0.5)

        # 桶数组
        num_buckets = 7
        buckets = []
        bucket_texts = []
        for i in range(num_buckets):
            rect = Rectangle(width=1.0, height=0.6, color=BLACK, stroke_width=2)
            idx_text = Text(str(i), color=BLACK, font_size=18).move_to(rect)
            rect_group = VGroup(rect, idx_text).shift(RIGHT * (i - num_buckets/2 + 0.5) * 1.2 + DOWN * 0.5)
            buckets.append(rect_group)
            bucket_texts.append(idx_text)

        buckets_group = VGroup(*buckets)
        self.play(FadeIn(buckets_group))
        self.wait(0.3)

        # 插入操作
        inserts = [("a", 1), ("d", 4), ("f", 6), ("q", 17)]

        for key, val in inserts:
            idx = val % 7
            # 显示哈希计算
            calc = Text(f'hash("{key}") = {val} % 7 = {idx}', color=BLACK, font_size=18).to_edge(DOWN).shift(UP*0.5)
            self.play(Write(calc))

            # 高亮桶
            self.play(buckets[idx][0].animate.set_fill(YELLOW, opacity=0.3), run_time=0.3)

            # 在桶中添加元素
            entry = Text(f"{key}:{val}", color=BLACK, font_size=14).next_to(buckets[idx], DOWN, buff=0.1)
            self.play(Write(entry))
            self.wait(0.3)

            self.play(buckets[idx][0].animate.set_fill(WHITE, opacity=0), FadeOut(calc), run_time=0.2)

        # 冲突演示
        conflict_title = Text("冲突: d和q都映射到桶4", color=RED, font_size=20).to_edge(DOWN)
        self.play(Write(conflict_title))
        self.play(buckets[4][0].animate.set_fill(RED, opacity=0.2), run_time=0.3)
        self.wait(0.5)

        # 链地址法
        chain_text = Text("链地址法: 同一桶用链表存储", color=GREEN, font_size=20).next_to(conflict_title, UP)
        self.play(Write(chain_text))
        self.wait(1)

        # 总结
        summary = Text("哈希表: 平均查找O(1) 最坏O(n)", color=BLACK, font_size=20).to_edge(DOWN)
        self.play(Write(summary))
        self.wait(1)
'''

_register("hash_table", "HashTableScene", _HASH_TABLE_SCRIPT, [
    "哈希表通过哈希函数将键映射到数组索引，实现快速查找。",
    "哈希函数的设计直接影响哈希表的性能。",
    "当不同的键映射到同一个索引时，就发生了哈希冲突。",
    "常见的冲突解决方法有链地址法和开放地址法。",
    "平均情况下哈希表的查找时间复杂度为O(1)。",
])


# ===== 图BFS =====

_GRAPH_BFS_SCRIPT = '''from manim import *

class GraphBFSScene(Scene):
    def construct(self):
        self.camera.background_color = WHITE

        title = Text("图 - 广度优先搜索 BFS", color=BLACK, font_size=36).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # 创建图节点
        node_positions = {
            "A": LEFT*3 + UP*1,
            "B": LEFT*1 + UP*1,
            "C": RIGHT*1 + UP*1,
            "D": LEFT*2 + DOWN*0.5,
            "E": RIGHT*2 + DOWN*0.5,
        }

        nodes = {}
        for name, pos in node_positions.items():
            circle = Circle(radius=0.35, color=BLACK, stroke_width=2, fill_color=WHITE, fill_opacity=1)
            text = Text(name, color=BLACK, font_size=22).move_to(circle)
            node = VGroup(circle, text).move_to(pos)
            nodes[name] = node

        # 边
        edge_pairs = [("A", "B"), ("A", "D"), ("B", "C"), ("B", "D"), ("C", "E"), ("D", "E")]

        for n1, n2 in edge_pairs:
            edge = Line(nodes[n1].get_center(), nodes[n2].get_center(), color=BLACK, stroke_width=2)
            self.play(Create(edge), run_time=0.2)

        for node in nodes.values():
            self.play(FadeIn(node), run_time=0.15)

        self.wait(0.5)

        # BFS过程
        queue_label = Text("队列: ", color=BLUE, font_size=20).to_edge(DOWN).shift(UP*0.8)
        self.play(Write(queue_label))

        bfs_order = ["A", "B", "D", "C", "E"]
        visited = set()
        queue_display = ["A"]

        for node_name in bfs_order:
            if node_name in visited:
                continue
            visited.add(node_name)

            # 高亮当前节点
            self.play(nodes[node_name][0].animate.set_fill(YELLOW, opacity=0.4), run_time=0.3)

            # 更新队列显示
            q_text = Text(f"队列: {queue_display}", color=BLUE, font_size=18).next_to(queue_label, RIGHT)
            self.play(Write(q_text), run_time=0.2)

            self.wait(0.3)
            self.play(nodes[node_name][0].animate.set_fill(GREEN, opacity=0.2), run_time=0.2)

            if queue_display and queue_display[0] == node_name:
                queue_display.pop(0)

        # 结果
        result = Text(f"BFS顺序: {' → '.join(bfs_order)}", color=BLACK, font_size=22).to_edge(DOWN)
        self.play(Write(result))
        self.wait(1)
'''

_register("graph_basics", "GraphBFSScene", _GRAPH_BFS_SCRIPT, [
    "广度优先搜索BFS是一种图的遍历算法，使用队列实现。",
    "从起始节点开始，先访问所有相邻节点，再逐层向外扩展。",
    "BFS使用队列来管理待访问的节点，保证按层次顺序遍历。",
    "BFS常用于求最短路径、层序遍历等场景。",
    "时间复杂度为O(V+E)，V是顶点数，E是边数。",
])


# ===== 图DFS =====

_GRAPH_DFS_SCRIPT = '''from manim import *

class GraphDFSScene(Scene):
    def construct(self):
        self.camera.background_color = WHITE

        title = Text("图 - 深度优先搜索 DFS", color=BLACK, font_size=36).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # 创建图节点
        node_positions = {
            "A": LEFT*3 + UP*1,
            "B": LEFT*1 + UP*1,
            "C": RIGHT*1 + UP*1,
            "D": LEFT*2 + DOWN*0.5,
            "E": RIGHT*2 + DOWN*0.5,
        }

        nodes = {}
        for name, pos in node_positions.items():
            circle = Circle(radius=0.35, color=BLACK, stroke_width=2, fill_color=WHITE, fill_opacity=1)
            text = Text(name, color=BLACK, font_size=22).move_to(circle)
            node = VGroup(circle, text).move_to(pos)
            nodes[name] = node

        edge_pairs = [("A", "B"), ("A", "D"), ("B", "C"), ("B", "D"), ("C", "E"), ("D", "E")]

        for n1, n2 in edge_pairs:
            edge = Line(nodes[n1].get_center(), nodes[n2].get_center(), color=BLACK, stroke_width=2)
            self.play(Create(edge), run_time=0.2)

        for node in nodes.values():
            self.play(FadeIn(node), run_time=0.15)

        self.wait(0.5)

        # DFS过程
        stack_label = Text("栈: ", color=RED, font_size=20).to_edge(DOWN).shift(UP*0.8)
        self.play(Write(stack_label))

        dfs_order = ["A", "B", "D", "E", "C"]
        visited = set()

        for node_name in dfs_order:
            if node_name in visited:
                continue
            visited.add(node_name)

            # 高亮当前节点
            self.play(nodes[node_name][0].animate.set_fill(YELLOW, opacity=0.4), run_time=0.3)

            s_text = Text(f"栈: {list(reversed(dfs_order[:dfs_order.index(node_name)+1]))}", color=RED, font_size=18).next_to(stack_label, RIGHT)
            self.play(Write(s_text), run_time=0.2)

            self.wait(0.3)
            self.play(nodes[node_name][0].animate.set_fill(GREEN, opacity=0.2), run_time=0.2)

        # 结果
        result = Text(f"DFS顺序: {' → '.join(dfs_order)}", color=BLACK, font_size=22).to_edge(DOWN)
        self.play(Write(result))
        self.wait(1)
'''

_register("graph_traversal", "GraphDFSScene", _GRAPH_DFS_SCRIPT, [
    "深度优先搜索DFS是一种图的遍历算法，使用栈或递归实现。",
    "从起始节点开始，沿着一条路径尽可能深入，直到无法继续再回溯。",
    "DFS使用栈来管理待访问的节点，保证一条路走到底。",
    "DFS常用于拓扑排序、连通分量检测、迷宫求解等场景。",
    "时间复杂度为O(V+E)，与BFS相同，但遍历顺序不同。",
])


# ===== 获取模板的辅助函数 =====

# 中文知识点 -> 模板key 的映射（支持模糊匹配）
_CN_ALIAS = {
    "冒泡排序": "bubble_sort",
    "冒泡": "bubble_sort",
    "快速排序": "quick_sort",
    "快排": "quick_sort",
    "链表": "linked_list",
    "单链表": "linked_list",
    "栈": "stack",
    "队列": "queue",
    "二叉树": "binary_tree",
    "二叉搜索树": "bst",
    "二叉查找树": "bst",
    "BST": "bst",
    "AVL树": "avl",
    "AVL": "avl",
    "平衡二叉树": "avl",
    "哈希表": "hash_table",
    "散列表": "hash_table",
    "图": "graph_basics",
    "图的遍历": "graph_traversal",
    "BFS": "graph_basics",
    "广度优先搜索": "graph_basics",
    "DFS": "graph_traversal",
    "深度优先搜索": "graph_traversal",
}


def get_manim_template(knowledge_point: str) -> dict | None:
    """获取知识点对应的Manim模板

    支持英文key直接匹配和中文模糊匹配。

    Returns:
        {"scene_class": str, "script": str, "narrations": list[str]} 或 None
    """
    # 1. 直接key匹配
    if knowledge_point in MANIM_TEMPLATES:
        return MANIM_TEMPLATES[knowledge_point]

    # 2. 中文别名精确匹配
    if knowledge_point in _CN_ALIAS:
        key = _CN_ALIAS[knowledge_point]
        return MANIM_TEMPLATES.get(key)

    # 3. 中文模糊匹配：知识点包含中文关键词
    for cn, key in _CN_ALIAS.items():
        if cn in knowledge_point or knowledge_point in cn:
            return MANIM_TEMPLATES.get(key)

    return None


def list_available_templates() -> list[dict]:
    """列出所有可用的Manim模板"""
    result = []
    for kp, template in MANIM_TEMPLATES.items():
        result.append({
            "knowledge_point": kp,
            "scene_class": template["scene_class"],
            "narration_count": len(template["narrations"]),
        })
    return result
