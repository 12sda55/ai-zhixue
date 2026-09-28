"""认证路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User
from ..schemas import RegisterReq, LoginReq, TokenRes, UserRes
from ..auth import _hash_password, _verify_password, create_access_token, get_current_user

router = APIRouter()

# 管理员邀请码（可按需修改或迁移到数据库）
ADMIN_INVITE_CODES = {"ADM2026", "ZHIXUE2026", "ADMIN001"}


@router.post("/register", response_model=TokenRes)
async def register(req: RegisterReq, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 管理员注册必须提供有效邀请码
    if req.role == "admin":
        if not req.invite_code or req.invite_code.strip().upper() not in ADMIN_INVITE_CODES:
            raise HTTPException(status_code=403, detail="邀请码无效，无法注册管理员账户")

    role = req.role if req.role in ("student", "admin") else "student"
    user = User(username=req.username, hashed_password=_hash_password(req.password), role=role)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.username)
    return TokenRes(access_token=token, user=UserRes(id=user.id, username=user.username, role=user.role))


@router.post("/login", response_model=TokenRes)
async def login(req: LoginReq, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not _verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(user.id, user.username)
    return TokenRes(access_token=token, user=UserRes(id=user.id, username=user.username, role=user.role))


@router.get("/me", response_model=UserRes)
async def me(user: User = Depends(get_current_user)):
    return UserRes(id=user.id, username=user.username, role=user.role)
