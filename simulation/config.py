# -*- coding: utf-8 -*-
"""仿真验证框架配置 — XH-202630 领域知识个性化生成与多智能体协同决策系统研究

所有参数集中在此，按需修改后运行 run_simulation.py
"""

# ========== 系统 API 配置 ==========
API_BASE = "http://localhost:8001"          # ai-tutor 服务地址（后端端口）
CHAT_ENDPOINT = "/api/chat/"              # 非流式对话接口（ai-tutor 路由前缀 /api/chat）
REQUEST_TIMEOUT = 180                        # 单次请求超时（秒），多Agent生成可能较慢
MAX_CONCURRENT = 2                           # 并发数（与后端 Semaphore(2) 匹配，避免打爆限流）

# ========== 仿真规模 ==========
NUM_USERS = 20                               # 虚拟用户数量
SCENARIOS_PER_USER = 3                       # 每个用户执行的交互剧本数（总请求数 = NUM_USERS × SCENARIOS_PER_USER）
USER_ID_PREFIX = "sim_user_"                 # 虚拟用户 ID 前缀（与实际用户区分，便于在系统内识别）

# ========== 评测开关 ==========
# 1. 意图-调度正确性：请求预期调度的 Agent 与实际 agent_calls 比对（无需外部 LLM）
EVAL_INTENT = True
# 2. 个性化差异度：同一知识点、不同画像 → 回复文本相似度（字符 n-gram Jaccard）
EVAL_DIVERSITY = True
DIVERSITY_KNOWLEDGE_POINTS = ["二叉树", "快速排序", "动态规划"]   # 用于差异度对比的知识点
# 3. 生成质量：规则评分（结构完整/长度/知识点覆盖）+ 可选 LLM-as-Judge
EVAL_QUALITY = True
#    LLM-as-Judge（可选）：填了 key 则启用，用大模型对生成内容 1-5 打分
JUDGE_API_KEY = ""                            # 例如智谱 key（留空则只用规则评分）
JUDGE_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
JUDGE_MODEL = "glm-4.7-flash"

# ========== 报告输出 ==========
OUTPUT_DIR = "output"                         # 相对本目录的报告输出文件夹

# ========== 虚拟用户画像空间 ==========
# 每个维度取值会组合生成多样化的虚拟用户，用于验证"个性化"
PROFILE_SPACE = {
    "major": ["计算机", "软件工程", "信息管理", "非计算机"],       # 专业背景
    "level": ["基础", "中级", "高级"],                             # 知识水平
    "style": ["视觉型", "文字型", "实践型"],                       # 认知风格
    "goal": ["考研", "期末考试", "面试算法", "兴趣学习"],           # 学习目标
}
