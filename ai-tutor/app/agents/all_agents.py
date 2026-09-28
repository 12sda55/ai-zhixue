"""所有Agent注册 — 导入此模块即可将全部Agent注册到AGENT_REGISTRY

每个Agent实现 TrueAgent 三阶段（think/execute/reflect），
execute 阶段调用对应的 service 方法。
"""

# 先导入DocumentAgent（示范改造，独立文件）
from app.agents.document_agent import DocumentAgent  # noqa: F401

from app.core.true_agent import TrueAgent, AgentPlan, AgentResult, AgentReflection, register_agent
from typing import Dict
import logging

logger = logging.getLogger(__name__)


# ===== ProfileAgent =====

@register_agent("profile_agent")
class ProfileAgent(TrueAgent):
    """画像构建Agent — 调用 ProfileService"""

    async def think(self, task: Dict) -> AgentPlan:
        action = task.get("action", "get_profile")
        user_id = task.get("user_id", "")
        return AgentPlan(
            tasks=[{"type": action, "user_id": user_id}],
            focus_areas=["profile"],
            parameters={"action": action, "user_id": user_id, "data": task.get("data", {})}
        )

    async def execute(self, plan: AgentPlan) -> AgentResult:
        from app.services.profile_service import profile_service
        from app.core.database import SessionLocal

        action = plan.parameters.get("action", "get_profile")
        user_id = plan.parameters.get("user_id", "")
        data = plan.parameters.get("data", {})

        db = SessionLocal()
        try:
            if action == "get_profile":
                profile = profile_service.get_profile(db, user_id)
                if profile:
                    return AgentResult(success=True, data={"profile": profile.model_dump()}, summary="获取画像成功")
                return AgentResult(success=True, data={"profile": None, "message": "画像不存在"}, summary="画像不存在")
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
                    return AgentResult(success=True, data={"radar": radar}, summary="雷达图数据获取成功")
                return AgentResult(success=True, data={"radar": []}, summary="画像不存在，雷达图为空")
            elif action == "init_profile":
                from app.schemas.profile import StudentProfile
                profile = StudentProfile(user_id=user_id, **data)
                profile_service.create_profile(db, profile)
                return AgentResult(success=True, data={"profile": profile.model_dump()}, summary="画像初始化成功")
            elif action == "update_profile":
                profile = profile_service.get_profile(db, user_id)
                if profile:
                    profile_service.update_profile(db, profile, "用户请求更新")
                    return AgentResult(success=True, data={"profile": profile.model_dump()}, summary="画像更新成功")
                return AgentResult(success=False, errors=["画像不存在"])
            else:
                return AgentResult(success=True, data={"message": f"画像操作{action}完成"}, summary=f"画像操作{action}完成")
        except Exception as e:
            logger.error(f"ProfileAgent execute failed: {e}")
            return AgentResult(success=False, errors=[str(e)])
        finally:
            db.close()

    async def reflect(self, result: AgentResult) -> AgentReflection:
        if not result.success:
            return AgentReflection(quality_score=0.0, issues=["执行失败"], should_retry=True)
        if not result.data:
            return AgentReflection(quality_score=0.3, issues=["无数据返回"], should_retry=False)
        return AgentReflection(quality_score=1.0, issues=[], should_retry=False)


# ===== QuestionAgent =====

@register_agent("question_agent")
class QuestionAgent(TrueAgent):
    """题库生成Agent — 调用 QuestionService"""

    async def think(self, task: Dict) -> AgentPlan:
        knowledge_point = task.get("knowledge_point", "")
        user_id = task.get("user_id", "")
        count = task.get("count", 3)
        level = task.get("level")
        question_type = task.get("question_type", "choice")

        focus_areas = []
        if level:
            focus_areas.append(f"level_{level}")
        if question_type:
            focus_areas.append(f"type_{question_type}")

        return AgentPlan(
            tasks=[{"type": "generate_question", "knowledge_point": knowledge_point}],
            focus_areas=focus_areas,
            parameters={
                "knowledge_point": knowledge_point,
                "user_id": user_id,
                "count": min(count, 10),
                "level": level,
                "question_type": question_type,
            }
        )

    async def execute(self, plan: AgentPlan) -> AgentResult:
        from app.services.question_service import question_service
        from app.services.profile_service import profile_service
        from app.core.database import SessionLocal

        kp = plan.parameters.get("knowledge_point", "")
        user_id = plan.parameters.get("user_id", "")
        count = plan.parameters.get("count", 3)
        level = plan.parameters.get("level")
        db = SessionLocal()
        try:
            profile = profile_service.get_profile(db, user_id) if user_id else None

            if level is not None:
                questions = question_service.get_questions_by_level(
                    knowledge_point=kp, level=level, count=count, db=db,
                )
                return AgentResult(
                    success=True,
                    data={"knowledge_point": kp, "questions": questions, "source": "by_level"},
                    summary=f"获取{kp}的Level{level}题目{len(questions)}道"
                )

            result = question_service.get_next_question(
                user_id=user_id, knowledge_point=kp, profile=profile, db=db,
            )
            return AgentResult(
                success=True,
                data={
                    "knowledge_point": kp,
                    "question": result["question"],
                    "level": result["level"],
                    "source": result["source"],
                },
                summary=f"生成{kp}的练习题"
            )
        except Exception as e:
            logger.error(f"QuestionAgent execute failed: {e}")
            return AgentResult(success=False, errors=[str(e)])
        finally:
            db.close()

    async def reflect(self, result: AgentResult) -> AgentReflection:
        if not result.success:
            return AgentReflection(quality_score=0.0, issues=["执行失败"], should_retry=True)
        if not result.data.get("question") and not result.data.get("questions"):
            return AgentReflection(quality_score=0.3, issues=["无题目返回"], should_retry=True)
        return AgentReflection(quality_score=1.0, issues=[], should_retry=False)


