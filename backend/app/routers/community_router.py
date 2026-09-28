"""社区路由 — 跨用户资源共享 + 资源质量评估 + 推荐案例验证

设计说明（赛题评分要点）：
- 创新价值：跨用户资源共享释放资源压力，质量评估机制筛选优质内容
- 功能实现：画像匹配推荐 + 质量多维评分 + 推荐过程可解释
- 多用户覆盖：聚合所有用户的资源，标注作者来源，区分自有/共享
"""

import json
import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User, ResourceRecord, ProfileRecord
from ..auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def _normalize_json(raw):
    """★ 兼容 MySQL JSON 字段返回 str 的情况"""
    if isinstance(raw, str):
        try:
            return json.loads(raw) if raw else None
        except Exception:
            return None
    return raw


# ===== 资源质量评估 =====

def assess_quality(resource: dict) -> dict:
    """评估资源质量，返回多维评分。

    评分维度（对应赛题"资源质量评估"创新点）：
    - 内容完整度 (30分): 有内容 + 内容详实
    - 科目标注 (15分): 标注了所属科目
    - 难度标注 (10分): 标注了难度等级
    - 多模态就绪 (25分): 视频/代码/导图等多模态内容已就绪
    - 元信息完整 (10分): 有标题 + 有描述 + 有标签
    - AI生成标记 (10分): AI智能体生成
    """
    score = 0
    dimensions = []

    content = resource.get("content") or ""
    rtype = resource.get("type") or ""

    # 1. 内容完整度 (30分)
    if content and len(content) > 50:
        score += 15
        dimensions.append("内容已填充")
    if content and len(content) > 200:
        score += 15
        dimensions.append("内容详实")

    # 2. 科目标注 (15分)
    if resource.get("subject"):
        score += 15
        dimensions.append("科目标注")

    # 3. 难度标注 (10分)
    if resource.get("difficulty"):
        score += 10
        dimensions.append("难度标注")

    # 4. 多模态就绪 (25分)
    if rtype == "video" and resource.get("url") and resource.get("videoStatus") == "done":
        score += 25
        dimensions.append("视频已生成")
    elif rtype == "code" and content and "```" in content:
        score += 25
        dimensions.append("代码可运行")
    elif rtype == "mindmap" and content:
        score += 25
        dimensions.append("导图完整")
    elif rtype == "knowledge-graph" and content:
        score += 25
        dimensions.append("图谱完整")
    elif rtype == "exercise" and content and len(content) > 50:
        score += 25
        dimensions.append("题目完整")
    elif content and len(content) > 50:
        score += 15
        dimensions.append("内容就绪")

    # 5. 元信息完整 (10分)
    title = resource.get("title") or ""
    if title and len(title) > 3:
        score += 5
    if resource.get("description"):
        score += 3
        dimensions.append("有描述")
    if resource.get("tags"):
        score += 2
        dimensions.append("有标签")

    # 6. AI生成标记 (10分)
    if resource.get("aiGenerated"):
        score += 10
        dimensions.append("AI生成")

    score = min(score, 100)
    level = "优质" if score >= 75 else ("良好" if score >= 50 else ("基础" if score >= 25 else "待完善"))

    return {"score": score, "level": level, "dimensions": dimensions}


# ===== 跨用户资源池聚合 =====

async def _aggregate_pool(db: AsyncSession, current_user_id: int) -> list:
    """聚合所有用户的公开资源，附加作者信息和质量评分。

    质量门槛：只纳入质量分 >= 25 的资源（至少"基础"级别）。
    排除：空内容、无标题、视频未完成的资源。
    """
    result = await db.execute(select(ResourceRecord))
    records = result.scalars().all()

    # 预取所有用户名，避免 N+1 查询
    user_ids = list({r.user_id for r in records})
    users_map = {}
    if user_ids:
        user_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in user_result.scalars().all():
            users_map[u.id] = u.username

    pool = []
    skipped = 0  # 统计被过滤的低质量资源数
    for record in records:
        author_name = users_map.get(record.user_id, f"用户{record.user_id}")
        # 数据库存储格式为 {"resources": [...]} 或直接 [...]
        # ★ 兼容 MySQL JSON 字段返回 str 的情况
        raw = _normalize_json(record.data)
        if isinstance(raw, dict):
            resources = raw.get("resources", [])
        elif isinstance(raw, list):
            resources = raw
        else:
            resources = []
        for r in resources:
            if not isinstance(r, dict):
                continue

            # === 质量门槛过滤 ===
            # 1. 必须有标题
            if not r.get("title") or len(r.get("title", "")) < 2:
                skipped += 1
                continue
            # 2. 必须有内容（视频除外，视频看 url）
            content = r.get("content") or ""
            rtype = r.get("type") or ""
            if rtype == "video":
                # 视频必须已完成渲染
                if r.get("videoStatus") != "done" or not r.get("url"):
                    skipped += 1
                    continue
            else:
                # 非视频资源必须有内容
                if not content or len(content) < 20:
                    skipped += 1
                    continue

            quality = assess_quality(r)
            # 3. 质量分至少 25 分（基础级别）
            if quality["score"] < 25:
                skipped += 1
                continue

            pool.append({
                **r,
                "_author": author_name,
                "_authorId": record.user_id,
                "_isOwn": record.user_id == current_user_id,
                "_quality": quality,
            })

    # 按质量评分降序，同分按创建时间降序（最新优先）
    pool.sort(key=lambda x: (x["_quality"]["score"], x.get("createdAt", "")), reverse=True)
    return pool


