"""多模态资源接口 - 对照 ai_architecture_plan.md Agent 5

完整实现：
- GET /visualization/{knowledge_point} - 获取前端可视化配置
- GET /mindmap/{knowledge_point} - 生成思维导图
- GET /time-machine/{knowledge_point} - 算法时光机步骤
- GET /comparison - 算法对比模式
- GET /videos/{knowledge_point} - B站视频推荐
- GET /cloud/{knowledge_point} - 云端视频列表
- POST /cloud - 上传云端视频
- POST /cloud/{video_id}/rate - 视频评分
- GET /code-visualization/{knowledge_point} - 代码执行可视化
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.profile_service import profile_service
from app.services.multimodal_service import multimodal_service

router = APIRouter()


class CloudVideoUpload(BaseModel):
    """云端视频上传请求"""
    title: str
    knowledge_point: str
    url: str
    duration: int = 0
    difficulty: str = "intermediate"
    tags: list[str] = Field(default_factory=list)
    user_id: str = ""


class VideoRateRequest(BaseModel):
    """视频评分请求"""
    rating: int = Field(ge=1, le=5, description="评分1-5星")
    tags: list[str] = Field(default_factory=list, description="标签评价")
    user_id: str = ""


@router.get("/visualization/{knowledge_point}")
async def get_visualization(
    knowledge_point: str,
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """获取前端可视化组件配置"""
    profile = None
    if user_id:
        profile = profile_service.get_profile(db, user_id)

    config = multimodal_service.get_visualization_config(knowledge_point)
    return {"status": "ok", "knowledge_point": knowledge_point, "config": config}


@router.get("/mindmap/{knowledge_point}")
async def get_mindmap(
    knowledge_point: str,
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """生成思维导图（Markdown格式，前端Markmap渲染）"""
    profile = None
    if user_id:
        profile = profile_service.get_profile(db, user_id)

    data = multimodal_service.generate_mind_map(knowledge_point)
    return {"status": "ok", "knowledge_point": knowledge_point, "data": data}


@router.get("/time-machine/{knowledge_point}")
async def get_time_machine(
    knowledge_point: str,
    input_data: Optional[str] = Query(None, description="自定义输入数据(逗号分隔)"),
):
    """算法时光机 - 逐步回放算法执行过程"""
    custom_input = None
    if input_data:
        try:
            custom_input = [int(x.strip()) for x in input_data.split(",")]
        except ValueError:
            try:
                custom_input = [x.strip() for x in input_data.split(",")]
            except Exception:
                custom_input = None

    steps = multimodal_service.get_time_machine_steps(knowledge_point, custom_input)
    return {"status": "ok", "knowledge_point": knowledge_point, "steps": steps}


@router.get("/comparison")
async def get_algorithm_comparison(
    algorithm1: str = Query(..., description="第一个算法知识点"),
    algorithm2: str = Query(..., description="第二个算法知识点"),
    input_data: Optional[str] = Query(None, description="自定义输入数据(逗号分隔)"),
):
    """算法对比模式 - 左右并排展示两种算法"""
    custom_input = None
    if input_data:
        try:
            custom_input = [int(x.strip()) for x in input_data.split(",")]
        except ValueError:
            custom_input = None

    comparison = multimodal_service.get_algorithm_comparison(algorithm1, algorithm2, custom_input)
    return {"status": "ok", "comparison": comparison}


@router.get("/videos/{knowledge_point}")
async def get_video_recommendations(
    knowledge_point: str,
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """B站视频推荐"""
    profile = None
    if user_id:
        profile = profile_service.get_profile(db, user_id)

    recommendations = multimodal_service.get_video_recommendations(knowledge_point)
    return {"status": "ok", "knowledge_point": knowledge_point, "recommendations": recommendations}


@router.get("/cloud/{knowledge_point}")
async def get_cloud_videos(
    knowledge_point: str,
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """获取云端视频列表（含推荐）"""
    profile = None
    if user_id:
        profile = profile_service.get_profile(db, user_id)

    if profile:
        videos = multimodal_service.get_recommended_cloud_videos(profile)
    else:
        videos = multimodal_service.get_cloud_videos(knowledge_point, db=db)

    return {"status": "ok", "knowledge_point": knowledge_point, "videos": videos}


@router.post("/cloud")
async def upload_cloud_video(video: CloudVideoUpload, db: Session = Depends(get_db)):
    """上传云端视频"""
    result = multimodal_service.add_cloud_video(
        title=video.title,
        url=video.url,
        knowledge_point=video.knowledge_point,
        uploaded_by=video.user_id,
        tags=video.tags,
        db=db,
    )
    return {"status": "ok", "video": result}


@router.post("/cloud/{video_id}/rate")
async def rate_cloud_video(video_id: str, req: VideoRateRequest, db: Session = Depends(get_db)):
    """视频评分"""
    result = multimodal_service.rate_video(
        video_id=video_id,
        rating=req.rating,
        tags=req.tags,
        user_id=req.user_id,
        db=db,
    )
    return {"status": "ok", "rating": result}


@router.get("/code-visualization/{knowledge_point}")
async def get_code_visualization(knowledge_point: str):
    """代码执行可视化配置"""
    data = multimodal_service.get_code_visualization(
        code="# 请在此输入代码",
        language="python",
    )
    return {"status": "ok", "knowledge_point": knowledge_point, "data": data}


# 保留旧接口兼容
@router.post("/generate")
async def generate_video(
    user_id: str = "",
    knowledge_point: str = "",
    style: str = "rigorous",
):
    """生成Manim概念视频（异步）- 降级为可视化配置"""
    config = multimodal_service.get_visualization_config(knowledge_point, None)
    return {"status": "ok", "task_id": "viz_config", "config": config}


@router.get("/status/{task_id}")
async def get_video_status(task_id: str):
    """查询视频生成状态"""
    return {"task_id": task_id, "status": "completed"}