# ===== CodeAgent =====

@register_agent("code_agent")
class CodeAgent(TrueAgent):
    """代码实操Agent — 调用 code_service + CODE_TEMPLATES"""

    async def think(self, task: Dict) -> AgentPlan:
        knowledge_point = task.get("knowledge_point", "")
        action = task.get("action", "template")
        return AgentPlan(
            tasks=[{"type": action, "knowledge_point": knowledge_point}],
            focus_areas=["code"],
            parameters={
                "knowledge_point": knowledge_point,
                "action": action,
                "template_id": task.get("template_id", ""),
                "code": task.get("code", ""),
            }
        )

    async def execute(self, plan: AgentPlan) -> AgentResult:
        from app.knowledge.code_templates import CODE_TEMPLATES
        from app.services.code_service import code_sandbox

        kp = plan.parameters.get("knowledge_point", "")
        action = plan.parameters.get("action", "template")
        template_id = plan.parameters.get("template_id", "")
        code = plan.parameters.get("code", "")

        try:
            if action == "template":
                if template_id:
                    for k, templates in CODE_TEMPLATES.items():
                        for t in templates:
                            if t["id"] == template_id:
                                return AgentResult(success=True, data={
                                    "template": {
                                        "id": t["id"], "title": t["title"],
                                        "description": t["description"], "code": t["code"],
                                        "test_cases": t.get("test_cases", []),
                                        "difficulty": t["difficulty"],
                                        "blanks": t.get("blanks", []),
                                        "knowledge_point": k,
                                    }
                                }, summary=f"获取代码模板{template_id}")
                    return AgentResult(success=False, errors=[f"模板 {template_id} 不存在"])
                else:
                    templates = CODE_TEMPLATES.get(kp, [])
                    return AgentResult(success=True, data={
                        "knowledge_point": kp,
                        "templates": [
                            {"id": t["id"], "title": t["title"], "description": t["description"],
                             "difficulty": t["difficulty"], "has_blanks": bool(t.get("blanks"))}
                            for t in templates
                        ],
                    }, summary=f"获取{kp}的代码模板列表")

            elif action == "execute":
                if not code:
                    return AgentResult(success=False, errors=["请提供代码"])
                test_cases = []
                if template_id:
                    for k, templates in CODE_TEMPLATES.items():
                        for t in templates:
                            if t["id"] == template_id:
                                test_cases = t.get("test_cases", [])
                                break
                result = code_sandbox.execute(code=code, test_cases=test_cases)
                return AgentResult(success=True, data={
                    "success": result.success,
                    "output": result.output[:2000],
                    "error": result.error[:1000] if result.error else "",
                    "test_results": result.test_results,
                }, summary="代码执行完成")

            elif action == "fill_blank":
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
                                return AgentResult(success=True, data={
                                    "template_id": template_id,
                                    "fill_blank_code": "\n".join(code_lines),
                                    "blanks": blanks,
                                    "test_cases": t.get("test_cases", []),
                                }, summary=f"代码填空挑战{template_id}")
                return AgentResult(success=False, errors=["请指定template_id"])

            else:
                return AgentResult(success=False, errors=[f"未知action: {action}"])
        except Exception as e:
            logger.error(f"CodeAgent execute failed: {e}")
            return AgentResult(success=False, errors=[str(e)])

    async def reflect(self, result: AgentResult) -> AgentReflection:
        if not result.success:
            return AgentReflection(quality_score=0.0, issues=["执行失败"], should_retry=True)
        return AgentReflection(quality_score=1.0, issues=[], should_retry=False)


