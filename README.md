# AI 多智能体个性化学习系统

> 参赛项目：XH-202630「领域知识个性化生成与多智能体协同决策系统研究」（2026"挑战杯"揭榜挂帅专项赛 · 人工智能领域）
> 技术栈：Vue 3 + FastAPI + LangGraph + ChromaDB + DeepSeek

## 项目简介

基于多智能体架构的领域知识个性化学习系统，聚焦数据结构课程。学生以自然语言对话即可获得"个性化画像 → 学习路径规划 → 文档/题目/思维导图/讲解视频多模态资源自动生成 → 学习评估"的一站式教学闭环。

## 系统架构

```
frontend/ (Vue 3, 端口 5173)          # 14 个功能模块，含数据大屏
backend/  (FastAPI, 端口 8000)        # JWT 认证 / 对话代理 / 社区 / 管理后台
ai-tutor/ (FastAPI, 端口 8001)        # 多智能体中枢（核心）
  ├── core/orchestrator.py            # 编排器：意图拆解 → DAG 调度 → 结果编织
  ├── core/true_agent.py              # TrueAgent 抽象：think → execute → reflect
  ├── agents/                         # 10 个专业 Agent + LangGraph 状态图调度
  ├── services/                       # 视频生成 / 代码沙箱 / 评估 / 画像等
  └── knowledge/                      # 领域知识库（ChromaDB RAG + 本地 embedding）
simulation/ (独立仿真验证框架)          # 虚拟用户 + 自动评测（见下文）
```

**多智能体协同**：Orchestrator 中枢 + 10 个专职 Agent（画像/文档/题库/代码/路径/多模态/辅导/阅读/评估/视频），LLM 意图分解 → 按依赖分层并行执行（asyncio.gather）→ 结果整合流式输出。每个 Agent 实现 think/execute/reflect 三阶段，自带质量自省与重试。

**领域知识个性化生成**：9 维画像（专业/水平/认知风格/学习节奏等）× 教学法驱动生成（五段式结构、认知风格适配、68 条事实核查、遗忘曲线调度）。

## 快速运行

```bash
# 1. 创建虚拟环境并安装依赖（Python 3.10+）
python -m venv venv
venv/Scripts/pip install -r ai-tutor/requirements.txt

# 2. 配置 API Key（ai-tutor/.env，参考 .env.example）
#    DEEPSEEK_API_KEY=xxx / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL
#    本地开发建议 DATABASE_TYPE=sqlite（免 MySQL/Redis）

# 3. 启动 AI Tutor（核心服务）
venv/Scripts/python -m uvicorn app.main:app --port 8001 --app-dir ai-tutor

# 4.（可选）启动主后端与前端，见 安装部署说明.md
```

## 协同决策审计

每次对话自动记录「意图 → 调度 Agent → DAG → 耗时」到 `ai-tutor/data/decision_audit.jsonl`，可查询：

```bash
curl "http://localhost:8001/api/audit/decisions?limit=20"
```

## 仿真验证框架（simulation/）

用虚拟用户（4 维画像 × 8 类交互场景）驱动系统做自动化验证，指标覆盖：意图识别召回/调度精确率、端到端成功率、生成质量、个性化差异度。详见 `simulation/README.md`。

```bash
cd simulation
python run_simulation.py --dry            # 预览虚拟用户与剧本
python run_simulation.py --users 20       # 运行完整验证（约 1 元 API 费用）
# 报告输出：simulation/output/simulation_report.{md,json}
```

## 修复记录（2026-09-01）

本次运行修复了以下原有问题（均因 Python 3.13 环境暴露）：

| 文件 | 问题 | 修复 |
|---|---|---|
| `agents/teacher/agent.py` | 工具定义中 `"default": true` 为 JS 风格字面量，触发 NameError | 改为 `True` |
| `agents/teacher/agent.py` | `AGENT_DISPATCHERS` 在函数定义前引用函数名 | 改为字符串名 + `globals()` 惰性解析 |
| `core/orchestrator.py` | `run_in_executor(None, next, gen)` 在 Py3.13 下 StopIteration 无法跨 Future 传播 | 新增 `_safe_next()` 哨兵包装 |

新增功能：
- `services/audit_service.py` + `api/audit.py`：协同决策审计日志与查询接口
- `simulation/`：虚拟用户仿真与自动评测框架

## 验证数据（2026-09-01 实测）

- 33 次端到端多智能体任务，成功率 **100%**
- 意图识别召回率 **1.0**，调度 F1 0.79~0.96
- 个性化差异度（同知识点不同画像生成内容相似度）**0.15 左右**，验证个性化有效
