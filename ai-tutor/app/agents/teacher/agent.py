"""虚拟老师Agent - Orchestrator模式

对照 ai_architecture_plan.md：
- 统一入口：学生只和虚拟老师对话
- 智能调度：Function Calling调用7个专业Agent
- 上下文管理：摘要压缩 + 画像感知
- 可视化：状态条 + 小DAG流程图

LangGraph状态图：
    START → route_intent → [agent_nodes] → integrate_response → END
                                  ↑              |
                                  └──────────────┘ (最多5轮)
"""

from __future__ import annotations
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from app.core.llm import llm_client
from app.schemas.profile import StudentProfile
from app.agents.teacher.dispatcher import (
    validate_agent_args, apply_fallback_rules, check_call_limit,
    get_execution_plan, normalize_knowledge_point,
)
from app.agents.teacher.context import context_manager

logger = logging.getLogger(__name__)

# ===== Agent名称枚举 =====

class AgentName(str, Enum):
    """10个Agent名称"""
    PROFILE = "profile_agent"           # 画像构建Agent
    DOCUMENT = "document_agent"         # 文档生成Agent
    QUESTION = "question_agent"         # 题库生成Agent
    CODE = "code_agent"                 # 代码实操Agent
    PATH = "path_agent"                 # 路径规划Agent
    MULTIMODAL = "multimodal_agent"     # 多模态资源Agent
    TUTOR = "tutor_agent"               # 智能辅导Agent
    READING = "reading_agent"           # 拓展阅读Agent
    ASSESSMENT = "assessment_agent"     # 评估Agent
    TEACHER = "teacher_agent"           # 虚拟老师自身（直接回答）


# ===== Function Calling Tool定义 =====

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "profile_agent",
            "description": (
                "画像构建Agent：管理学生9维度画像（专业背景、知识基础、薄弱环节等）。"
                "适用场景：查询/更新学生画像、冷启动画像构建、获取学习进度。"
                "当需要了解学生当前状态、薄弱环节、知识掌握度时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["get_profile", "get_radar", "get_dashboard", "init_profile", "update_profile"],
                        "description": "画像操作类型"
                    },
                    "user_id": {"type": "string", "description": "用户ID"},
                    "data": {
                        "type": "object",
                        "description": "操作数据（如初始化参数、更新字段等）",
                        "default": {}
                    }
                },
                "required": ["action", "user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "document_agent",
            "description": (
                "文档生成Agent：基于RAG知识库生成个性化学习文档。"
                "适用场景：学生想学习某个知识点、需要概念讲解、原理分析、伪代码说明。"
                "当学生说'帮我讲一下XX'、'我不理解XX'、'XX是什么'时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "knowledge_point": {
                        "type": "string",
                        "description": "知识点名称（如array、bst、dfs等）"
                    },
                    "user_id": {"type": "string", "description": "用户ID"},
                    "style": {
                        "type": "string",
                        "enum": ["concept", "principle", "code_example", "comparison"],
                        "description": "文档风格：概念讲解/原理分析/代码示例/对比分析",
                        "default": "concept"
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["basic", "intermediate", "advanced"],
                        "description": "难度级别",
                        "default": "intermediate"
                    }
                },
                "required": ["knowledge_point", "user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "question_agent",
            "description": (
                "题库生成Agent：根据画像生成阶梯式练习题。"
                "适用场景：学生想练习某个知识点、需要测试、想检验掌握程度。"
                "当学生说'给我出题'、'我想练习XX'、'测试一下'时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "knowledge_point": {
                        "type": "string",
                        "description": "知识点名称"
                    },
                    "user_id": {"type": "string", "description": "用户ID"},
                    "question_type": {
                        "type": "string",
                        "enum": ["choice", "fill_blank", "judge", "code", "analysis"],
                        "description": "题目类型：选择题/填空题/判断题/编程题/分析题",
                        "default": "choice"
                    },
                    "count": {
                        "type": "integer",
                        "description": "题目数量",
                        "default": 3
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["basic", "intermediate", "advanced"],
                        "description": "难度级别",
                        "default": "intermediate"
                    }
                },
                "required": ["knowledge_point", "user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "code_agent",
            "description": (
                "代码实操Agent：提供代码模板、AI解析、沙箱运行、性能对比。"
                "适用场景：学生想写代码练习、需要代码示例、想看算法实现、代码性能分析。"
                "当学生说'帮我写XX代码'、'XX怎么实现'、'运行一下'时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "knowledge_point": {
                        "type": "string",
                        "description": "知识点名称"
                    },
                    "user_id": {"type": "string", "description": "用户ID"},
                    "action": {
                        "type": "string",
                        "enum": ["template", "explain", "run", "compare", "fill_blank"],
                        "description": "操作类型：代码模板/AI解析/沙箱运行/算法对比/代码填空",
                        "default": "template"
                    },
                    "code": {
                        "type": "string",
                        "description": "用户提交的代码（运行/解析时需要）",
                        "default": ""
                    }
                },
                "required": ["knowledge_point", "user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "path_agent",
            "description": (
                "路径规划Agent：基于知识依赖图和画像生成个性化学习路径。"
                "适用场景：学生想制定学习计划、查看学习路径、不知道接下来学什么。"
                "当学生说'我该怎么学'、'下一步学什么'、'帮我规划'时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "用户ID"},
                    "action": {
                        "type": "string",
                        "enum": ["plan", "next_step", "progress", "time_machine"],
                        "description": "操作类型：规划路径/推荐下一步/查看进度/时光机回放",
                        "default": "plan"
                    },
                    "target_knowledge": {
                        "type": "string",
                        "description": "目标知识点（规划路径时需要）",
                        "default": ""
                    }
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "multimodal_agent",
            "description": (
                "多模态资源Agent：生成算法动画、思维导图、代码执行可视化。"
                "适用场景：学生想看算法可视化、动画演示、思维导图。"
                "当学生说'演示一下'、'动画展示'、'可视化'时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "knowledge_point": {
                        "type": "string",
                        "description": "知识点名称"
                    },
                    "user_id": {"type": "string", "description": "用户ID"},
                    "resource_type": {
                        "type": "string",
                        "enum": ["animation", "mind_map", "code_visualization", "video"],
                        "description": "资源类型：算法动画/思维导图/代码执行可视化/视频",
                        "default": "animation"
                    }
                },
                "required": ["knowledge_point", "user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tutor_agent",
            "description": (
                "智能辅导Agent：Socratic式引导，不直接给答案而是通过提问引导学生思考。"
                "适用场景：学生问'为什么'类问题、需要深度理解、卡住了需要引导。"
                "当学生说'为什么XX'、'不太懂'、'能再解释一下吗'时调用。"
                "注意：简单概念问题由虚拟老师直接回答，不需要调用辅导Agent。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "knowledge_point": {
                        "type": "string",
                        "description": "知识点名称"
                    },
                    "user_id": {"type": "string", "description": "用户ID"},
                    "question": {
                        "type": "string",
                        "description": "学生的问题"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["socratic", "hint", "explain"],
                        "description": "辅导模式：Socratic引导/提示/讲解",
                        "default": "socratic"
                    }
                },
                "required": ["knowledge_point", "user_id", "question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reading_agent",
            "description": (
                "拓展阅读Agent：为知识点生成拓展阅读材料，包含现实应用、历史背景、进阶主题和推荐资源。"
                "适用场景：学生想深入了解某个知识点、需要课外拓展阅读、想看推荐书籍/论文/博客。"
                "当学生说'推荐阅读'、'拓展'、'深入了解一下'、'有什么参考资料'时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "knowledge_point": {
                        "type": "string",
                        "description": "知识点名称（如array、bst、dfs等）"
                    },
                    "user_id": {"type": "string", "description": "用户ID"}
                },
                "required": ["knowledge_point", "user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "assessment_agent",
            "description": (
                "评估Agent：生成学习效果评估报告，包含掌握度趋势、薄弱点改善、目标差距分析。"
                "适用场景：学生想了解自己的学习效果、查看评估报告、分析薄弱点改善情况。"
                "当学生说'评估'、'测评'、'效果'、'我学得怎么样'、'学习报告'时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "用户ID"}
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "video_agent",
            "description": (
                "视频生成Agent：为知识点生成教学视频，包含动画演示和语音讲解。"
                "适用场景：学生想看某个知识点的视频讲解、需要动画演示、想要更直观的理解。"
                "当学生说'生成视频'、'视频讲解'、'动画演示'、'帮我做个视频'时调用。"
                "注意：视频生成是异步任务，会立即返回task_id，需要轮询查询进度。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "knowledge_point": {
                        "type": "string",
                        "description": "知识点名称（如array、bst、dfs等）"
                    },
                    "user_id": {"type": "string", "description": "用户ID"},
                    "style": {
                        "type": "string",
                        "enum": ["rigorous", "relaxed", "guided", "whiteboard"],
                        "description": "讲解风格：严谨/轻松/引导/白板",
                        "default": "rigorous"
                    },
                    "with_tts": {
                        "type": "boolean",
                        "description": "是否生成TTS语音旁白",
                        "default": True
                    }
                },
                "required": ["knowledge_point", "user_id"]
            }
        }
    },
]


