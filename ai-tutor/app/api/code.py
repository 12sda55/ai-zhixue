"""代码实操API - Phase 5

对照 ai_architecture_plan.md Agent 6：
- 预制代码库 + AI动态生成
- 代码沙箱执行
- AI解析面板（代码分析+优化建议+逐行注释）
- 实操→知识点闭环
- 代码填空挑战
- 代码进化轨迹
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.code_service import code_sandbox, ExecutionResult
from app.services.profile_service import ProfileService
from app.rules.profile_rules import LearningEvent, EventType
from app.knowledge.code_templates import CODE_TEMPLATES

logger = logging.getLogger(__name__)
router = APIRouter()
profile_service = ProfileService()


# ---- 请求模型 ----

class CodeSubmitRequest(BaseModel):
    code: str
    knowledge_point: str
    template_id: str = ""
    is_fill_blank: bool = False
    iteration: int = 1  # 第几次提交


class CodeAnalyzeRequest(BaseModel):
    code: str
    knowledge_point: str


# ---- 端点 ----

@router.get("/templates")
async def list_templates(
    knowledge_point: str = Query(None, description="知识点ID（可选，不传则返回全部）"),
):
    """获取预制代码模板列表"""
    if knowledge_point:
        templates = CODE_TEMPLATES.get(knowledge_point, [])
    else:
        templates = []
        for kp, tpls in CODE_TEMPLATES.items():
            for t in tpls:
                templates.append({**t, "knowledge_point": kp})

    # 返回摘要（不含完整代码，前端按需加载）
    result = []
    for t in templates:
        result.append({
            "id": t["id"],
            "title": t["title"],
            "description": t["description"],
            "difficulty": t["difficulty"],
            "has_blanks": bool(t.get("blanks")),
            "test_count": len(t.get("test_cases", [])),
            "knowledge_point": t.get("knowledge_point", knowledge_point or ""),
        })
    return {"templates": result, "total": len(result)}


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """获取代码模板详情（含完整代码和填空版）"""
    for kp, templates in CODE_TEMPLATES.items():
        for t in templates:
            if t["id"] == template_id:
                # 生成填空版代码
                fill_blank_code = _generate_fill_blank(t)

                return {
                    "id": t["id"],
                    "title": t["title"],
                    "description": t["description"],
                    "code": t["code"],
                    "fill_blank_code": fill_blank_code,
                    "test_cases": t.get("test_cases", []),
                    "difficulty": t["difficulty"],
                    "blanks": t.get("blanks", []),
                    "knowledge_point": kp,
                }
    return {"error": f"模板 {template_id} 不存在"}


@router.post("/execute")
async def execute_code(
    req: CodeSubmitRequest,
    db: Session = Depends(get_db),
):
    """执行代码 + 测试用例验证 + 画像闭环

    对照设计文档闭环逻辑：
    - 运行成功 → AI解析+优化建议 → mastery提升
    - 编译/运行错误 → AI诊断
    - 逻辑错误 → AI对比期望vs实际
    - 多次失败(3次+) → 触发知识点回讲
    """
    # 1. 获取测试用例
    test_cases = []
    template = _find_template(req.template_id) if req.template_id else None
    if template:
        test_cases = template.get("test_cases", [])
    elif req.knowledge_point:
        # 从知识点找默认模板
        kp_templates = CODE_TEMPLATES.get(req.knowledge_point, [])
        if kp_templates:
            test_cases = kp_templates[0].get("test_cases", [])

    # 2. 沙箱执行
    result: ExecutionResult = code_sandbox.execute(
        code=req.code,
        test_cases=test_cases,
    )

    # 3. 诊断错误
    diagnosis = None
    if not result.success:
        diagnosis = _diagnose_error(result, req.code)

    # 4. 判断是否需要回讲
    need_review = (not result.success) and (req.iteration >= 3)

    # 5. 后台更新画像（异步，不阻塞）
    import asyncio
    user_id = getattr(req, '_user_id', 'anonymous')
    if result.success:
        # 1-2次通过: +0.12, 6+次: +0.03
        delta = 0.12 if req.iteration <= 2 else 0.03
        event = LearningEvent(
            event_type=EventType.CODE_PASS_QUICK if req.iteration <= 2 else EventType.CODE_PASS_SLOW,
            user_id=user_id,
            knowledge_point=req.knowledge_point,
            data={"iteration": req.iteration, "delta": delta},
        )
    else:
        event = LearningEvent(
            event_type=EventType.ANSWER_WRONG,
            user_id=user_id,
            knowledge_point=req.knowledge_point,
            data={"iteration": req.iteration, "error_type": diagnosis.get("type", "unknown") if diagnosis else "unknown"},
        )

    try:
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, lambda: _update_profile_bg(user_id, event))
    except Exception:
        pass

    return {
        "success": result.success,
        "output": result.output[:2000],
        "error": result.error[:1000] if result.error else "",
        "test_results": result.test_results,
        "diagnosis": diagnosis,
        "need_review": need_review,
        "iteration": req.iteration,
    }


@router.post("/analyze")
async def analyze_code(req: CodeAnalyzeRequest):
    """AI解析面板

    对照设计文档：
    - 代码分析：这段代码做了什么，时间/空间复杂度
    - 优化建议：可以怎么改进
    - 相关知识点链接
    - 逐行注释：对关键行生成自然语言解释
    """
    from app.core.llm import llm_client

    prompt = f"""你是一位编程课程助教，请分析以下学生提交的Python代码。

