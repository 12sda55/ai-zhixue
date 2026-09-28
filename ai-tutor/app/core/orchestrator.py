"""编排器 - 系统的核心大脑

对照 AI开发指南_产品内核与架构规范.md 第4.1节：
- 这不是一个Agent，是系统的中枢神经
- 必须能同时调度多个Agent（不是if/elif选一个）
- 必须能处理Agent间的数据依赖（前面的输出作为后面的输入）
- 必须能决定回复策略（纯文本 / 文本+资源卡片 / 纯资源推送）
"""
from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Any, AsyncGenerator

from sqlalchemy.orm import Session

from app.core.llm import llm_client
from app.core.context import ExecutionContext, GeneratedResource
from app.core.true_agent import AGENT_REGISTRY, TrueAgent
from app.schemas.profile import StudentProfile
from app.agents.teacher.agent import AGENT_TOOLS
from app.core.session_state import session_state_machine, SessionState
from app.core.proactive_push import proactive_push
from app.core.progress_engine import progress_engine

logger = logging.getLogger(__name__)

# 生成器安全迭代哨兵：Python 3.13 下 StopIteration 不能直接跨 asyncio Future 传播
_STREAM_END = object()


def _safe_next(gen):
    """线程安全地取下一个流式块，耗尽时返回 _STREAM_END 哨兵"""
    try:
        return next(gen)
    except StopIteration:
        return _STREAM_END