# ===== PathAgent =====

@register_agent("path_agent")
class PathAgent(TrueAgent):
    """路径规划Agent — 调用 PathService"""

    async def think(self, task: Dict) -> AgentPlan:
        user_id = task.get("user_id", "")
        action = task.get("action", "plan")
        target_knowledge = task.get("target_knowledge", "")
        return AgentPlan(
            tasks=[{"type": action, "user_id": user_id}],
            focus_areas=["path"],
            parameters={"user_id": user_id, "action": action, "target_knowledge": target_knowledge}
        )

    async def execute(self, plan: AgentPlan) -> AgentResult:
        from app.services.path_service import path_service
        from app.services.profile_service import profile_service
        from app.core.database import SessionLocal

        user_id = plan.parameters.get("user_id", "")
        action = plan.parameters.get("action", "plan")

        db = SessionLocal()
        try:
            profile = profile_service.get_profile(db, user_id) if user_id else None
            if not profile:
                return AgentResult(success=False, errors=["画像不存在，请先完成冷启动"])

            if action == "plan":
                strategy = path_service.recommend_strategy(profile)
                path = path_service.generate_path(profile, strategy)
                multi = path_service.generate_multi_path(profile)
                simulations = path_service.simulate_future(profile, path)
                return AgentResult(success=True, data={
                    "strategy": strategy.value,
                    "path_summary": {
                        "total": path.total_nodes, "mastered": path.mastered_count,
                        "todo": path.todo_count, "weak": path.weak_count,
                        "completion_rate": path.completion_rate,
                        "estimated_hours": path.estimated_total_hours,
                    },
                    "next_steps": [n.model_dump() for n in path.nodes[:5] if n.status.value != "mastered"],
                    "multi_path_summary": {
                        key: {"strategy": key, "completion_rate": p.completion_rate, "estimated_hours": p.estimated_total_hours}
                        for key, p in multi.items()
                    },
                    "simulation_1month": simulations[1].model_dump() if len(simulations) > 1 else None,
                }, summary=f"生成学习路径，策略：{strategy.value}")

            elif action == "next_step":
                next_node = path_service.recommend_next_step(profile)
                if not next_node:
                    return AgentResult(success=True, data={"message": "所有知识点已掌握！", "next": None}, summary="全部掌握")
                return AgentResult(success=True, data={"next": next_node.model_dump()}, summary="推荐下一步")

            elif action == "progress":
                progress = path_service.get_progress(profile)
                return AgentResult(success=True, data={"progress": progress}, summary="获取学习进度")

            elif action == "time_machine":
                strategy = path_service.recommend_strategy(profile)
                path = path_service.generate_path(profile, strategy)
                simulations = path_service.simulate_future(profile, path)
                return AgentResult(success=True, data={
                    "simulations": [s.model_dump() for s in simulations],
                }, summary="路径模拟完成")

            else:
                return AgentResult(success=False, errors=[f"未知action: {action}"])
        except Exception as e:
            logger.error(f"PathAgent execute failed: {e}")
            return AgentResult(success=False, errors=[str(e)])
        finally:
            db.close()

    async def reflect(self, result: AgentResult) -> AgentReflection:
        if not result.success:
            return AgentReflection(quality_score=0.0, issues=["执行失败"], should_retry=True)
        return AgentReflection(quality_score=1.0, issues=[], should_retry=False)


# ===== VideoAgent =====

@register_agent("video_agent")
class VideoAgent(TrueAgent):
    """视频生成Agent — 调用 VideoService"""

    async def think(self, task: Dict) -> AgentPlan:
        knowledge_point = task.get("knowledge_point", "")
        style = task.get("style", "rigorous")
        return AgentPlan(
            tasks=[{"type": "generate_video", "knowledge_point": knowledge_point}],
            focus_areas=["video"],
            parameters={"knowledge_point": knowledge_point, "style": style}
        )

    async def execute(self, plan: AgentPlan) -> AgentResult:
        from app.services.video_service import video_service

        kp = plan.parameters.get("knowledge_point", "")
        style = plan.parameters.get("style", "rigorous")

        try:
            # 先查缓存
            cached = video_service.get_cached_video(kp, style)
            if cached:
                return AgentResult(success=True, data={
                    "knowledge_point": kp, "video": cached, "type": "video", "cached": True,
                }, summary=f"获取{kp}的缓存视频")

            # 启动异步生成
            task_id = video_service.start_video_generation(kp, style, with_tts=True)
            return AgentResult(success=True, data={
                "knowledge_point": kp, "type": "video", "task_id": task_id, "status": "generating",
            }, summary=f"视频生成任务已提交：{task_id}")
        except Exception as e:
            logger.error(f"VideoAgent execute failed: {e}")
            return AgentResult(success=False, errors=[str(e)])

    async def reflect(self, result: AgentResult) -> AgentReflection:
        if not result.success:
            return AgentReflection(quality_score=0.0, issues=["执行失败"], should_retry=True)
        return AgentReflection(quality_score=1.0, issues=[], should_retry=False)


