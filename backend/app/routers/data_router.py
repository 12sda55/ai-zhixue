"""数据持久化路由 — profile/resources/path/assess-history"""

import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User, ProfileRecord, ResourceRecord, PathRecord, AssessHistory, ProfileHistory
from ..auth import get_current_user
from ..schemas import DataPutReq, DataGetRes

router = APIRouter()
logger = logging.getLogger(__name__)


# ===== Profile =====
@router.get("/profile", response_model=DataGetRes)
async def get_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(ProfileRecord).where(ProfileRecord.user_id == user.id))
        record = result.scalar_one_or_none()
        if not record:
            return DataGetRes(data=None)
        # ★ MySQL JSON 字段可能返回 str，需兼容处理
        data = record.data
        if isinstance(data, str):
            import json
            data = json.loads(data) if data else None
        return DataGetRes(data=data, updated_at=record.updated_at.isoformat() if record.updated_at else None)
    except Exception as e:
        logger.error("[GET /profile FAILED] %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"profile查询失败: {str(e)}")


@router.put("/profile")
async def save_profile(req: DataPutReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(ProfileRecord).where(ProfileRecord.user_id == user.id))
        record = result.scalar_one_or_none()
        if record:
            record.data = req.data
        else:
            record = ProfileRecord(user_id=user.id, data=req.data)
            db.add(record)
        await db.commit()
        return {"status": "ok"}
    except Exception as e:
        logger.error("[PUT /profile FAILED] %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"profile保存失败: {str(e)}")


# ===== Resources =====
@router.get("/resources", response_model=DataGetRes)
async def get_resources(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(ResourceRecord).where(ResourceRecord.user_id == user.id))
        record = result.scalar_one_or_none()
        if not record:
            return DataGetRes(data=None)
        # ★ MySQL JSON 字段可能返回 str，需兼容处理
        data = record.data
        if isinstance(data, str):
            import json
            data = json.loads(data) if data else None
        return DataGetRes(data=data, updated_at=record.updated_at.isoformat() if record.updated_at else None)
    except Exception as e:
        logger.error("[GET /resources FAILED] %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"resources查询失败: {str(e)}")


@router.put("/resources")
async def save_resources(req: DataPutReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ResourceRecord).where(ResourceRecord.user_id == user.id))
    record = result.scalar_one_or_none()
    if record:
        record.data = req.data
    else:
        record = ResourceRecord(user_id=user.id, data=req.data)
        db.add(record)
    await db.commit()
    return {"status": "ok"}


# ===== Path =====
@router.get("/path", response_model=DataGetRes)
async def get_path(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PathRecord).where(PathRecord.user_id == user.id))
    record = result.scalar_one_or_none()
    if not record:
        return DataGetRes(data=None)
    return DataGetRes(data=record.data, updated_at=record.updated_at.isoformat() if record.updated_at else None)


@router.put("/path")
async def save_path(req: DataPutReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PathRecord).where(PathRecord.user_id == user.id))
    record = result.scalar_one_or_none()
    if record:
        record.data = req.data
    else:
        record = PathRecord(user_id=user.id, data=req.data)
        db.add(record)
    await db.commit()
    return {"status": "ok"}


# ===== Assess History =====
@router.get("/assess-history", response_model=DataGetRes)
async def get_assess_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AssessHistory)
        .where(AssessHistory.user_id == user.id)
        .order_by(AssessHistory.created_at.desc())
        .limit(50)
    )
    records = result.scalars().all()
    if not records:
        return DataGetRes(data=None)
    data = [{
        "id": r.id, "score": r.score, "modules": r.modules,
        "weakPoints": r.weak_points, "timeUsed": r.time_used,
        "createdAt": r.created_at.isoformat() if r.created_at else None,
    } for r in records]
    return DataGetRes(data={"history": data})


@router.put("/assess-history")
async def save_assess_history(req: DataPutReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    d = req.data
    record = AssessHistory(
        user_id=user.id,
        score=d.get("score", 0),
        modules=d.get("modules"),
        weak_points=d.get("weakPoints", []),
        time_used=d.get("timeUsed", 0),
    )
    db.add(record)
    await db.commit()
    return {"status": "ok"}


# ===== Profile History =====

@router.get("/profile/history/list")
async def get_profile_history_list(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProfileHistory)
        .where(ProfileHistory.user_id == user.id)
        .order_by(ProfileHistory.created_at.desc())
        .limit(50)
    )
    records = result.scalars().all()
    histories = []
    for r in records:
        pd = r.profile_data or {}
        histories.append({
            "id": str(r.id),
            "name": r.name or "",
            "major": pd.get("major", ""),
            "grade": pd.get("grade", ""),
            "base_level": pd.get("base_level", ""),
            "weak_points_summary": "、".join(pd.get("weak_points", [])),
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "updated_at": r.updated_at.isoformat() if r.updated_at else "",
        })
    return {"success": True, "histories": histories, "total": len(histories)}


@router.post("/profile/history/save")
async def save_profile_history(req: DataPutReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    d = req.data or {}
    name = d.get("name", "")
    profile_data = d.get("profile_data", {})
    # 取消当前用户的其他活跃画像
    result = await db.execute(
        select(ProfileHistory).where(ProfileHistory.user_id == user.id, ProfileHistory.is_active == 1)
    )
    for r in result.scalars().all():
        r.is_active = 0
    record = ProfileHistory(
        user_id=user.id,
        name=name,
        profile_data=profile_data,
        is_active=1,
    )
    db.add(record)
    await db.commit()
    return {"success": True, "id": str(record.id)}


@router.get("/profile/history/{history_id}")
async def get_profile_history_detail(history_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProfileHistory).where(ProfileHistory.id == history_id, ProfileHistory.user_id == user.id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="画像历史不存在")
    return {
        "success": True,
        "profile": {
            "id": str(record.id),
            "name": record.name,
            "profile_data": record.profile_data,
            "is_active": record.is_active,
            "created_at": record.created_at.isoformat() if record.created_at else "",
        },
    }


@router.post("/profile/history/{history_id}/activate")
async def activate_profile_history(history_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # 取消所有活跃画像
    result = await db.execute(
        select(ProfileHistory).where(ProfileHistory.user_id == user.id, ProfileHistory.is_active == 1)
    )
    for r in result.scalars().all():
        r.is_active = 0
    # 激活指定画像
    result = await db.execute(
        select(ProfileHistory).where(ProfileHistory.id == history_id, ProfileHistory.user_id == user.id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="画像历史不存在")
    record.is_active = 1
    # 同时更新主 profile 记录
    profile_result = await db.execute(
        select(ProfileRecord).where(ProfileRecord.user_id == user.id)
    )
    profile_record = profile_result.scalar_one_or_none()
    if profile_record:
        profile_record.data = record.profile_data
    else:
        profile_record = ProfileRecord(user_id=user.id, data=record.profile_data)
        db.add(profile_record)
    await db.commit()
    return {"success": True}


@router.delete("/profile/history/{history_id}")
async def delete_profile_history(history_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProfileHistory).where(ProfileHistory.id == history_id, ProfileHistory.user_id == user.id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="画像历史不存在")
    if record.is_active == 1:
        raise HTTPException(status_code=400, detail="不能删除当前活跃画像")
    await db.delete(record)
    await db.commit()
    return {"success": True}


@router.get("/profile/full")
async def get_full_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProfileRecord).where(ProfileRecord.user_id == user.id)
    )
    record = result.scalar_one_or_none()
    if not record:
        return {"success": False, "profile": None}
    return {"success": True, "profile": {"profile_data": record.data}}