# ===== LangGraph State =====

class TeacherState(BaseModel):
    """虚拟老师状态 - LangGraph状态图的核心数据结构"""
    # 对话消息（LangGraph自动管理）
    messages: list = Field(default_factory=list)

    # 用户信息
    user_id: str = ""

    # 画像快照（每次调度前更新）
    profile_summary: str = ""  # 画像摘要（用于LLM上下文）

    # 调度状态
    agent_calls: list = Field(default_factory=list)  # 本轮已调用的Agent列表
    agent_results: dict = Field(default_factory=dict)  # Agent调用结果 {agent_name: result}
    call_count: int = 0  # 本轮Agent调用次数（最多5次）

    # 可视化状态
    status_bar: list = Field(default_factory=list)  # 状态条信息 [{agent, status, message}]
    dag_nodes: list = Field(default_factory=list)  # DAG流程图节点
    dag_edges: list = Field(default_factory=list)  # DAG流程图边

    # 上下文管理
    conversation_summary: str = ""  # 早期对话摘要
    conversation_history: list = Field(default_factory=list)  # 完整对话历史
    is_new_user: bool = True  # 是否新用户

    class Config:
        arbitrary_types_allowed = True


# ===== 虚拟老师系统Prompt =====

TEACHER_SYSTEM_PROMPT = """你是"小智"，一位专业的学习辅导老师。

## 绝对约束（必须遵守）
1. 你需要根据学生当前学习的知识点所属学科进行辅导，覆盖数据结构与算法、编程语言、英语语法、数学、物理等各类学科
2. 你的课程范围：由学生当前学习的知识点决定，覆盖该知识点所属学科的相关内容
3. 当学生问与当前学习知识点完全无关的话题时，礼貌拒绝并引导回学习话题
4. 你必须优先使用工具（function calling）来服务学生

## 工具调用规则（必须遵守）
- 学生要学习/理解某知识点 → 必须调用 document_agent
- 学生要练习/做题 → 必须调用 question_agent
- 学生要写代码/实操 → 必须调用 code_agent
- 学生要规划学习 → 必须调用 path_agent
- 学生要看动画/可视化 → 必须调用 multimodal_agent
- 学生问"为什么"/深度问题 → 调用 tutor_agent
- 学生说不懂/薄弱 → 调用 document_agent + question_agent
- 简单问候/闲聊 → 直接回复，不调工具

## 当前学生画像
{profile_summary}

## 对话历史摘要
{conversation_summary}

## 人格设定
{persona}

## 回复格式
- 用中文回复，使用Markdown格式
- 知识讲解要详细清晰，可以用标题、列表、代码块、表格等
- 如果调用了工具，先简要说明正在做什么（如"我来为你生成学习资料和练习题"），然后展示工具返回的内容
- 代码示例用Python（除非学生要求其他语言）
- 讲解时结合具体例子，避免纯理论堆砌
"""


def _build_persona(profile_summary: str, is_new_user: bool) -> str:
    """根据画像构建人格设定"""
    if is_new_user:
        return "耐心学长型：语气温和鼓励，多用类比和图示，避免专业术语堆砌。"
    return "自适应型：根据学生水平调整语气，进阶者用专业讨论，初学者用鼓励引导。"


