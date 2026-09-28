"""Pydantic 请求/响应模型"""

from typing import List, Optional
from pydantic import BaseModel


# ===== Auth =====
class RegisterReq(BaseModel):
    username: str
    password: str
    role: str = "student"
    invite_code: Optional[str] = None

class LoginReq(BaseModel):
    username: str
    password: str

class UserRes(BaseModel):
    id: int
    username: str
    role: str = "student"

class TokenRes(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRes


# ===== GLM Chat =====
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatReq(BaseModel):
    messages: List[ChatMessage]
    model: str = "deepseek-v4-flash"
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = True


# ===== Data Persistence =====
class DataPutReq(BaseModel):
    data: dict

class DataGetRes(BaseModel):
    data: Optional[dict] = None
    updated_at: Optional[str] = None


# ===== Admin =====
class AdminStats(BaseModel):
    total_users: int = 0
    total_profiles: int = 0
    total_assessments: int = 0