class Orchestrator:
    """编排器 - 意图拆解 → DAG调度 → 结果编织"""

    async def handle_message(
        self,
        user_input: str,
        db: Session,
        user_id: str,
        profile: Optional[StudentProfile] = None,
        current_path: Any = None,
        dialogue_history: list[dict] = None,
    ) -> AsyncGenerator[dict, None]:
        """处理用户消息 - 编排全流程

        Yields SSE events:
        - {"event": "status", "data": {...}} - 状态更新
        - {"event": "agent_status", "data": {...}} - Agent执行状态
        - {"event": "agent_result", "data": {...}} - Agent原始结果
        - {"event": "dag", "data": {...}} - DAG可视化数据
        - {"event": "message", "data": {...}} - 流式文本回复
        - {"event": "resource", "data": {...}} - 资源面板更新
        - {"event": "done", "data": {...}} - 完成信号
        """
        # 1. 创建执行上下文
        ctx = ExecutionContext(
            db_session=db,
            user_id=user_id,
            profile=profile,
            current_path=current_path,
            dialogue_history=dialogue_history or [],
        )

        # 1.5 用户回归欢迎（ProgressEngine）
        welcome_prefix = ""
        try:
            welcome = progress_engine.on_user_return(user_id)
            if welcome and welcome.days_gone >= 3:
                welcome_prefix = welcome.text + "\n\n"
        except Exception as e:
            logger.debug(f"ProgressEngine on_user_return failed: {e}")

        # 1.6 从Redis恢复会话状态
        try:
            session_state_machine.load_from_redis(user_id)
            session = session_state_machine.get_session(user_id)
            # 如果已有视频就绪通知，推送
            if session.metadata.get("pending_video_ready"):
                kp = session.metadata.pop("pending_video_ready")
                push_msg = proactive_push.check_and_push("video_ready", {"knowledge_point": kp})
                if push_msg:
                    yield {
                        "event": "message",
                        "data": json.dumps({"content": push_msg.text}, ensure_ascii=False)
                    }
        except Exception as e:
            logger.debug(f"SessionStateMachine load_from_redis failed: {e}")

        # 2. 先输出一条即时反馈（2秒内第一个token）
        yield {
            "event": "status",
            "data": json.dumps({"status": "thinking", "message": "让我想想需要准备什么资源..."}, ensure_ascii=False)
        }

        # 3. 意图拆解 - LLM分析需要哪些Agent
        plan = await self._plan_tasks(user_input, ctx)

        if not plan["tasks"]:
            # 无需调度Agent，直接流式回复
            yield {"event": "status", "data": json.dumps({"status": "responding", "message": "正在回复..."}, ensure_ascii=False)}
            if welcome_prefix:
                yield {"event": "message", "data": json.dumps({"content": welcome_prefix}, ensure_ascii=False)}
            async for chunk in self._stream_direct_response(user_input, ctx):
                yield {"event": "message", "data": json.dumps({"content": chunk}, ensure_ascii=False)}
            yield {"event": "done", "data": json.dumps({})}
            return

        # 4. 推送DAG数据
        dag = self._build_dag(plan["tasks"])
        yield {"event": "dag", "data": json.dumps(dag, ensure_ascii=False)}

        # 5. 执行DAG - 按依赖关系分层执行
        all_results = {}
        second_round_tasks = []  # 路径→资源联动的第二轮任务

        for layer_idx, layer in enumerate(plan["execution_layers"]):
            # 推送running状态
            for task in layer:
                yield {
                    "event": "agent_status",
                    "data": json.dumps({
                        "agent": task["agent"],
                        "status": "running",
                        "message": f"{self._agent_display_name(task['agent'])} 执行中...",
                    }, ensure_ascii=False)
                }

            # 执行本层Agent（同层并行）
            if len(layer) == 1:
                task = layer[0]
                result = await asyncio.to_thread(
                    self._execute_agent, task["agent"], task["args"], ctx
                )
                all_results[task["agent"]] = result
                ctx.set_agent_output(task["agent"], result)

                # 如果生成了资源，添加到上下文
                self._extract_resources(task["agent"], task["args"], result, ctx)

                # 路径→资源联动：path_agent完成后自动调度前3个节点的资源生成
                if task["agent"] == "path_agent" and "error" not in result:
                    path_data = result
                    nodes = path_data.get("nodes", [])
                    first_3_nodes = nodes[:3]
                    for node in first_3_nodes:
                        node_id = node.get("node_id", "")
                        if node_id:
                            second_round_tasks.append({
                                "agent": "document_agent",
                                "action": "generate",
                                "args": {"knowledge_point": node_id, "user_id": ctx.user_id},
                                "depends_on": ["path_agent"],
                            })
                            second_round_tasks.append({
                                "agent": "question_agent",
                                "action": "generate",
                                "args": {"knowledge_point": node_id, "user_id": ctx.user_id, "count": 2},
                                "depends_on": ["path_agent"],
                            })
                    # 修改path_agent的回复文本
                    if first_3_nodes:
                        result["message"] = f"3周学习路径已生成，第1周的学习资料已准备好，从{first_3_nodes[0].get('name', '第一个知识点')}开始吧"

            else:
                results = await asyncio.gather(*[
                    asyncio.to_thread(self._execute_agent, t["agent"], t["args"], ctx)
                    for t in layer
                ], return_exceptions=True)

                for task, result in zip(layer, results):
                    if isinstance(result, Exception):
                        all_results[task["agent"]] = {"error": str(result)}
                    else:
                        all_results[task["agent"]] = result
                        ctx.set_agent_output(task["agent"], result)
                        self._extract_resources(task["agent"], task["args"], result, ctx)

                        # 路径→资源联动：path_agent完成后自动调度前3个节点的资源生成
                        if task["agent"] == "path_agent" and "error" not in result:
                            path_data = result
                            nodes = path_data.get("nodes", [])
                            first_3_nodes = nodes[:3]
                            for node in first_3_nodes:
                                node_id = node.get("node_id", "")
                                if node_id:
                                    second_round_tasks.append({
                                        "agent": "document_agent",
                                        "action": "generate",
                                        "args": {"knowledge_point": node_id, "user_id": ctx.user_id},
                                        "depends_on": ["path_agent"],
                                    })
                                    second_round_tasks.append({
                                        "agent": "question_agent",
                                        "action": "generate",
                                        "args": {"knowledge_point": node_id, "user_id": ctx.user_id, "count": 2},
                                        "depends_on": ["path_agent"],
                                    })
                            if first_3_nodes:
                                result["message"] = f"3周学习路径已生成，第1周的学习资料已准备好，从{first_3_nodes[0].get('name', '第一个知识点')}开始吧"

            # 推送完成状态
            for task in layer:
                agent_result = all_results.get(task["agent"], {})
                status = "completed" if "error" not in agent_result else "failed"
                yield {
                    "event": "agent_status",
                    "data": json.dumps({
                        "agent": task["agent"],
                        "status": status,
                        "message": f"{self._agent_display_name(task['agent'])} {'已完成' if status == 'completed' else '执行失败'}",
                    }, ensure_ascii=False)
                }
                # 推送Agent原始结果
                if status == "completed":
                    yield {
                        "event": "agent_result",
                        "data": json.dumps({
                            "agent": task["agent"],
                            "result": agent_result,
                        }, ensure_ascii=False)
                    }

        # 5.5 执行第二轮任务（路径→资源联动）
        if second_round_tasks:
            # 构建第二轮执行层
            second_layers = self._build_execution_layers(second_round_tasks)
            for layer_idx, layer in enumerate(second_layers):
                for task in layer:
                    yield {
                        "event": "agent_status",
                        "data": json.dumps({
                            "agent": task["agent"],
                            "status": "running",
                            "message": f"{self._agent_display_name(task['agent'])} 执行中（路径联动）...",
                        }, ensure_ascii=False)
                    }

                results = await asyncio.gather(*[
                    asyncio.to_thread(self._execute_agent, t["agent"], t["args"], ctx)
                    for t in layer
                ], return_exceptions=True)

                for task, result in zip(layer, results):
                    agent_key = f"{task['agent']}_{task['args'].get('knowledge_point', '')}"
                    if isinstance(result, Exception):
                        all_results[agent_key] = {"error": str(result)}
                    else:
                        all_results[agent_key] = result
                        ctx.set_agent_output(task["agent"], result)
                        self._extract_resources(task["agent"], task["args"], result, ctx)

                for task in layer:
                    agent_key = f"{task['agent']}_{task['args'].get('knowledge_point', '')}"
                    agent_result = all_results.get(agent_key, {})
                    status = "completed" if "error" not in agent_result else "failed"
                    yield {
                        "event": "agent_status",
                        "data": json.dumps({
                            "agent": task["agent"],
                            "status": status,
                            "message": f"{self._agent_display_name(task['agent'])} {'已完成' if status == 'completed' else '执行失败'}（路径联动）",
                        }, ensure_ascii=False)
                    }
                    if status == "completed":
                        yield {
                            "event": "agent_result",
                            "data": json.dumps({
                                "agent": task["agent"],
                                "result": agent_result,
                            }, ensure_ascii=False)
                        }

            # 更新DAG
            dag = self._build_dag(plan["tasks"] + second_round_tasks)
            yield {"event": "dag", "data": json.dumps(dag, ensure_ascii=False)}

        # 6. 推送资源面板更新
        for resource in ctx.generated_resources:
            yield {
                "event": "resource",
                "data": json.dumps({
                    "id": resource.id,
                    "type": resource.type,
                    "title": self._resource_title(resource),
                    "kg_node_ids": resource.kg_node_ids,
                    "path_node_id": resource.path_node_id,
                }, ensure_ascii=False)
            }

        # 7. 结果编织 - 生成最终回复
        yield {"event": "status", "data": json.dumps({"status": "integrating", "message": "正在整合结果..."}, ensure_ascii=False)}

        # 7.5 ProactivePushSystem — 在关键节点主动推送
        push_msg = None
        last_agent = ""
        for agent_name in all_results:
            if "error" not in all_results[agent_name]:
                last_agent = agent_name
        # 取原始agent名（去掉路径联动的后缀）
        last_agent_base = last_agent.split("_")[0] + "_" + last_agent.split("_")[1] if "_" in last_agent else last_agent

        trigger = ""
        push_context = {"user_id": ctx.user_id, "knowledge_point": ctx.knowledge_point if hasattr(ctx, 'knowledge_point') else ""}

        if last_agent_base == "document_agent":
            trigger = "after_document_generated"
        elif last_agent_base == "question_agent":
            # 检查是否全对
            last_result = all_results.get(last_agent, {})
            all_correct = last_result.get("all_correct", False)
            if all_correct:
                trigger = "after_quiz_all_correct"
            else:
                trigger = "after_quiz_partial"
                wrong_count = last_result.get("wrong_count", 0)
                push_context["wrong_count"] = wrong_count
        elif last_agent_base == "profile_agent":
            session = session_state_machine.get_session(user_id)
            if session.state == SessionState.COLD_START:
                trigger = "after_cold_start_completed"

        if trigger:
            try:
                push_msg = proactive_push.check_and_push(trigger, push_context)
            except Exception as e:
                logger.debug(f"ProactivePushSystem check_and_push failed: {e}")

        # 输出欢迎前缀
        if welcome_prefix:
            yield {"event": "message", "data": json.dumps({"content": welcome_prefix}, ensure_ascii=False)}

        async for chunk in self._stream_integrated_response(user_input, all_results, ctx):
            yield {"event": "message", "data": json.dumps({"content": chunk}, ensure_ascii=False)}

        # 追加推送消息
        if push_msg:
            yield {"event": "message", "data": json.dumps({"content": f"\n\n{push_msg.text}"}, ensure_ascii=False)}
            if push_msg.quick_action:
                yield {
                    "event": "quick_action",
                    "data": json.dumps({
                        "action": push_msg.quick_action,
                        "label": push_msg.quick_action_label,
                        "trigger": push_msg.trigger,
                    }, ensure_ascii=False)
                }

        # 8. 更新SessionStateMachine
        try:
            new_state = SessionState.IDLE
            kp = ""
            if last_agent_base == "document_agent":
                new_state = SessionState.LEARNING
                kp = all_results.get(last_agent, {}).get("knowledge_point", "")
            elif last_agent_base == "question_agent":
                new_state = SessionState.PRACTICING
                kp = all_results.get(last_agent, {}).get("knowledge_point", "")
            elif last_agent_base == "assessment_agent":
                new_state = SessionState.ASSESSING
            elif last_agent_base == "profile_agent":
                new_state = SessionState.IDLE

            session_state_machine.transition(user_id, new_state, current_knowledge_point=kp)
            session = session_state_machine.get_session(user_id)
            session.last_agent = last_agent_base
            session.last_action = trigger
            session_state_machine.save_to_redis(user_id)
        except Exception as e:
            logger.debug(f"SessionStateMachine update failed: {e}")

        # 9. 推送完成信号
        yield {
            "event": "done",
            "data": json.dumps({
                "agent_calls": list(all_results.keys()),
                "dag": dag,
                "resources": [
                    {"id": r.id, "type": r.type, "kg_node_ids": r.kg_node_ids}
                    for r in ctx.generated_resources
                ],
            }, ensure_ascii=False)
        }

    async def _plan_tasks(self, user_input: str, ctx: ExecutionContext) -> dict:
        """意图拆解 - LLM分析需要哪些Agent，确定依赖关系

        Returns:
            {
                "tasks": [
                    {"agent": "profile_agent", "action": "update", "args": {...}, "depends_on": []},
                    {"agent": "path_agent", "action": "generate", "args": {...}, "depends_on": ["profile_agent"]},
                    ...
                ],
                "execution_layers": [
                    [task1, task2],  # 第一层（并行）
                    [task3],         # 第二层（依赖第一层）
                ],
                "response_strategy": "text_and_resources"
            }
        """
        # 构建规划prompt
        profile_summary = self._build_profile_summary(ctx.profile) if ctx.profile else "（新用户）"
        path_context = ""
        if ctx.current_path:
            path_context = f"当前学习路径：{ctx.current_path}"  # simplified

        planning_prompt = f"""分析以下学生消息，决定需要调度哪些Agent来处理。

学生消息：{user_input}

当前学生画像：{profile_summary}
{path_context}

可用的Agent：
- profile_agent: 画像查询/更新
- document_agent: 讲解文档生成
- question_agent: 练习题生成
- code_agent: 代码实操/沙箱
- path_agent: 学习路径规划
- multimodal_agent: 可视化/思维导图
- video_agent: 算法视频生成
- tutor_agent: Socratic辅导
- reading_agent: 拓展阅读生成
- assessment_agent: 学习效果评估

请返回JSON格式的执行计划：
{{
    "tasks": [
        {{"agent": "agent_name", "action": "action_type", "args": {{"key": "value"}}, "depends_on": []}},
        ...
    ],
    "response_strategy": "text_only" | "text_and_resources" | "resources_first"
}}

规则：
1. 如果学生说"速通/规划/怎么学"→ 同时调度 profile_agent + path_agent
2. 如果学生说"讲一下/解释"→ 调度 document_agent，如果适合可视化则加 multimodal_agent
3. 如果学生说"出题/练习"→ 调度 question_agent
4. 如果学生说"写代码/运行"→ 调度 code_agent
5. 如果学生说"为什么/不懂"→ 调度 tutor_agent
6. 如果学生说"拓展/阅读/参考资料"→ 调度 reading_agent
7. 如果学生说"评估/测评/效果"→ 调度 assessment_agent
8. path_agent 依赖 profile_agent 的输出（depends_on: ["profile_agent"]）
9. document_agent 如果和 path_agent 同时调度，可以并行
10. 简单问候/闲聊 → tasks为空数组

只返回JSON，不要其他内容。"""

        try:
            # 使用规划prompt
            result = await asyncio.to_thread(
                llm_client.chat,
                messages=[
                    {"role": "system", "content": "你是任务规划器，只返回JSON。"},
                    {"role": "user", "content": planning_prompt},
                ],
                temperature=0.1,
            )

            # 解析JSON
            plan = json.loads(result.strip().removeprefix("```json").removesuffix("```").strip())

            # 验证和补充
            tasks = plan.get("tasks", [])

            # 应用规则兜底
            tasks = self._apply_planning_rules(user_input, tasks, ctx)

            # 构建执行层
            execution_layers = self._build_execution_layers(tasks)

            return {
                "tasks": tasks,
                "execution_layers": execution_layers,
                "response_strategy": plan.get("response_strategy", "text_and_resources"),
            }

        except Exception as e:
            logger.error(f"意图拆解失败: {e}")
            # 降级：使用Function Calling
            return await self._fallback_plan_with_fc(user_input, ctx)

    def _apply_planning_rules(self, user_input: str, tasks: list, ctx: ExecutionContext) -> list:
        """应用规划规则兜底"""
        agent_names = [t["agent"] for t in tasks]

        # 如果调度了path_agent但没有profile_agent，自动补充
        if "path_agent" in agent_names and "profile_agent" not in agent_names:
            tasks.insert(0, {
                "agent": "profile_agent",
                "action": "get_profile",
                "args": {"action": "get_profile", "user_id": ctx.user_id},
                "depends_on": [],
            })
            # path_agent 现在依赖 profile_agent
            for t in tasks:
                if t["agent"] == "path_agent" and "profile_agent" not in t.get("depends_on", []):
                    t.setdefault("depends_on", []).append("profile_agent")

        # 如果调度了document_agent，检查是否需要补充question_agent
        if "document_agent" in agent_names and "question_agent" not in agent_names:
            # 检测知识点关键词
            kp_keywords = ["讲", "解释", "理解", "学习", "是什么"]
            if any(kw in user_input for kw in kp_keywords):
                doc_task = next(t for t in tasks if t["agent"] == "document_agent")
                kp = doc_task.get("args", {}).get("knowledge_point", "")
                if kp:
                    tasks.append({
                        "agent": "question_agent",
                        "action": "generate",
                        "args": {"knowledge_point": kp, "user_id": ctx.user_id, "count": 2},
                        "depends_on": ["document_agent"],
                    })

        # 如果用户说"评估/测评/效果"，自动补充assessment_agent
        assessment_keywords = ["评估", "测评", "效果", "学得怎么样", "学习报告", "学习效果"]
        if any(kw in user_input for kw in assessment_keywords) and "assessment_agent" not in agent_names:
            tasks.append({
                "agent": "assessment_agent",
                "action": "generate",
                "args": {"user_id": ctx.user_id},
                "depends_on": [],
            })

        # 如果用户说"拓展/阅读/参考资料"，自动补充reading_agent
        reading_keywords = ["拓展", "阅读", "参考资料", "推荐书", "深入"]
        if any(kw in user_input for kw in reading_keywords) and "reading_agent" not in agent_names:
            # 尝试从已有任务中提取知识点
            kp = ""
            for t in tasks:
                kp = t.get("args", {}).get("knowledge_point", "")
                if kp:
                    break
            if kp:
                tasks.append({
                    "agent": "reading_agent",
                    "action": "generate",
                    "args": {"knowledge_point": kp, "user_id": ctx.user_id},
                    "depends_on": [],
                })

        # 确保所有task都有user_id
        for t in tasks:
            if "user_id" not in t.get("args", {}):
                t["args"]["user_id"] = ctx.user_id

        return tasks

    def _build_execution_layers(self, tasks: list) -> list[list[dict]]:
        """根据依赖关系构建执行层"""
        if not tasks:
            return []

        # 拓扑排序分层
        layers = []
        remaining = list(tasks)
        completed = set()

        while remaining:
            # 找出所有依赖已满足的task
            layer = []
            for task in remaining:
                deps = task.get("depends_on", [])
                if all(d in completed for d in deps):
                    layer.append(task)

            if not layer:
                # 循环依赖，把剩余的都放一层
                layers.append(remaining)
                break

            layers.append(layer)
            for t in layer:
                completed.add(t["agent"])
                remaining.remove(t)

        return layers

    def _execute_agent(self, agent_name: str, args: dict, ctx: ExecutionContext) -> dict:
        """执行单个Agent - 优先使用AGENT_REGISTRY，回退到旧版分发"""
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
                import asyncio
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

        # 2. 回退：如果注册表中没有，使用旧版分发（兼容期）
        logger.warning(f"Agent '{agent_name}' not in AGENT_REGISTRY, falling back to legacy dispatch")
        from app.agents.teacher.agent import _dispatch_agent_with_context
        return _dispatch_agent_with_context(agent_name, args, ctx)

    def _extract_resources(self, agent_name: str, args: dict, result: dict, ctx: ExecutionContext) -> None:
        """从Agent结果中提取资源，添加到上下文并持久化到DB"""
        if "error" in result:
            return

        resource_type_map = {
            "path_agent": "path",
            "document_agent": "document",
            "question_agent": "question",
            "code_agent": "code",
            "multimodal_agent": "mind_map",
            "video_agent": "video",
            "tutor_agent": None,  # 辅导不生成资源
            "profile_agent": None,  # 画像不生成资源
            "reading_agent": "reading",
            "assessment_agent": "assessment",
        }

        resource_type = resource_type_map.get(agent_name)
        if not resource_type:
            return

        # 提取知识点ID
        kg_node_ids = []
        kp = result.get("knowledge_point", "") or args.get("knowledge_point", "")
        if kp:
            kg_node_ids = [kp]

        resource_id = f"{resource_type}_{ctx.user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        resource = GeneratedResource(
            id=resource_id,
            type=resource_type,
            content=result,
            kg_node_ids=kg_node_ids,
        )
        ctx.add_resource(resource)

        # 持久化到数据库（对照规范 B8：所有资源都有 kg_node_id 关联）
        self._persist_resource(resource, ctx)

    def _persist_resource(self, resource: GeneratedResource, ctx: ExecutionContext) -> None:
        """将资源持久化到数据库"""
        try:
            from app.models.profile import ResourceModel
            import json

            db = ctx.db_session
            existing = db.query(ResourceModel).filter(ResourceModel.id == resource.id).first()
            if existing:
                return

            row = ResourceModel(
                id=resource.id,
                type=resource.type,
                content_json=json.dumps(resource.content, ensure_ascii=False),
                kg_node_ids=json.dumps(resource.kg_node_ids, ensure_ascii=False),
                path_node_id=resource.path_node_id or "",
                parent_resource_id=resource.parent_resource_id or "",
                user_id=ctx.user_id,
                title=self._resource_title(resource),
            )
            db.add(row)
            db.flush()  # flush但不commit，让chat.py统一commit
            logger.info(f"资源已持久化: id={resource.id}, type={resource.type}, kg_nodes={resource.kg_node_ids}")
        except Exception as e:
            logger.error(f"资源持久化失败: {e}")
            # 不影响主流程，只记录错误

    def _build_dag(self, tasks: list) -> dict:
        """构建DAG可视化数据"""
        nodes = [{"id": "user_input", "label": "用户输入", "type": "input"}]
        edges = []

        for task in tasks:
            agent = task["agent"]
            nodes.append({
                "id": agent,
                "label": self._agent_display_name(agent),
                "type": "agent",
                "agent": agent,
            })
            deps = task.get("depends_on", [])
            if not deps:
                edges.append({"source": "user_input", "target": agent})
            else:
                for dep in deps:
                    edges.append({"source": dep, "target": agent})

        if len(tasks) > 0:
            nodes.append({"id": "integrate", "label": "整合回复", "type": "output"})
            for task in tasks:
                edges.append({"source": task["agent"], "target": "integrate"})

        return {"nodes": nodes, "edges": edges}

    async def _stream_direct_response(self, user_input: str, ctx: ExecutionContext) -> AsyncGenerator[str, None]:
        """直接流式回复（无需Agent调度时）"""
        messages = [
            {"role": "system", "content": "你是小智，学习辅导老师。简洁友好地回复。"},
            {"role": "user", "content": user_input},
        ]
        loop = asyncio.get_event_loop()
        gen = llm_client.chat_stream(messages=messages, temperature=0.5)
        while True:
            chunk = await loop.run_in_executor(None, _safe_next, gen)
            if chunk is _STREAM_END:
                break
            yield chunk

    async def _stream_integrated_response(
        self, user_input: str, results: dict, ctx: ExecutionContext
    ) -> AsyncGenerator[str, None]:
        """流式编织整合回复"""
        results_text = ""
        for agent_name, result in results.items():
            results_text += f"\n### {self._agent_display_name(agent_name)} 结果:\n{json.dumps(result, ensure_ascii=False, indent=2)[:2000]}\n"

        resources_text = ""
        if ctx.generated_resources:
            resources_text = "\n\n已生成的资源：\n"
            for r in ctx.generated_resources:
                resources_text += f"- {self._resource_title(r)}（知识点: {', '.join(r.kg_node_ids)}）\n"

        profile_summary = self._build_profile_summary(ctx.profile) if ctx.profile else "（新用户）"

        integration_prompt = f"""请根据以下各Agent的执行结果，整合生成一个连贯、自然的回复给学生。

重要规则：
1. 用中文回复，使用Markdown格式
2. 整合各Agent结果，不要简单罗列
3. 资源内容不要在对话中展开——只说"已生成XXX，点击右侧面板查看"
4. 根据学生画像调整语气和详细程度
5. 适当推荐下一步学习内容

当前学生画像：
{profile_summary}

各Agent结果：
{results_text}
{resources_text}
"""

        messages = [
            {"role": "system", "content": integration_prompt},
            {"role": "user", "content": user_input},
        ]

        loop = asyncio.get_event_loop()
        gen = llm_client.chat_stream(messages=messages, temperature=0.5)
        while True:
            chunk = await loop.run_in_executor(None, _safe_next, gen)
            if chunk is _STREAM_END:
                break
            yield chunk

    async def _fallback_plan_with_fc(self, user_input: str, ctx: ExecutionContext) -> dict:
        """降级：使用Function Calling规划"""
        try:
            profile_summary = self._build_profile_summary(ctx.profile) if ctx.profile else "（新用户）"

            llm_messages = [
                {"role": "system", "content": f"你是小智，学习辅导老师。当前学生画像：{profile_summary}"},
                {"role": "user", "content": user_input},
            ]

            fc_result = await asyncio.to_thread(
                llm_client.chat_with_tools,
                messages=llm_messages,
                tools=AGENT_TOOLS,
                temperature=0.3,
            )

            if not fc_result["tool_calls"]:
                return {"tasks": [], "execution_layers": [], "response_strategy": "text_only"}

            from app.agents.teacher.dispatcher import validate_agent_args, apply_fallback_rules

            tasks = []
            for tool_call in fc_result["tool_calls"]:
                func_name = tool_call.function.name
                try:
                    func_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    continue
                func_args = validate_agent_args(func_name, func_args)
                tasks.append({
                    "agent": func_name,
                    "action": func_args.get("action", ""),
                    "args": func_args,
                    "depends_on": [],
                })

            # 应用规则兜底
            agent_calls = [{"agent": t["agent"], "args": t["args"]} for t in tasks]
            agent_calls = apply_fallback_rules(agent_calls)

            # 重建tasks（兜底可能新增了Agent）
            existing_agents = {t["agent"] for t in tasks}
            for call in agent_calls:
                if call["agent"] not in existing_agents:
                    tasks.append({
                        "agent": call["agent"],
                        "action": call["args"].get("action", ""),
                        "args": call["args"],
                        "depends_on": [],
                    })

            # 补充依赖关系
            for t in tasks:
                if t["agent"] == "path_agent" and "profile_agent" in {tt["agent"] for tt in tasks}:
                    if "profile_agent" not in t.get("depends_on", []):
                        t.setdefault("depends_on", []).append("profile_agent")

            execution_layers = self._build_execution_layers(tasks)

            return {
                "tasks": tasks,
                "execution_layers": execution_layers,
                "response_strategy": "text_and_resources",
            }

        except Exception as e:
            logger.error(f"Function Calling降级也失败: {e}")
            return {"tasks": [], "execution_layers": [], "response_strategy": "text_only"}

    @staticmethod
    def _agent_display_name(agent_name: str) -> str:
        names = {
            "profile_agent": "画像构建",
            "document_agent": "文档生成",
            "question_agent": "题库生成",
            "code_agent": "代码实操",
            "path_agent": "路径规划",
            "multimodal_agent": "多模态资源",
            "video_agent": "视频生成",
            "tutor_agent": "智能辅导",
            "reading_agent": "拓展阅读",
            "assessment_agent": "学习评估",
            "teacher_agent": "虚拟老师",
        }
        return names.get(agent_name, agent_name)

    @staticmethod
    def _resource_title(resource: GeneratedResource) -> str:
        type_titles = {
            "path": "🗺️ 学习路径",
            "document": "📄 讲解文档",
            "question": "📝 练习题",
            "code": "💻 代码模板",
            "video": "🎬 算法视频",
            "mind_map": "🧠 思维导图",
            "assessment": "📊 评估报告",
            "reading": "📖 拓展阅读",
        }
        return type_titles.get(resource.type, resource.type)

    @staticmethod
    def _build_profile_summary(profile: StudentProfile) -> str:
        """从画像生成摘要文本"""
        if not profile:
            return "（新用户）"
        parts = [
            f"专业：{profile.major.value}",
            f"阶段：{profile.stage.value}",
            f"认知风格：{profile.cognitive_style.value}",
            f"难度偏好：{profile.difficulty_level.value}",
        ]
        if profile.weak_points:
            weak_names = [wp.knowledge_point for wp in profile.weak_points]
            parts.append(f"薄弱环节：{', '.join(weak_names)}")
        if profile.learning_goals:
            parts.append(f"学习目标：{', '.join(profile.learning_goals)}")
        return "\n".join(parts)


# 全局单例
orchestrator = Orchestrator()