def _build_profile_summary(profile: StudentProfile) -> str:
    """从画像生成摘要文本（用于LLM上下文）"""
    parts = [
        f"专业：{profile.major.value}",
        f"阶段：{profile.stage.value}",
        f"认知风格：{profile.cognitive_style.value}",
        f"难度偏好：{profile.difficulty_level.value}",
        f"学习节奏：{profile.learning_pace.value}",
    ]
    if profile.weak_points:
        weak_names = [wp.knowledge_point for wp in profile.weak_points]
        parts.append(f"薄弱环节：{', '.join(weak_names)}")
    if profile.learning_goals:
        parts.append(f"学习目标：{', '.join(profile.learning_goals)}")
    return "\n".join(parts)


# ===== LangGraph节点函数 =====

def route_intent(state: dict) -> dict:
    """意图路由节点：LLM分析学生意图，决定调用哪些Agent"""
    messages = state.get("messages", [])
    user_id = state.get("user_id", "")
    profile_summary = state.get("profile_summary", "")
    conversation_summary = state.get("conversation_summary", "")
    conversation_history = state.get("conversation_history", [])
    is_new_user = state.get("is_new_user", True)
    call_count = state.get("call_count", 0)

    # 构建系统Prompt
    persona = _build_persona(profile_summary, is_new_user)
    system_prompt = TEACHER_SYSTEM_PROMPT.format(
        profile_summary=profile_summary,
        conversation_summary=conversation_summary or "（新对话）",
        persona=persona,
    )

    # 构建消息列表：系统Prompt + 历史对话 + 当前消息
    llm_messages = [{"role": "system", "content": system_prompt}]

    # 先加入数据库中的对话历史（如果有）
    for hist_msg in conversation_history[-10:]:
        llm_messages.append(hist_msg)

    # 再加入当前对话中的消息
    for msg in messages[-6:]:
        if isinstance(msg, HumanMessage):
            llm_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            llm_messages.append({"role": "assistant", "content": msg.content})

    # 调用LLM with Function Calling
    try:
        result = llm_client.chat_with_tools(
            messages=llm_messages,
            tools=AGENT_TOOLS,
            temperature=0.3,
        )

        # 调试日志
        logger.info(f"LLM result: content={result['content'][:100] if result['content'] else 'None'}, tool_calls={len(result['tool_calls']) if result['tool_calls'] else 0}")
        if result["tool_calls"]:
            for tc in result["tool_calls"]:
                logger.info(f"  Tool call: {tc.function.name}({tc.function.arguments[:100]})")

        # 记录LLM回复
        if result["content"]:
            state["messages"].append(AIMessage(content=result["content"]))

        # 处理Function Calling结果
        if result["tool_calls"] and check_call_limit(call_count):
            raw_calls = []
            for tool_call in result["tool_calls"]:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)

                # 参数校验
                func_args = validate_agent_args(func_name, func_args)

                raw_calls.append({
                    "agent": func_name,
                    "args": func_args,
                    "call_id": tool_call.id,
                })

            # 规则兜底：检测到知识点→补充文档+题库Agent
            enhanced_calls = apply_fallback_rules(raw_calls)

            for call_info in enhanced_calls:
                if not check_call_limit(state.get("call_count", 0)):
                    break

                state["agent_calls"].append(call_info)
                state["call_count"] = state.get("call_count", 0) + 1

                # 更新状态条
                state["status_bar"].append({
                    "agent": call_info["agent"],
                    "status": "pending",
                    "message": f"正在调用{call_info['agent']}...",
                })

    except Exception as e:
        logger.error(f"意图路由失败: {e}")
        # 降级：纯对话模式
        state["messages"].append(AIMessage(
            content="抱歉，我遇到了一些技术问题。让我直接回答你的问题。"
        ))

    return state


def execute_agents(state: dict) -> dict:
    """执行Agent调用节点：按执行计划分层调用（同层并行）

    执行计划由dispatcher生成，每层内的Agent可并行执行。
    使用asyncio.gather实现同层并行，层间串行。
    """
    import asyncio

    agent_calls = state.get("agent_calls", [])
    agent_results = state.get("agent_results", {})

    # 生成执行计划
    execution_plan = get_execution_plan(agent_calls)

    for layer_idx, layer in enumerate(execution_plan):
        logger.info(f"执行第{layer_idx + 1}层，共{len(layer)}个Agent")

        # 更新状态条：标记为running
        for call_info in layer:
            agent_name = call_info["agent"]
            for item in state.get("status_bar", []):
                if item.get("agent") == agent_name and item.get("status") == "pending":
                    item["status"] = "running"
                    item["message"] = f"{agent_name} 执行中..."

        # 同层Agent并行执行
        if len(layer) == 1:
            # 单个Agent，直接执行
            call_info = layer[0]
            result = _execute_single_agent(call_info)
            agent_name = call_info["agent"]
            agent_results[agent_name] = result
            _update_status_bar(state, agent_name, "completed" if "error" not in result else "failed")
        else:
            # 多个Agent，并行执行
            async def _run_parallel():
                tasks = []
                for call_info in layer:
                    tasks.append(_execute_agent_async(call_info))
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return list(zip(layer, results))

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果已在异步上下文中，用run_in_executor
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, _run_parallel())
                        parallel_results = future.result()
                else:
                    parallel_results = asyncio.run(_run_parallel())
            except RuntimeError:
                parallel_results = asyncio.run(_run_parallel())

            for call_info, result in parallel_results:
                agent_name = call_info["agent"]
                if isinstance(result, Exception):
                    agent_results[agent_name] = {"error": str(result)}
                    _update_status_bar(state, agent_name, "failed")
                else:
                    agent_results[agent_name] = result
                    _update_status_bar(state, agent_name, "completed" if "error" not in result else "failed")

    state["agent_results"] = agent_results
    state["agent_calls"] = []

    return state


def _execute_single_agent(call_info: dict) -> dict:
    """执行单个Agent调用"""
    agent_name = call_info["agent"]
    args = call_info["args"]
    try:
        return _dispatch_agent(agent_name, args)
    except Exception as e:
        logger.error(f"Agent {agent_name} 执行失败: {e}")
        return {"error": str(e)}


async def _execute_agent_async(call_info: dict) -> dict:
    """异步执行单个Agent调用"""
    return _execute_single_agent(call_info)


