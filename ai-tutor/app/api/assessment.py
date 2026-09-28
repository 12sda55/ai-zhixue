"""评估接口 - 对照规范 4.8

完整实现：
- POST /generate - 生成评估报告（新版，返回AssessmentResult）
- GET /{user_id} - 获取最新评估报告（新版，返回AssessmentResult）
- POST /update - 更新学习进度
- POST /adjust-path - 动态调整学习路径
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.assessment_service import assessment_service
from app.services.profile_service import profile_service
from app.models.profile import ResourceModel
from app.schemas.assessment import (
    AssessmentRequest,
    LearningProgressUpdate,
    PathAdjustmentRequest
)

router = APIRouter()


class AssessmentGenerateRequest(BaseModel):
    """评估生成请求"""
    user_id: str


@router.post("/generate")
async def generate_assessment(
    req: AssessmentGenerateRequest,
    db: Session = Depends(get_db),
):
    """生成学习效果评估报告（新版）

    返回完整的AssessmentResult对象，包含：
    - 学习时长统计
    - 学习效率评估
    - 各知识点学习进度
    - 薄弱点识别
    - 路径动态调整建议
    """
    profile = profile_service.get_profile(db, req.user_id)

    # 使用新的generate_assessment_result方法
    assessment_result = assessment_service.generate_assessment_result(
        user_id=req.user_id,
        profile=profile,
        db_session=db,
    )

    # 保存评估报告到数据库（可选）
    resource_id = f"assessment_{uuid.uuid4().hex[:12]}"
    resource = ResourceModel(
        id=resource_id,
        type="assessment",
        user_id=req.user_id,
        title=f"学习效果评估报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        content_json=json.dumps(assessment_result.model_dump()),
        status="completed",
        created_at=datetime.now()
    )
    db.add(resource)
    db.commit()

    return {
        "status": "ok",
        "resource_id": resource_id,
        "assessment": assessment_result.model_dump()
    }


@router.get("/{user_id}")
async def get_latest_assessment(
    user_id: str,
    db: Session = Depends(get_db),
):
    """获取最新的评估报告（新版）

    返回完整的AssessmentResult对象格式
    """
    # 优先从数据库获取最新评估报告
    resource = (
        db.query(ResourceModel)
        .filter(
            ResourceModel.user_id == user_id,
            ResourceModel.type == "assessment",
        )
        .order_by(ResourceModel.created_at.desc())
        .first()
    )

    if resource:
        content = json.loads(resource.content_json) if resource.content_json else {}

        # 检查是否是新版AssessmentResult格式
        if "overall_mastery" in content:
            # 新版格式，直接返回
            return {
                "status": "ok",
                "resource_id": resource.id,
                "title": resource.title,
                "assessment": content,
                "created_at": resource.created_at.isoformat() if resource.created_at else None,
            }
        else:
            # 旧版格式，兼容处理
            return {
                "status": "ok",
                "resource_id": resource.id,
                "title": resource.title,
                "overall_score": content.get("overall_score", 0),
                "mastery_trend": content.get("mastery_trend", []),
                "weak_points_improvement": content.get("weak_points_improvement", []),
                "goal_gap_analysis": content.get("goal_gap_analysis", {}),
                "recommendations": content.get("recommendations", []),
                "kg_node_ids": json.loads(resource.kg_node_ids) if resource.kg_node_ids else [],
                "created_at": resource.created_at.isoformat() if resource.created_at else None,
            }

    # 如果数据库没有评估报告，实时生成
    profile = profile_service.get_profile(db, user_id)
    assessment_result = assessment_service.generate_assessment_result(
        user_id=user_id,
        profile=profile,
        db_session=db,
    )

    return {
        "status": "ok",
        "message": "实时生成评估报告",
        "assessment": assessment_result.model_dump()
    }


@router.post("/update")
async def update_learning_progress(
    req: LearningProgressUpdate,
    db: Session = Depends(get_db),
):
    """更新学习进度

    用于在学习过程中实时跟踪学习数据：
    - 学习时长增量
    - 答题结果
    - 资源使用情况

    这个API是学习效果评估系统的基础数据收集接口
    """
    success = assessment_service.update_learning_progress(
        db=db,
        user_id=req.user_id,
        knowledge_point_id=req.knowledge_point_id,
        learning_duration_increment=req.learning_duration_increment,
        answer_result=req.answer_result,
        resource_type=req.resource_type
    )

    if not success:
        raise HTTPException(status_code=500, detail="更新学习进度失败")

    return {
        "status": "ok",
        "message": "学习进度已更新",
        "user_id": req.user_id,
        "knowledge_point_id": req.knowledge_point_id,
        "updated_at": datetime.now().isoformat()
    }


@router.post("/adjust-path")
async def adjust_learning_path(
    req: PathAdjustmentRequest,
    db: Session = Depends(get_db),
):
    """动态调整学习路径

    根据评估结果自动调整学习路径：
    - 插入薄弱点学习节点
    - 调整学习顺序
    - 增加薄弱点学习时长

    返回调整后的学习路径建议
    """
    profile = profile_service.get_profile(db, req.user_id)

    # 生成评估结果（获取调整建议）
    assessment_result = assessment_service.generate_assessment_result(
        user_id=req.user_id,
        profile=profile,
        db_session=db,
    )

    # 提取路径调整建议
    adjustments = assessment_result.adjustment_recommendations

    # 根据调整类型执行不同的路径调整逻辑
    if req.adjustment_type == "auto":
        # 自动调整模式：应用所有高优先级建议
        applied_adjustments = [
            adj for adj in adjustments
            if adj.adjustment_priority in ["高", "中"]
        ]
    else:
        # 手动调整模式：返回调整建议，由用户确认
        applied_adjustments = adjustments

    return {
        "status": "ok",
        "message": f"已生成{len(adjustments)}条路径调整建议",
        "adjustment_type": req.adjustment_type,
        "total_recommendations": len(adjustments),
        "applied_adjustments": len(applied_adjustments),
        "adjustments": [adj.model_dump() for adj in applied_adjustments],
        "assessment_summary": assessment_result.assessment_summary
    }


@router.post("/realtime")
async def generate_realtime_assessment(
    req: AssessmentRequest,
    db: Session = Depends(get_db),
):
    """实时生成评估报告（不保存到数据库）

    用于快速查看当前学习状态，不持久化
    """
    profile = profile_service.get_profile(db, req.user_id)

    assessment_result = assessment_service.generate_assessment_result(
        user_id=req.user_id,
        profile=profile,
        db_session=db,
    )

    return {
        "status": "ok",
        "assessment": assessment_result.model_dump()
    }