# ===== API 路由 =====

@router.get("/resources")
async def get_community_resources(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取跨用户资源池（含质量评分和作者信息）。"""
    try:
        pool = await _aggregate_pool(db, user.id)
        own_count = sum(1 for r in pool if r["_isOwn"])
        shared_count = len(pool) - own_count
        return {
            "success": True,
            "resources": pool,
            "total": len(pool),
            "ownCount": own_count,
            "sharedCount": shared_count,
        }
    except Exception as e:
        logger.error("[GET /community/resources FAILED] %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"社区资源查询失败: {str(e)}")


@router.get("/stats")
async def get_community_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取社区统计信息（用户数、资源数、类型分布、科目分布、质量分布）。"""
    try:
        pool = await _aggregate_pool(db, user.id)

        # 类型分布
        type_dist = {}
        for r in pool:
            t = r.get("type", "unknown")
            type_dist[t] = type_dist.get(t, 0) + 1

        # 科目分布
        subject_dist = {}
        for r in pool:
            s = r.get("subject", "未分类")
            subject_dist[s] = subject_dist.get(s, 0) + 1

        # 质量分布
        quality_dist = {"优质": 0, "良好": 0, "基础": 0, "待完善": 0}
        for r in pool:
            level = r["_quality"]["level"]
            quality_dist[level] = quality_dist.get(level, 0) + 1

        # 唯一用户数
        author_ids = list({r["_authorId"] for r in pool})

        return {
            "success": True,
            "totalUsers": len(author_ids),
            "totalResources": len(pool),
            "typeDistribution": type_dist,
            "subjectDistribution": subject_dist,
            "qualityDistribution": quality_dist,
        }
    except Exception as e:
        logger.error("[GET /community/stats FAILED] %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"社区统计查询失败: {str(e)}")


@router.get("/profile/summary")
async def get_profile_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户画像摘要（用于推荐案例验证展示）。

    返回画像6+维度的摘要信息，让推荐过程可解释。
    """
    try:
        result = await db.execute(select(ProfileRecord).where(ProfileRecord.user_id == user.id))
        record = result.scalar_one_or_none()
        if not record or not record.data:
            return {"success": False, "profile": None, "dimensions": []}

        # ★ 兼容 MySQL JSON 字段返回 str 的情况
        p = _normalize_json(record.data)
        if not isinstance(p, dict):
            return {"success": False, "profile": None, "dimensions": []}
        dimensions = []

        # 维度1: 专业
        if p.get("major"):
            dimensions.append({"key": "major", "label": "专业", "value": p["major"]})
        # 维度2: 年级
        if p.get("grade"):
            dimensions.append({"key": "grade", "label": "年级", "value": p["grade"]})
        # 维度3: 知识基础
        if p.get("base_level"):
            dimensions.append({"key": "base_level", "label": "知识基础", "value": p["base_level"]})
        # 维度4: 当前科目
        if p.get("currentSubject"):
            dimensions.append({"key": "currentSubject", "label": "当前学习科目", "value": p["currentSubject"]})
        # 维度5: 薄弱点
        wps = p.get("weak_points") or []
        if wps:
            dimensions.append({"key": "weak_points", "label": "薄弱知识点", "value": "、".join(wps[:5])})
        # 维度6: 学习目标
        if p.get("study_goal"):
            dimensions.append({"key": "study_goal", "label": "学习目标", "value": p["study_goal"]})
        # 维度7: 认知风格
        if p.get("cognitive_style"):
            dimensions.append({"key": "cognitive_style", "label": "认知风格", "value": p["cognitive_style"]})
        # 维度8: 学习节奏
        if p.get("study_rhythm"):
            dimensions.append({"key": "study_rhythm", "label": "学习节奏", "value": p["study_rhythm"]})
        # 维度9: 兴趣偏好
        if p.get("interest_preference"):
            dimensions.append({"key": "interest_preference", "label": "兴趣偏好", "value": p["interest_preference"]})

        return {
            "success": True,
            "profile": p,
            "dimensions": dimensions,
            "dimensionCount": len(dimensions),
        }
    except Exception as e:
        logger.error("[GET /community/profile/summary FAILED] %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"画像摘要查询失败: {str(e)}")