def _update_status_bar(state: dict, agent_name: str, status: str) -> None:
    """更新状态条"""
    status_msg = f"{agent_name} 已完成" if status == "completed" else f"{agent_name} 执行失败"
    for item in state.get("status_bar", []):
        if item.get("agent") == agent_name and item.get("status") == "running":
            item["status"] = status
            item["message"] = status_msg


def integrate_response(state: dict) -> dict:
    """整合回复节点：汇总各Agent结果，生成最终回复"""
    agent_results = state.get("agent_results", {})
    messages = state.get("messages", [])

    if not agent_results:
        # 没有Agent调用结果，LLM已经直接回复了
        return state

    # 构建整合Prompt
    results_text = ""
    for agent_name, result in agent_results.items():
        results_text += f"\n### {agent_name} 结果:\n{json.dumps(result, ensure_ascii=False, indent=2)}\n"

    integration_prompt = f"""请根据以下各Agent的执行结果，整合生成一个连贯、自然的回复给学生。

要求：
1. 用中文回复
2. 整合各Agent结果，不要简单罗列
3. 根据学生画像调整语气和详细程度
4. 如果有可视化内容，提示学生查看
5. 适当推荐下一步学习内容

各Agent结果：
{results_text}
"""

    # 添加整合请求
    llm_messages = [{"role": "system", "content": integration_prompt}]
    for msg in messages[-5:]:
        if isinstance(msg, HumanMessage):
            llm_messages.append({"role": "user", "content": msg.content})

    try:
        response = llm_client.chat(
            messages=llm_messages,
            temperature=0.5,
        )
        state["messages"].append(AIMessage(content=response))
    except Exception as e:
        logger.error(f"整合回复失败: {e}")
        state["messages"].append(AIMessage(
            content="我已经为你准备好了学习资料，请查看上方内容。"
        ))

    return state


# ===== Agent分发注册表 =====
# 使用字符串名 + 惰性解析，避免模块顶层按顺序执行时函数尚未定义的 NameError

AGENT_DISPATCHERS = {
    "document_agent": "_dispatch_document_agent",
    "profile_agent": "_dispatch_profile_agent",
    "question_agent": "_dispatch_question_agent",
    "code_agent": "_dispatch_code_agent",
    "path_agent": "_dispatch_path_agent",
    "multimodal_agent": "_dispatch_multimodal_agent",
    "tutor_agent": "_dispatch_tutor_agent",
    "reading_agent": "_dispatch_reading_agent",
    "assessment_agent": "_dispatch_assessment_agent",
    "video_agent": "_dispatch_video_agent",
}


def _dispatch_agent(agent_name: str, args: dict) -> dict:
    """分发Agent调用到真实实现（使用注册表模式）"""
    from app.core.database import SessionLocal

    func_name = AGENT_DISPATCHERS.get(agent_name)
    dispatcher_func = globals().get(func_name) if func_name else None
    if dispatcher_func:
        return dispatcher_func(args)
    else:
        return {"status": "error", "message": f"未知Agent: {agent_name}"}


def _dispatch_document_agent(args: dict) -> dict:
    """文档Agent：RAG检索 + LLM个性化文档生成"""
    from app.services.knowledge_service import knowledge_service
    from app.services.profile_service import profile_service
    from app.core.database import SessionLocal

    kp = args.get("knowledge_point", "")
    user_id = args.get("user_id", "")
    style = args.get("style", "concept")

    db = SessionLocal()
    try:
        profile = profile_service.get_profile(db, user_id) if user_id else None
        result = knowledge_service.generate_document(
            knowledge_point=kp,
            user_id=user_id,
            profile=profile,
            style=style,
        )
        return result
    except Exception as e:
        logger.error(f"文档Agent执行失败: {e}")
        return {"status": "error", "message": str(e), "content": ""}
    finally:
        db.close()