# ===== TutorAgent =====

@register_agent("tutor_agent")
class TutorAgent(TrueAgent):
    """智能辅导Agent — 调用 TutorService"""

    async def think(self, task: Dict) -> AgentPlan:
        knowledge_point = task.get("knowledge_point", "")
        question = task.get("question", "")
        mode = task.get("mode", "socratic")
        return AgentPlan(
            tasks=[{"type": "tutor", "knowledge_point": knowledge_point}],
            focus_areas=[mode],
            parameters={"knowledge_point": knowledge_point, "question": question, "mode": mode}
        )

    async def execute(self, plan: AgentPlan) -> AgentResult:
        from app.services.tutor_service import tutor_service

        kp = plan.parameters.get("knowledge_point", "")
        question = plan.parameters.get("question", "")
        mode = plan.parameters.get("mode", "socratic")

        # 获取画像
        profile = self._memory.get("profile")

        try:
            result = tutor_service.tutor(
                knowledge_point=kp, question=question, mode=mode, profile=profile,
            )
            return AgentResult(success=True, data=result, summary=f"辅导完成（{mode}模式）")
        except Exception as e:
            logger.error(f"TutorAgent execute failed: {e}")
            return AgentResult(success=False, errors=[str(e)])

    async def reflect(self, result: AgentResult) -> AgentReflection:
        if not result.success:
            return AgentReflection(quality_score=0.0, issues=["执行失败"], should_retry=True)
        if not result.data.get("response"):
            return AgentReflection(quality_score=0.3, issues=["辅导回复为空"], should_retry=True)
        return AgentReflection(quality_score=1.0, issues=[], should_retry=False)


# ===== ReadingAgent =====

@register_agent("reading_agent")
class ReadingAgent(TrueAgent):
    """拓展阅读Agent — 调用 ReadingService"""

    async def think(self, task: Dict) -> AgentPlan:
        knowledge_point = task.get("knowledge_point", "")
        return AgentPlan(
            tasks=[{"type": "generate_reading", "knowledge_point": knowledge_point}],
            focus_areas=["reading"],
            parameters={"knowledge_point": knowledge_point}
        )

    async def execute(self, plan: AgentPlan) -> AgentResult:
        from app.services.reading_service import reading_service

        kp = plan.parameters.get("knowledge_point", "")
        profile = self._memory.get("profile")

        try:
            result = reading_service.generate_reading(knowledge_point=kp, profile=profile)
            return AgentResult(success=True, data=result, summary=f"生成{kp}的拓展阅读")
        except Exception as e:
            logger.error(f"ReadingAgent execute failed: {e}")
            return AgentResult(success=False, errors=[str(e)])

    async def reflect(self, result: AgentResult) -> AgentReflection:
        if not result.success:
            return AgentReflection(quality_score=0.0, issues=["执行失败"], should_retry=True)
        return AgentReflection(quality_score=1.0, issues=[], should_retry=False)


# ===== AssessmentAgent =====

@register_agent("assessment_agent")
class AssessmentAgent(TrueAgent):
    """评估Agent — 调用 AssessmentService"""

    async def think(self, task: Dict) -> AgentPlan:
        user_id = task.get("user_id", "")
        return AgentPlan(
            tasks=[{"type": "generate_assessment", "user_id": user_id}],
            focus_areas=["assessment"],
            parameters={"user_id": user_id}
        )

    async def execute(self, plan: AgentPlan) -> AgentResult:
        from app.services.assessment_service import assessment_service
        from app.services.profile_service import profile_service
        from app.core.database import SessionLocal

        user_id = plan.parameters.get("user_id", "")

        db = SessionLocal()
        try:
            profile = profile_service.get_profile(db, user_id) if user_id else None
            result = assessment_service.generate_assessment(
                user_id=user_id, profile=profile, db_session=db,
            )
            return AgentResult(success=True, data=result, summary="学习效果评估报告生成完成")
        except Exception as e:
            logger.error(f"AssessmentAgent execute failed: {e}")
            return AgentResult(success=False, errors=[str(e)])
        finally:
            db.close()

    async def reflect(self, result: AgentResult) -> AgentReflection:
        if not result.success:
            return AgentReflection(quality_score=0.0, issues=["执行失败"], should_retry=True)
        return AgentReflection(quality_score=1.0, issues=[], should_retry=False)
