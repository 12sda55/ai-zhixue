"""ORM 模型"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(20), default="student", nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class ProfileRecord(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    data = Column(JSON, nullable=False)          # 完整 ProfileData JSON
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ResourceRecord(Base):
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    data = Column(JSON, nullable=False)          # 资源列表 JSON
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PathRecord(Base):
    __tablename__ = "paths"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    data = Column(JSON, nullable=False)          # 路径 JSON
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AssessHistory(Base):
    __tablename__ = "assess_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    score = Column(Integer, nullable=False)
    modules = Column(JSON)
    weak_points = Column(JSON)
    time_used = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())


class ProfileHistory(Base):
    __tablename__ = "profile_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(200))
    profile_data = Column(JSON, nullable=False)
    is_active = Column(Integer, default=0)  # 0=inactive, 1=active
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