def _dispatch_profile_agent(args: dict) -> dict:
    """画像Agent：查询/更新画像"""
    from app.services.profile_service import profile_service
    from app.core.database import SessionLocal

    action = args.get("action", "get_profile")
    user_id = args.get("user_id", "")

    db = SessionLocal()
    try:
        if action == "get_profile":
            profile = profile_service.get_profile(db, user_id)
            if profile:
                return {"status": "ok", "profile": profile.model_dump()}
            return {"status": "ok", "profile": None, "message": "画像不存在"}
        elif action == "get_radar":
            from app.schemas.knowledge_graph import get_categories
            profile = profile_service.get_profile(db, user_id)
            if profile:
                categories = get_categories()
                radar = []
                for cat, nids in categories.items():
                    masteries = [profile.get_knowledge_mastery(nid) for nid in nids]
                    avg = sum(masteries) / len(masteries) if masteries else 0
                    radar.append({"category": cat, "mastery": round(avg, 2)})
                return {"status": "ok", "radar": radar}
            return {"status": "ok", "radar": []}
        else:
            return {"status": "ok", "message": f"画像操作{action}完成"}
    except Exception as e:
        logger.error(f"画像Agent执行失败: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def _dispatch_question_agent(args: dict) -> dict:
    """题库Agent：画像驱动出题（经典题优先 + LLM动态生成）

    Args:
        args: {knowledge_point, user_id, count?, level?}
    """
    from app.services.question_service import question_service
    from app.services.profile_service import profile_service
    from app.core.database import SessionLocal

    kp = args.get("knowledge_point", "")
    user_id = args.get("user_id", "")
    count = min(args.get("count", 3), 10)
    level = args.get("level")

    db = SessionLocal()
    try:
        profile = profile_service.get_profile(db, user_id) if user_id else None

        if level is not None:
            questions = question_service.get_questions_by_level(
                knowledge_point=kp, level=level, count=count,
            )
            return {
                "status": "ok",
                "knowledge_point": kp,
                "questions": questions,
                "source": "by_level",
            }

        # 画像驱动出题
        result = question_service.get_next_question(
            user_id=user_id,
            knowledge_point=kp,
            profile=profile,
        )
        return {
            "status": "ok",
            "knowledge_point": kp,
            "question": result["question"],
            "level": result["level"],
            "source": result["source"],
        }
    except Exception as e:
        logger.error(f"题库Agent失败: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def _dispatch_code_agent(args: dict) -> dict:
    """代码实操Agent：预制代码库 + 沙箱执行 + AI解析 + 闭环

    对照 ai_architecture_plan.md Agent 6：
    - action=template: 获取代码模板
    - action=execute: 沙箱执行代码
    - action=analyze: AI解析面板
    - action=fill_blank: 代码填空挑战

    Args:
        args: {knowledge_point, user_id, action?, template_id?, code?}
    """
    from app.knowledge.code_templates import CODE_TEMPLATES
    from app.services.code_service import code_sandbox

    kp = args.get("knowledge_point", "")
    action = args.get("action", "template")
    template_id = args.get("template_id", "")
    code = args.get("code", "")

    try:
        if action == "template":
            # 获取代码模板列表或详情
            if template_id:
                # 获取详情
                for k, templates in CODE_TEMPLATES.items():
                    for t in templates:
                        if t["id"] == template_id:
                            return {
                                "status": "ok",
                                "template": {
                                    "id": t["id"],
                                    "title": t["title"],
                                    "description": t["description"],
                                    "code": t["code"],
                                    "test_cases": t.get("test_cases", []),
                                    "difficulty": t["difficulty"],
                                    "blanks": t.get("blanks", []),
                                    "knowledge_point": k,
                                },
                            }
                return {"status": "error", "message": f"模板 {template_id} 不存在"}
            else:
                # 列出知识点下的模板
                templates = CODE_TEMPLATES.get(kp, [])
                return {
                    "status": "ok",
                    "knowledge_point": kp,
                    "templates": [
                        {
                            "id": t["id"],
                            "title": t["title"],
                            "description": t["description"],
                            "difficulty": t["difficulty"],
                            "has_blanks": bool(t.get("blanks")),
                        }
                        for t in templates
                    ],
                }

        elif action == "execute":
            # 沙箱执行代码
            if not code:
                return {"status": "error", "message": "请提供代码"}

            # 获取测试用例
            test_cases = []
            if template_id:
                for k, templates in CODE_TEMPLATES.items():
                    for t in templates:
                        if t["id"] == template_id:
                            test_cases = t.get("test_cases", [])
                            break
            elif kp:
                kp_templates = CODE_TEMPLATES.get(kp, [])
                if kp_templates:
                    test_cases = kp_templates[0].get("test_cases", [])

            result = code_sandbox.execute(code=code, test_cases=test_cases)

            return {
                "status": "ok",
                "success": result.success,
                "output": result.output[:2000],
                "error": result.error[:1000] if result.error else "",
                "test_results": result.test_results,
            }

        elif action == "fill_blank":
            # 代码填空挑战
            if template_id:
                for k, templates in CODE_TEMPLATES.items():
                    for t in templates:
                        if t["id"] == template_id:
                            blanks = t.get("blanks", [])
                            code_lines = t["code"].split("\n")
                            for blank in blanks:
                                line_idx = blank["line"] - 1
                                if 0 <= line_idx < len(code_lines):
                                    hint = blank.get("hint", "填写代码")
                                    indent = len(code_lines[line_idx]) - len(code_lines[line_idx].lstrip())
                                    code_lines[line_idx] = " " * indent + f"# ___ {hint} ___"
                            return {
                                "status": "ok",
                                "template_id": template_id,
                                "fill_blank_code": "\n".join(code_lines),
                                "blanks": blanks,
                                "test_cases": t.get("test_cases", []),
                            }
            return {"status": "error", "message": "请指定template_id"}

        else:
            return {"status": "error", "message": f"未知action: {action}"}

    except Exception as e:
        logger.error(f"代码实操Agent失败: {e}")
        return {"status": "error", "message": str(e)}


def _dispatch_path_agent(args: dict) -> dict:
    """路径规划Agent：个性化路径+多路径对比+模拟未来+伙伴匹配

    对照 ai_architecture_plan.md Agent 7：
    - action=plan: 生成个性化学习路径
    - action=next_step: 推荐下一步学习内容
    - action=progress: 查看学习进度
    - action=time_machine: 路径模拟未来
    """
    from app.services.path_service import path_service, PathStrategy
    from app.services.profile_service import profile_service
    from app.core.database import SessionLocal

    user_id = args.get("user_id", "")
    action = args.get("action", "plan")
    target_knowledge = args.get("target_knowledge", "")

    db = SessionLocal()
    try:
        profile = profile_service.get_profile(db, user_id) if user_id else None
        if not profile:
            return {"status": "error", "message": "画像不存在，请先完成冷启动"}

        if action == "plan":
            strategy = path_service.recommend_strategy(profile)
            path = path_service.generate_path(profile, strategy)
            # 同时生成多路径对比
            multi = path_service.generate_multi_path(profile)
            simulations = path_service.simulate_future(profile, path)
            return {
                "status": "ok",
                "strategy": strategy.value,
                "path_summary": {
                    "total": path.total_nodes,
                    "mastered": path.mastered_count,
                    "todo": path.todo_count,
                    "weak": path.weak_count,
                    "completion_rate": path.completion_rate,
                    "estimated_hours": path.estimated_total_hours,
                },
                "next_steps": [n.model_dump() for n in path.nodes[:5] if n.status.value != "mastered"],
                "multi_path_summary": {
                    key: {"strategy": key, "completion_rate": p.completion_rate, "estimated_hours": p.estimated_total_hours}
                    for key, p in multi.items()
                },
                "simulation_1month": simulations[1].model_dump() if len(simulations) > 1 else None,
            }

        elif action == "next_step":
            next_node = path_service.recommend_next_step(profile)
            if not next_node:
                return {"status": "ok", "message": "所有知识点已掌握！", "next": None}
            return {
                "status": "ok",
                "next": next_node.model_dump(),
            }

        elif action == "progress":
            progress = path_service.get_progress(profile)
            return {"status": "ok", "progress": progress}

        elif action == "time_machine":
            strategy = path_service.recommend_strategy(profile)
            path = path_service.generate_path(profile, strategy)
            simulations = path_service.simulate_future(profile, path)
            return {
                "status": "ok",
                "simulations": [s.model_dump() for s in simulations],
            }

        else:
            return {"status": "error", "message": f"未知action: {action}"}

    except Exception as e:
        logger.error(f"路径规划Agent失败: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def _dispatch_multimodal_agent(args: dict) -> dict:
    """多模态资源Agent：可视化配置+思维导图+时光机+算法对比

    对照 ai_architecture_plan.md Agent 5：
    - resource_type=animation: 算法动画（前端实时可视化配置）
    - resource_type=mind_map: 思维导图
    - resource_type=code_visualization: 代码执行可视化
    - resource_type=video: 视频推荐
    """
    from app.services.multimodal_service import multimodal_service
    from app.services.profile_service import profile_service
    from app.core.database import SessionLocal

    kp = args.get("knowledge_point", "")
    user_id = args.get("user_id", "")
    resource_type = args.get("resource_type", "animation")

    db = SessionLocal()
    try:
        profile = profile_service.get_profile(db, user_id) if user_id else None

        if resource_type == "animation":
            result = multimodal_service.get_visualization_config(kp)
            return {"status": "ok", "type": "animation", "config": result.model_dump() if result else None}

        elif resource_type == "mind_map":
            result = multimodal_service.generate_mind_map(kp)
            return {"status": "ok", "type": "mind_map", "data": {"markdown": result}}

        elif resource_type == "code_visualization":
            result = multimodal_service.get_code_visualization(
                code="# 代码可视化", language="python"
            )
            return {"status": "ok", "type": "code_visualization", "data": result.model_dump()}

        elif resource_type == "video":
            result = multimodal_service.get_video_recommendations(kp)
            return {"status": "ok", "type": "video", "recommendations": [r.model_dump() for r in result]}

        else:
            return {"status": "error", "message": f"未知resource_type: {resource_type}"}

    except Exception as e:
        logger.error(f"多模态Agent失败: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def _dispatch_tutor_agent(args: dict) -> dict:
    """智能辅导Agent：Socratic引导+渐进提示+安全阀

    对照 ai_architecture_plan.md Agent 8：
    - mode=socratic: Socratic引导
    - mode=hint: 渐进提示
    - mode=explain: 直接讲解
    """
    from app.services.tutor_service import tutor_service
    from app.services.profile_service import profile_service
    from app.core.database import SessionLocal

    kp = args.get("knowledge_point", "")
    user_id = args.get("user_id", "")
    question = args.get("question", "")
    mode = args.get("mode", "socratic")

    db = SessionLocal()
    try:
        profile = profile_service.get_profile(db, user_id) if user_id else None

        result = tutor_service.tutor(
            knowledge_point=kp,
            question=question,
            mode=mode,
            profile=profile,
        )
        return {"status": "ok", **result}

    except Exception as e:
        logger.error(f"辅导Agent失败: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def _dispatch_reading_agent(args: dict) -> dict:
    """拓展阅读Agent：LLM生成拓展阅读材料"""
    from app.services.reading_service import reading_service
    from app.services.profile_service import profile_service
    from app.core.database import SessionLocal

    kp = args.get("knowledge_point", "")
    user_id = args.get("user_id", "")

    db = SessionLocal()
    try:
        profile = profile_service.get_profile(db, user_id) if user_id else None
        result = reading_service.generate_reading(
            knowledge_point=kp,
            profile=profile,
        )
        return {"status": "ok", **result}
    except Exception as e:
        logger.error(f"拓展阅读Agent失败: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def _dispatch_assessment_agent(args: dict) -> dict:
    """评估Agent：生成学习效果评估报告"""
    from app.services.assessment_service import assessment_service
    from app.services.profile_service import profile_service
    from app.core.database import SessionLocal

    user_id = args.get("user_id", "")

    db = SessionLocal()
    try:
        profile = profile_service.get_profile(db, user_id) if user_id else None
        result = assessment_service.generate_assessment(
            user_id=user_id,
            profile=profile,
            db_session=db,
        )
        return {"status": "ok", **result}
    except Exception as e:
        logger.error(f"评估Agent失败: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def _dispatch_video_agent(args: dict) -> dict:
    """视频Agent：生成教学视频（异步任务）"""
    from app.services.video_service import video_service

    knowledge_point = args.get("knowledge_point", "")
    user_id = args.get("user_id", "")
    style = args.get("style", "rigorous")
    with_tts = args.get("with_tts", True)

    try:
        # 启动异步视频生成任务
        task_id = video_service.start_video_generation(
            knowledge_point=knowledge_point,
            style=style,
            with_tts=with_tts,
        )

        return {
            "status": "ok",
            "task_id": task_id,
            "message": f"视频生成任务已启动，任务ID: {task_id}。请使用 /api/video/task/{task_id} 查询进度。",
        }
    except Exception as e:
        logger.error(f"视频Agent失败: {e}")
        return {"status": "error", "message": str(e)}


# ===== 基于ExecutionContext的Agent分发 =====

def _dispatch_agent_with_context(agent_name: str, args: dict, ctx: "ExecutionContext") -> dict:
    """通过AGENT_REGISTRY调度Agent

    优先从注册表查找TrueAgent子类，找不到则回退到旧版调度。
    """
    import asyncio
    from app.core.true_agent import AGENT_REGISTRY

    # 1. 尝试从注册表获取TrueAgent
    agent_cls = AGENT_REGISTRY.get(agent_name)
    if agent_cls:
        agent = agent_cls(context=ctx)
        task = {
            "intent": args.get("action", ""),
            "knowledge_point": args.get("knowledge_point", ""),
            "user_id": ctx.user_id,
            "user_message": "",
            **args,
        }
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, agent.run(task))
                    result = future.result()
            else:
                result = asyncio.run(agent.run(task))
            if result.success:
                return result.data
            else:
                return {"error": "; ".join(result.errors)}
        except Exception as e:
            logger.error(f"TrueAgent {agent_name} 执行失败: {e}")
            return {"status": "error", "message": str(e)}

    # 2. 回退：如果注册表中没有，使用旧版_dispatch_agent_legacy（兼容期）
    logger.warning(f"Agent '{agent_name}' not in AGENT_REGISTRY, falling back to legacy dispatch")
    return _dispatch_agent_legacy(agent_name, args, ctx)


def _dispatch_agent_legacy(agent_name: str, args: dict, ctx: "ExecutionContext") -> dict:
    """旧版Agent分发 - 使用ExecutionContext分发Agent调用 - 不自己开DB连接

    对照 AI开发指南_产品内核与架构规范.md 第5.3节：
    - Agent 不自己管理数据库连接，使用 ctx.db_session
    - Agent 之间通过 ctx 传递数据，不是通过函数返回值堆叠
    """
    try:
        if agent_name == "document_agent":
            return _dispatch_document_agent_ctx(args, ctx)
        elif agent_name == "profile_agent":
            return _dispatch_profile_agent_ctx(args, ctx)
        elif agent_name == "question_agent":
            return _dispatch_question_agent_ctx(args, ctx)
        elif agent_name == "code_agent":
            return _dispatch_code_agent_ctx(args, ctx)
        elif agent_name == "path_agent":
            return _dispatch_path_agent_ctx(args, ctx)
        elif agent_name == "multimodal_agent":
            return _dispatch_multimodal_agent_ctx(args, ctx)
        elif agent_name == "tutor_agent":
            return _dispatch_tutor_agent_ctx(args, ctx)
        elif agent_name == "reading_agent":
            return _dispatch_reading_agent_ctx(args, ctx)
        elif agent_name == "assessment_agent":
            return _dispatch_assessment_agent_ctx(args, ctx)
        else:
            return {"status": "error", "message": f"未知Agent: {agent_name}"}
    except Exception as e:
        logger.error(f"Agent {agent_name} 执行失败: {e}")
        return {"status": "error", "message": str(e)}


def _dispatch_document_agent_ctx(args: dict, ctx: "ExecutionContext") -> dict:
    """文档Agent（使用ExecutionContext）"""
    from app.services.knowledge_service import knowledge_service

    kp = args.get("knowledge_point", "")
    style = args.get("style", "concept")

    # 使用上下文中的画像，不重新查询
    profile = ctx.profile

    result = knowledge_service.generate_document(
        knowledge_point=kp,
        user_id=ctx.user_id,
        profile=profile,
        style=style,
    )
    return result


def _dispatch_profile_agent_ctx(args: dict, ctx: "ExecutionContext") -> dict:
    """画像Agent（使用ExecutionContext）"""
    from app.services.profile_service import profile_service

    action = args.get("action", "get_profile")
    user_id = args.get("user_id", ctx.user_id)

    # 使用上下文中的db_session，不自己开连接
    db = ctx.db_session

    if action == "get_profile":
        profile = ctx.profile or profile_service.get_profile(db, user_id)
        if profile:
            # 更新上下文中的画像
            ctx.profile = profile
            return {"status": "ok", "profile": profile.model_dump()}
        return {"status": "ok", "profile": None, "message": "画像不存在"}
    elif action == "get_radar":
        from app.schemas.knowledge_graph import get_categories
        profile = ctx.profile or profile_service.get_profile(db, user_id)
        if profile:
            categories = get_categories()
            radar = []
            for cat, nids in categories.items():
                masteries = [profile.get_knowledge_mastery(nid) for nid in nids]
                avg = sum(masteries) / len(masteries) if masteries else 0
                radar.append({"category": cat, "mastery": round(avg, 2)})
            return {"status": "ok", "radar": radar}
        return {"status": "ok", "radar": []}
    else:
        return {"status": "ok", "message": f"画像操作{action}完成"}


def _dispatch_question_agent_ctx(args: dict, ctx: "ExecutionContext") -> dict:
    """题库Agent（使用ExecutionContext）"""
    from app.services.question_service import question_service

    kp = args.get("knowledge_point", "")
    user_id = args.get("user_id", ctx.user_id)
    count = min(args.get("count", 3), 10)
    level = args.get("level")

    # 使用上下文中的db_session和画像
    db = ctx.db_session
    profile = ctx.profile

    if level is not None:
        questions = question_service.get_questions_by_level(
            knowledge_point=kp, level=level, count=count, db=db,
        )
        return {
            "status": "ok",
            "knowledge_point": kp,
            "questions": questions,
            "source": "by_level",
        }

    # 画像驱动出题
    result = question_service.get_next_question(
        user_id=user_id,
        knowledge_point=kp,
        db=db,
        profile=profile,
    )
    return {
        "status": "ok",
        "knowledge_point": kp,
        "question": result["question"],
        "level": result["level"],
        "source": result["source"],
    }


def _dispatch_code_agent_ctx(args: dict, ctx: "ExecutionContext") -> dict:
    """代码实操Agent（使用ExecutionContext）

    代码Agent不依赖DB，直接复用原有逻辑。
    """
    # 代码Agent不使用DB，直接调用原有_dispatch_code_agent
    return _dispatch_code_agent(args)


def _dispatch_path_agent_ctx(args: dict, ctx: "ExecutionContext") -> dict:
    """路径规划Agent（使用ExecutionContext）"""
    from app.services.path_service import path_service, PathStrategy

    user_id = args.get("user_id", ctx.user_id)
    action = args.get("action", "plan")
    target_knowledge = args.get("target_knowledge", "")

    # 使用上下文中的画像和db_session
    profile = ctx.profile
    if not profile:
        return {"status": "error", "message": "画像不存在，请先完成冷启动"}

    # 可以访问前序Agent的输出
    profile_output = ctx.get_agent_output("profile_agent")
    # 如果profile_agent刚更新了画像，使用最新数据

    if action == "plan":
        strategy = path_service.recommend_strategy(profile)
        path = path_service.generate_path(profile, strategy)
        # 同时生成多路径对比
        multi = path_service.generate_multi_path(profile)
        simulations = path_service.simulate_future(profile, path)
        # 保存路径到上下文
        ctx.current_path = path
        return {
            "status": "ok",
            "strategy": strategy.value,
            "path_summary": {
                "total": path.total_nodes,
                "mastered": path.mastered_count,
                "todo": path.todo_count,
                "weak": path.weak_count,
                "completion_rate": path.completion_rate,
                "estimated_hours": path.estimated_total_hours,
            },
            "next_steps": [n.model_dump() for n in path.nodes[:5] if n.status.value != "mastered"],
            "multi_path_summary": {
                key: {"strategy": key, "completion_rate": p.completion_rate, "estimated_hours": p.estimated_total_hours}
                for key, p in multi.items()
            },
            "simulation_1month": simulations[1].model_dump() if len(simulations) > 1 else None,
        }

    elif action == "next_step":
        next_node = path_service.recommend_next_step(profile)
        if not next_node:
            return {"status": "ok", "message": "所有知识点已掌握！", "next": None}
        return {
            "status": "ok",
            "next": next_node.model_dump(),
        }

    elif action == "progress":
        progress = path_service.get_progress(profile)
        return {"status": "ok", "progress": progress}

    elif action == "time_machine":
        strategy = path_service.recommend_strategy(profile)
        path = path_service.generate_path(profile, strategy)
        simulations = path_service.simulate_future(profile, path)
        return {
            "status": "ok",
            "simulations": [s.model_dump() for s in simulations],
        }

    else:
        return {"status": "error", "message": f"未知action: {action}"}


def _dispatch_multimodal_agent_ctx(args: dict, ctx: "ExecutionContext") -> dict:
    """多模态资源Agent（使用ExecutionContext）"""
    from app.services.multimodal_service import multimodal_service

    kp = args.get("knowledge_point", "")
    resource_type = args.get("resource_type", "animation")

    # 多模态Agent不依赖DB，直接调用服务
    if resource_type == "animation":
        result = multimodal_service.get_visualization_config(kp)
        return {"status": "ok", "type": "animation", "config": result.model_dump() if result else None}

    elif resource_type == "mind_map":
        result = multimodal_service.generate_mind_map(kp)
        return {"status": "ok", "type": "mind_map", "data": {"markdown": result}}

    elif resource_type == "code_visualization":
        result = multimodal_service.get_code_visualization(
            code="# 代码可视化", language="python"
        )
        return {"status": "ok", "type": "code_visualization", "data": result.model_dump()}

    elif resource_type == "video":
        result = multimodal_service.get_video_recommendations(kp)
        return {"status": "ok", "type": "video", "recommendations": [r.model_dump() for r in result]}

    else:
        return {"status": "error", "message": f"未知resource_type: {resource_type}"}


def _dispatch_tutor_agent_ctx(args: dict, ctx: "ExecutionContext") -> dict:
    """智能辅导Agent（使用ExecutionContext）"""
    from app.services.tutor_service import tutor_service

    kp = args.get("knowledge_point", "")
    question = args.get("question", "")
    mode = args.get("mode", "socratic")

    # 使用上下文中的画像
    profile = ctx.profile

    result = tutor_service.tutor(
        knowledge_point=kp,
        question=question,
        mode=mode,
        profile=profile,
    )
    return {"status": "ok", **result}


def _dispatch_reading_agent_ctx(args: dict, ctx: "ExecutionContext") -> dict:
    """拓展阅读Agent（使用ExecutionContext）"""
    from app.services.reading_service import reading_service

    kp = args.get("knowledge_point", "")

    # 使用上下文中的画像
    profile = ctx.profile

    result = reading_service.generate_reading(
        knowledge_point=kp,
        profile=profile,
    )
    return {"status": "ok", **result}


def _dispatch_assessment_agent_ctx(args: dict, ctx: "ExecutionContext") -> dict:
    """评估Agent（使用ExecutionContext）"""
    from app.services.assessment_service import assessment_service

    # 使用上下文中的画像和db_session
    profile = ctx.profile

    result = assessment_service.generate_assessment(
        user_id=ctx.user_id,
        profile=profile,
        db_session=ctx.db_session,
    )
    return {"status": "ok", **result}


# ===== 构建LangGraph =====

def build_teacher_graph() -> StateGraph:
    """构建虚拟老师LangGraph状态图"""
    graph = StateGraph(dict)

    # 添加节点
    graph.add_node("route_intent", route_intent)
    graph.add_node("execute_agents", execute_agents)
    graph.add_node("integrate_response", integrate_response)

    # 添加边
    graph.set_entry_point("route_intent")
    graph.add_edge("route_intent", "execute_agents")
    graph.add_edge("execute_agents", "integrate_response")
    graph.add_conditional_edges(
        "integrate_response",
        lambda state: END if not state.get("agent_calls") else "route_intent",
        {END: END, "route_intent": "route_intent"}
    )

    return graph.compile()


# ===== 虚拟老师服务 =====

class TeacherService:
    """虚拟老师服务 - 对外接口"""

    def __init__(self):
        self._graph = None

    @property
    def graph(self):
        """懒加载编译后的LangGraph"""
        if self._graph is None:
            self._graph = build_teacher_graph()
        return self._graph

    def chat(
        self,
        user_id: str,
        message: str,
        profile: Optional[StudentProfile] = None,
        conversation_summary: str = "",
        conversation_history: Optional[list[dict]] = None,
    ) -> dict:
        """处理学生消息

        Args:
            user_id: 用户ID
            message: 学生消息
            profile: 学生画像（可选，用于上下文感知）
            conversation_summary: 对话历史摘要
            conversation_history: 完整对话历史（用于上下文压缩）

        Returns:
            {
                "reply": str,           # AI回复
                "agent_calls": list,    # 调用的Agent列表
                "status_bar": list,     # 状态条信息
                "dag": dict,            # DAG流程图
                "summary": str,         # 更新后的对话摘要
            }
        """
        # 上下文压缩
        compressed_summary = conversation_summary
        if conversation_history:
            new_summary, _ = context_manager.compress_conversation(conversation_history)
            if new_summary:
                compressed_summary = new_summary

        # 构建初始状态
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "profile_summary": _build_profile_summary(profile) if profile else "（新用户，画像未建立）",
            "agent_calls": [],
            "agent_results": {},
            "call_count": 0,
            "status_bar": [],
            "dag_nodes": [],
            "dag_edges": [],
            "conversation_summary": compressed_summary,
            "conversation_history": conversation_history or [],
            "is_new_user": profile.is_new_user() if profile else True,
        }

        # 执行状态图
        try:
            final_state = self.graph.invoke(initial_state)
        except Exception as e:
            logger.error(f"LangGraph执行失败: {e}")
            return {
                "reply": "抱歉，我遇到了一些问题，请稍后再试。",
                "agent_calls": [],
                "status_bar": [],
                "dag": {"nodes": [], "edges": []},
            }

        # 提取最终AI回复
        reply = ""
        for msg in reversed(final_state.get("messages", [])):
            if isinstance(msg, AIMessage):
                reply = msg.content
                break

        return {
            "reply": reply,
            "agent_calls": [c["agent"] for c in final_state.get("status_bar", [])],
            "status_bar": final_state.get("status_bar", []),
            "dag": {
                "nodes": final_state.get("dag_nodes", []),
                "edges": final_state.get("dag_edges", []),
            },
            "summary": final_state.get("conversation_summary", ""),
        }


# 全局单例
teacher_service = TeacherService()
