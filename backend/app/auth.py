"""JWT 认证 + 密码哈希"""

import os
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import User

SECRET = os.getenv("JWT_SECRET", "ai-learning-system-jwt-secret-2026-gold")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天

security = HTTPBearer(auto_error=False)


def _hash_password(password: str) -> str:
    """简单 SHA256 哈希 — 适合竞赛演示，生产环境应使用 bcrypt"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _verify_password(plain: str, hashed: str) -> bool:
    return _hash_password(plain) == hashed


def create_access_token(user_id: int, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    # ★ 修复：credentials 可能为 None（HTTPBearer auto_error=False）
    # 原代码直接 credentials.credentials 会抛 AttributeError → 500
    # 应返回 401 让前端引导登录
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证令牌")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """可选认证：开发环境下即使JWT无效也放行，生产环境严格校验"""
    import os
    if credentials is None:
        dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        if dev_mode:
            result = await db.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            if user:
                return user
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证令牌")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        sub = payload.get("sub", "0")
        # 尝试转int（兼容UUID格式的sub）
        try:
            user_id = int(sub)
        except ValueError:
            # UUID格式的sub → 查找用户名为sub的用户（兼容旧token）
            username = payload.get("username", "")
            if username:
                result = await db.execute(select(User).where(User.username == username))
                user = result.scalar_one_or_none()
                if user:
                    return user
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    except (JWTError, ValueError):
        dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        if dev_mode:
            # 开发模式：查找第一个用户或返回匿名用户
            result = await db.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            if user:
                return user
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user