## 知识点
{req.knowledge_point}

## 学生代码
```python
{req.code}
```

请按以下格式输出（JSON）：
```json
{{
    "summary": "代码功能概述（1-2句话）",
    "time_complexity": "时间复杂度分析",
    "space_complexity": "空间复杂度分析",
    "optimization": "优化建议（如果有）",
    "related_knowledge": ["相关知识点1", "相关知识点2"],
    "line_annotations": [
        {{"line": 1, "comment": "这一行的作用"}},
        {{"line": 5, "comment": "关键逻辑：xxx"}}
    ],
    "score": 85,
    "issues": ["问题1（如果有）", "问题2"]
}}
```

只输出JSON，不要其他内容。"""

    try:
        response = llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )

        # 解析JSON
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        analysis = json.loads(response.strip())

        return {
            "analysis": analysis,
            "knowledge_point": req.knowledge_point,
        }

    except json.JSONDecodeError:
        return {
            "analysis": {
                "summary": response[:500] if response else "分析失败",
                "time_complexity": "N/A",
                "space_complexity": "N/A",
            },
            "knowledge_point": req.knowledge_point,
        }
    except Exception as e:
        logger.error(f"AI解析失败: {e}")
        return {"error": f"AI解析失败: {str(e)}"}


@router.get("/history/{user_id}")
async def get_code_history(
    user_id: str,
    knowledge_point: str = Query(None),
    db: Session = Depends(get_db),
):
    """获取代码进化轨迹"""
    from app.models.profile import AnswerRecordModel

    query = db.query(AnswerRecordModel).filter(
        AnswerRecordModel.user_id == user_id,
    )
    if knowledge_point:
        query = query.filter(AnswerRecordModel.knowledge_point == knowledge_point)

    records = query.order_by(AnswerRecordModel.created_at.desc()).limit(50).all()

    return {
        "history": [
            {
                "id": r.id,
                "knowledge_point": r.knowledge_point,
                "question_id": r.question_id,
                "is_correct": r.is_correct,
                "level_at_question": r.level_at_question,
                "created_at": str(r.created_at),
            }
            for r in records
        ],
        "total": len(records),
    }


# ---- 辅助函数 ----

def _find_template(template_id: str) -> Optional[dict]:
    """查找模板"""
    for kp, templates in CODE_TEMPLATES.items():
        for t in templates:
            if t["id"] == template_id:
                return t
    return None


def _generate_fill_blank(template: dict) -> str:
    """从预制代码生成填空版

    将blanks指定的行替换为注释提示
    """
    code_lines = template["code"].split("\n")
    blanks = template.get("blanks", [])

    for blank in blanks:
        line_idx = blank["line"] - 1  # 转为0-based
        if 0 <= line_idx < len(code_lines):
            hint = blank.get("hint", "填写代码")
            indent = len(code_lines[line_idx]) - len(code_lines[line_idx].lstrip())
            code_lines[line_idx] = " " * indent + f"# ___ {hint} ___"

    return "\n".join(code_lines)


def _diagnose_error(result: ExecutionResult, code: str) -> dict:
    """诊断代码错误

    返回：
    - type: syntax_error / runtime_error / logic_error / timeout
    - message: 诊断信息
    - suggestion: 修复建议
    """
    if result.error:
        if "SyntaxError" in result.error or "IndentationError" in result.error:
            return {
                "type": "syntax_error",
                "message": "语法错误：代码存在语法问题",
                "suggestion": "检查拼写、缩进、括号匹配",
                "detail": result.error[:300],
            }
        if "TimeLimit" in result.error or "超时" in result.error:
            return {
                "type": "timeout",
                "message": "运行超时：代码可能存在死循环或效率过低",
                "suggestion": "检查循环终止条件，考虑优化算法复杂度",
                "detail": result.error[:300],
            }
        return {
            "type": "runtime_error",
            "message": "运行时错误：代码执行过程中出错",
            "suggestion": "检查边界条件、空值处理、类型转换",
            "detail": result.error[:300],
        }

    # 有输出但不正确 → 逻辑错误
    failed_tests = [r for r in result.test_results if not r["passed"]]
    if failed_tests:
        first_fail = failed_tests[0]
        return {
            "type": "logic_error",
            "message": "逻辑错误：输出结果与预期不符",
            "suggestion": "对比期望输出和实际输出，检查算法逻辑",
            "detail": f"输入: {first_fail.get('input', '')}\n期望: {first_fail.get('expected', '')}\n实际: {first_fail.get('output', '')}",
        }

    return {
        "type": "unknown",
        "message": "未知错误",
        "suggestion": "请检查代码逻辑",
    }


def _update_profile_bg(user_id: str, event):
    """后台更新画像"""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        profile_service.process_event(db, event)
        db.commit()
    except Exception as e:
        logger.warning(f"后台画像更新失败: {e}")
        db.rollback()
    finally:
        db.close()
