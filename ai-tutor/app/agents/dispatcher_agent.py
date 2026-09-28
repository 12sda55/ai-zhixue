"""
Dispatcher Agent - 智能调度虚拟教师

接收用户自然语言需求 → 分析意图 → 调度资源生成
"""
import json
import logging
import re
import asyncio
from typing import AsyncGenerator, Dict, List, Optional, Any

from app.core.true_agent import TrueAgent, AgentPlan, AgentResult, AgentReflection, register_agent

logger = logging.getLogger(__name__)


@register_agent("dispatcher_agent")
class DispatcherAgent(TrueAgent):
    """
    意图分析 & 资源调度 Agent

    解析用户输入，决定需要生成哪些资源：
    - video: 教学视频（Manim+语音+字幕）
    - quiz: 配套习题
    - document: 学习文档/笔记
    - path: 学习路径规划
    """

    def __init__(self):
        super().__init__()

    async def think(self, task: Dict) -> AgentPlan:
        """分析用户需求，规划资源调度"""
        query = task.get("query", "")

        # 关键词快速路由（不依赖 LLM，毫秒级响应）
        knowledge_point = self._extract_knowledge_point(query)
        scope = self._determine_scope(query)
        resources = self._determine_resources(query, scope)

        plan = AgentPlan(
            tasks=[
                {"type": "analyze_intent", "query": query},
                {"type": "schedule_resources", "resources": resources, "knowledge_point": knowledge_point, "scope": scope},
            ],
            focus_areas=[knowledge_point] if knowledge_point else [],
            parameters={
                "query": query,
                "knowledge_point": knowledge_point,
                "scope": scope,
                "resources": resources,
            }
        )
        return plan

    async def execute(self, plan: AgentPlan) -> AgentResult:
        """调度资源生成（异步返回结果结构）"""
        params = plan.parameters
        resources = params.get("resources", [])
        knowledge_point = params.get("knowledge_point", "")
        scope = params.get("scope", "single")

        resource_items = []

        for res in resources:
            item = {
                "id": f"{res}_{knowledge_point}",
                "type": res,
                "title": self._generate_title(res, knowledge_point),
                "description": self._generate_description(res, knowledge_point, scope),
                "status": "queued",
            }
            resource_items.append(item)

        return AgentResult(
            success=True,
            data={
                "knowledge_point": knowledge_point,
                "scope": scope,
                "resources": resource_items,
                "message": self._generate_response_message(knowledge_point, scope, resource_items),
            },
            resources=resource_items,
        )

    async def reflect(self, result: AgentResult) -> AgentReflection:
        return AgentReflection(quality_score=0.9, issues=[], should_retry=False)

    # ── 意图分析 ──

    def _extract_knowledge_point(self, query: str) -> str:
        """从用户输入提取知识点"""
        from app.agents.teacher.dispatcher import normalize_knowledge_point
        kp = normalize_knowledge_point(query)
        if kp:
            return kp

        # 兜底：直接用 query 作为知识点
        return query.strip()

    def _determine_scope(self, query: str) -> str:
        """判断学习范围：单知识点 / 多知识点 / 完整课程"""
        multi_keywords = ["速通", "系统学习", "全面", "三周", "两周", "一周", "期末复习", "从头", "体系", "课程", "入门到"]
        for kw in multi_keywords:
            if kw in query:
                return "course"
        return "single"

    def _determine_resources(self, query: str, scope: str) -> List[str]:
        """决策需要生成哪些资源类型"""
        resources = ["video"]

        # 速通/课程 → 自动加路径规划
        if scope == "course":
            resources.append("path")

        # 包含练习/题目关键词 → 加习题
        exercise_kw = ["题目", "习题", "练习", "刷题", "考试", "测验", "考题"]
        if any(kw in query for kw in exercise_kw):
            resources.append("quiz")

        # 包含笔记/文档关键词 → 加文档
        doc_kw = ["笔记", "文档", "总结", "梳理", "整理", "复习资料"]
        if any(kw in query for kw in doc_kw):
            resources.append("document")

        return resources

    def _generate_title(self, res_type: str, kp: str) -> str:
        titles = {
            "video": f"【视频】{kp} 精讲",
            "quiz": f"【习题】{kp} 配套练习",
            "document": f"【文档】{kp} 学习笔记",
            "path": f"【路径】{kp} 学习路线",
        }
        return titles.get(res_type, kp)

    def _generate_description(self, res_type: str, kp: str, scope: str) -> str:
        descs = {
            "video": f"{kp} 的核心概念与动画演示",
            "quiz": f"检验 {kp} 掌握程度的配套习题",
            "document": f"{kp} 的完整知识点总结",
            "path": f"{'从零开始掌握' if scope == 'course' else '快速入门'}{kp}",
        }
        return descs.get(res_type, "")

    def _generate_response_message(self, kp: str, scope: str, resources: List[Dict]) -> str:
        type_names = {"video": "教学视频", "quiz": "配套习题", "document": "学习文档", "path": "学习路径"}
        resource_names = [type_names.get(r["type"], r["type"]) for r in resources]

        if scope == "course":
            intro = f"好的！我来帮你规划「{kp}」的系统学习。\n\n"
        else:
            intro = f"了解！我来为你讲解「{kp}」。\n\n"

        items = "\n".join([f"{i+1}. {'📹' if r['type']=='video' else '📝' if r['type']=='quiz' else '📄' if r['type']=='document' else '🗺️'} {r['title']}" for i, r in enumerate(resources)])
        return f"{intro}将生成以下内容：\n{items}\n\n正在生成中，请稍候..."
