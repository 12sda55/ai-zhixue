"""DocumentAgent — 讲解文档生成Agent

实现 TrueAgent 三阶段：
- think: 分析用户画像+薄弱点，制定讲解计划
- execute: 调用knowledge_service生成5段式文档
- reflect: 检查文档质量（5段完整+长度+薄弱点覆盖）
"""

from app.core.true_agent import TrueAgent, AgentPlan, AgentResult, AgentReflection, register_agent
from typing import Dict
import logging

logger = logging.getLogger(__name__)


@register_agent("document_agent")
class DocumentAgent(TrueAgent):
    """讲解文档生成Agent"""

    async def think(self, task: Dict) -> AgentPlan:
        """分析用户画像+薄弱点，制定讲解计划"""
        knowledge_point = task.get("knowledge_point", "")
        user_id = task.get("user_id", "")

        # 从记忆中获取画像信息
        profile = self._memory.get("profile", {})
        weak_points = self._memory.get("weak_points", [])

        # 制定讲解计划
        focus_areas = []
        parameters = {"knowledge_point": knowledge_point, "user_id": user_id}

        # 如果该知识点是薄弱点，重点关注
        if knowledge_point in weak_points:
            focus_areas.append("weak_point_emphasis")
            parameters["emphasis"] = True

        # 根据认知风格调整
        cognitive_style = profile.get("cognitive_style", "balanced") if isinstance(profile, dict) else ""
        if cognitive_style:
            focus_areas.append(f"cognitive_style_{cognitive_style}")
            parameters["cognitive_style"] = cognitive_style

        # 从task获取style参数
        style = task.get("style", "concept")
        parameters["style"] = style

        return AgentPlan(
            tasks=[{"type": "generate_document", "knowledge_point": knowledge_point}],
            focus_areas=focus_areas,
            parameters=parameters
        )

    async def execute(self, plan: AgentPlan) -> AgentResult:
        """调用knowledge_service生成5段式文档"""
        kp = plan.parameters.get("knowledge_point", "")
        user_id = plan.parameters.get("user_id", "")
        style = plan.parameters.get("style", "concept")

        if not kp:
            return AgentResult(success=False, errors=["No knowledge point specified"])

        try:
            from app.services.knowledge_service import knowledge_service

            # 获取画像
            profile = self._memory.get("profile")

            # 生成文档
            doc_result = knowledge_service.generate_document(
                knowledge_point=kp,
                user_id=user_id,
                profile=profile,
                style=style,
            )

            return AgentResult(
                success=True,
                data={
                    "knowledge_point": kp,
                    "document": doc_result,
                    "type": "document"
                },
                resources=[{
                    "type": "document",
                    "knowledge_point": kp,
                    "content": doc_result
                }],
                summary=f"已生成{kp}的讲解文档"
            )
        except Exception as e:
            logger.error(f"DocumentAgent execute failed: {e}")
            return AgentResult(success=False, errors=[str(e)])

    async def reflect(self, result: AgentResult) -> AgentReflection:
        """检查文档质量"""
        if not result.success:
            return AgentReflection(quality_score=0.0, issues=["执行失败"], should_retry=True)

        doc = result.data.get("document", {})
        issues = []
        quality_score = 1.0

        # 检查5段式完整
        required_sections = ["concept", "principle", "code_example", "common_mistakes", "applications"]
        content = doc if isinstance(doc, dict) else {}
        for section in required_sections:
            section_content = content.get(section, "")
            if not section_content or len(str(section_content)) < 50:
                issues.append(f"缺少完整的{section}段落")
                quality_score -= 0.15

        # 检查总长度
        total_length = sum(len(str(v)) for v in content.values() if isinstance(v, str))
        if total_length < 500:
            issues.append(f"文档总长度不足（{total_length}字，需要≥500字）")
            quality_score -= 0.2

        # 检查薄弱点覆盖
        weak_points = self._memory.get("weak_points", [])
        kp = result.data.get("knowledge_point", "")
        if kp in weak_points:
            # 薄弱点需要更详细的讲解
            if total_length < 800:
                issues.append("薄弱点需要更详细的讲解")
                quality_score -= 0.1

        quality_score = max(0.0, quality_score)

        return AgentReflection(
            quality_score=quality_score,
            issues=issues,
            should_retry=quality_score < 0.5
        )
