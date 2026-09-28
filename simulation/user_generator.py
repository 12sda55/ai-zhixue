# -*- coding: utf-8 -*-
"""虚拟用户生成器 — 生成多样化画像 + 交互剧本

设计依据（对应榜题"领域知识个性化生成与多智能体协同决策"）：
- 画像空间 × 交互剧本 → 覆盖"个性化输入"的多样性
- 每个剧本标注【预期调度的 Agent】，供评测器做"意图-调度一致性"比对
"""
import itertools
import random
from config import PROFILE_SPACE, NUM_USERS, SCENARIOS_PER_USER, USER_ID_PREFIX

# 领域知识库（数据结构课程知识点，对应系统知识图谱）
KNOWLEDGE_POINTS = [
    "数组", "链表", "栈", "队列", "哈希表", "二叉树", "二叉搜索树",
    "堆", "快速排序", "归并排序", "二分查找", "递归", "图", "动态规划",
]

# 交互剧本模板: (触发场景, 预期Agent列表, 请求构造函数)
# 预期Agent: profile_agent/document_agent/question_agent/path_agent/code_agent/
#            multimodal_agent/tutor_agent/reading_agent/assessment_agent
SCENARIO_TEMPLATES = [
    {
        "name": "讲解知识",
        # 对齐系统"学习资料三件套"设计：文档生成 + 可视化联动（实测讲解场景均自动补充 multimodal_agent）
        "expected_agents": ["document_agent", "multimodal_agent"],
        "build": lambda kp, u: f"我不太理解{kp}这个概念，能详细讲一下吗？{u['style_hint']}",
    },
    {
        "name": "出题练习",
        "expected_agents": ["question_agent"],
        "build": lambda kp, u: f"帮我出几道关于{kp}的练习题，我要检验一下掌握程度",
    },
    {
        "name": "学习规划",
        "expected_agents": ["path_agent", "profile_agent"],
        "build": lambda kp, u: f"我想系统学习{kp}，帮我规划一条学习路径，{u['goal']}",
    },
    {
        "name": "学习评估",
        "expected_agents": ["assessment_agent"],
        "build": lambda kp, u: f"帮我评估一下我对{kp}的学习效果，学得怎么样",
    },
    {
        "name": "代码实操",
        "expected_agents": ["code_agent"],
        "build": lambda kp, u: f"我想用代码实现一下{kp}，给我一个可运行的示例",
    },
    {
        "name": "深度答疑",
        "expected_agents": ["tutor_agent"],
        "build": lambda kp, u: f"为什么{kp}要这样设计？我一直想不通，能给我讲讲原理吗",
    },
    {
        "name": "拓展阅读",
        "expected_agents": ["reading_agent"],
        "build": lambda kp, u: f"关于{kp}，有什么拓展阅读资料或推荐书籍吗",
    },
    {
        "name": "综合学习",
        # 对齐"学习资料三件套"：讲解 + 出题 + 可视化联动
        "expected_agents": ["document_agent", "question_agent", "multimodal_agent"],
        "build": lambda kp, u: f"帮我讲一下{kp}，然后出几道题让我巩固一下",
    },
]

# 认知风格提示词（让请求带上画像特征，验证系统是否感知画像）
STYLE_HINTS = {
    "视觉型": "最好有图示或类比帮助理解",
    "文字型": "尽量严谨，给出推导过程",
    "实践型": "多给代码示例和实际应用场景",
}


def generate_users(n: int = None) -> list[dict]:
    """生成 n 个虚拟用户，每个用户带画像 + 交互剧本列表"""
    n = n or NUM_USERS
    users = []
    keys = list(PROFILE_SPACE.keys())
    combos = list(itertools.product(*[PROFILE_SPACE[k] for k in keys]))
    random.shuffle(combos)

    for i in range(min(n, len(combos))):
        combo = combos[i]
        profile = dict(zip(keys, combo))
        style = profile["style"]
        user = {
            "user_id": f"{USER_ID_PREFIX}{i:03d}",
            "profile": profile,
            "style_hint": STYLE_HINTS.get(style, ""),
            "scenarios": [],
            **profile,  # 画像字段展开到顶层，供剧本模板直接引用
        }
        # 每个用户抽取 SCENARIOS_PER_USER 个剧本
        chosen = random.sample(SCENARIO_TEMPLATES, min(SCENARIOS_PER_USER, len(SCENARIO_TEMPLATES)))
        for idx, sc in enumerate(chosen):
            kp = random.choice(KNOWLEDGE_POINTS)
            user["scenarios"].append({
                "name": sc["name"],
                "knowledge_point": kp,
                "expected_agents": list(sc["expected_agents"]),
                "message": sc["build"](kp, user),
                "scenario_id": f"{user['user_id']}-s{idx}",
            })
        users.append(user)
    return users


def get_diversity_pairs(kps: list[str]) -> list[dict]:
    """构造个性化差异度对比组：同一知识点 × 不同画像（视觉/文字/实践）"""
    pairs = []
    for kp in kps:
        styles = ["视觉型", "文字型", "实践型"]
        for style in styles:
            pairs.append({
                "knowledge_point": kp,
                "style": style,
                "message": f"请详细讲解{kp}，{STYLE_HINTS[style]}",
                # 讲解场景对齐"文档+可视化联动"设计
                "expected_agents": ["document_agent", "multimodal_agent"],
            })
    return pairs


if __name__ == "__main__":
    users = generate_users(3)
    for u in users:
        print(u["user_id"], u["profile"])
        for s in u["scenarios"]:
            print("   ", s["name"], "->", s["expected_agents"], "|", s["message"][:40])
