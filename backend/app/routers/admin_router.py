"""管理路由"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User, ProfileRecord, AssessHistory
from ..auth import get_current_user
from ..schemas import AdminStats

router = APIRouter()


@router.get("/stats", response_model=AdminStats)
async def admin_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_profiles = (await db.execute(select(func.count(ProfileRecord.id)))).scalar() or 0
    total_assessments = (await db.execute(select(func.count(AssessHistory.id)))).scalar() or 0
    return AdminStats(total_users=total_users, total_profiles=total_profiles, total_assessments=total_assessments)


@router.get("/users")
async def list_users(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(100))
    users = result.scalars().all()
    return [{"id": u.id, "username": u.username, "createdAt": u.created_at.isoformat() if u.created_at else None} for u in users]
