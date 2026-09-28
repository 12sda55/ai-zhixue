"""视频生成任务管理器

使用 Redis 追踪异步视频生成任务状态：
  pending → running → done / failed

参考 OpenMAIC 的 MediaTaskAdapter + useMediaGenerationStore 设计
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Redis不可用时使用内存字典作为降级
_memory_store: dict = {}


def _get_redis():
    """获取Redis连接，不可用返回None"""
    try:
        from app.core.config import settings
        import redis
        r = redis.Redis(
            host=getattr(settings, "REDIS_HOST", "localhost"),
            port=getattr(settings, "REDIS_PORT", 6379),
            db=getattr(settings, "REDIS_DB", 0),
            decode_responses=True,
        )
        r.ping()
        return r
    except Exception:
        return None


class VideoTaskManager:
    """视频生成任务管理器"""

    TASK_PREFIX = "video_task:"
    USER_TASKS_PREFIX = "video_user_tasks:"
    TASK_TTL = 3600 * 24  # 任务记录保留24小时

    def create_task(self, user_id: str, kp_id: str, provider: str = "seedance") -> str:
        """创建视频生成任务，返回task_id"""
        task_id = f"vt_{uuid.uuid4().hex[:12]}"
        task = {
            "task_id": task_id,
            "user_id": user_id,
            "kp_id": kp_id,
            "provider": provider,
            "status": "pending",
            "progress": 0,
            "video_url": "",
            "error": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        redis = _get_redis()
        if redis:
            pipe = redis.pipeline()
            pipe.setex(f"{self.TASK_PREFIX}{task_id}", self.TASK_TTL, json.dumps(task))
            pipe.sadd(f"{self.USER_TASKS_PREFIX}{user_id}", task_id)
            pipe.expire(f"{self.USER_TASKS_PREFIX}{user_id}", self.TASK_TTL)
            pipe.execute()
        else:
            _memory_store[task_id] = task
            user_key = f"{self.USER_TASKS_PREFIX}{user_id}"
            if user_key not in _memory_store:
                _memory_store[user_key] = set()
            _memory_store[user_key].add(task_id)

        return task_id

    def update_status(self, task_id: str, status: str, **meta):
        """更新任务状态"""
        task = self.get_task(task_id)
        if not task:
            return

        task["status"] = status
        task["updated_at"] = datetime.now().isoformat()
        task.update(meta)

        redis = _get_redis()
        if redis:
            redis.setex(f"{self.TASK_PREFIX}{task_id}", self.TASK_TTL, json.dumps(task))
        else:
            _memory_store[task_id] = task

    def get_task(self, task_id: str) -> Optional[dict]:
        """查询任务状态"""
        redis = _get_redis()
        if redis:
            data = redis.get(f"{self.TASK_PREFIX}{task_id}")
            return json.loads(data) if data else None
        else:
            return _memory_store.get(task_id)

    def get_user_tasks(self, user_id: str) -> list:
        """查询用户所有任务"""
        redis = _get_redis()
        if redis:
            task_ids = redis.smembers(f"{self.USER_TASKS_PREFIX}{user_id}")
            tasks = []
            for tid in task_ids:
                task = self.get_task(tid)
                if task:
                    tasks.append(task)
            return sorted(tasks, key=lambda t: t.get("created_at", ""), reverse=True)
        else:
            user_key = f"{self.USER_TASKS_PREFIX}{user_id}"
            task_ids = _memory_store.get(user_key, set())
            tasks = []
            for tid in task_ids:
                task = _memory_store.get(tid)
                if task:
                    tasks.append(task)
            return sorted(tasks, key=lambda t: t.get("created_at", ""), reverse=True)

    def mark_running(self, task_id: str, provider: str = ""):
        """标记任务为运行中"""
        meta = {"progress": 10}
        if provider:
            meta["provider"] = provider
        self.update_status(task_id, "running", **meta)

    def mark_done(self, task_id: str, video_url: str, duration: float = 0):
        """标记任务为完成"""
        self.update_status(task_id, "done", progress=100, video_url=video_url, duration=duration)

    def mark_failed(self, task_id: str, error: str):
        """标记任务为失败"""
        self.update_status(task_id, "failed", error=error)

    def delete_task(self, task_id: str) -> Optional[dict]:
        """删除任务记录，返回被删除的任务信息

        只能删除 done 或 failed 状态的任务，pending/running 不允许删除
        """
        task = self.get_task(task_id)
        if not task:
            return None

        # 不允许删除正在进行的任务
        if task.get("status") in ("pending", "running"):
            return None

        redis = _get_redis()
        if redis:
            user_id = task.get("user_id", "")
            pipe = redis.pipeline()
            pipe.delete(f"{self.TASK_PREFIX}{task_id}")
            if user_id:
                pipe.srem(f"{self.USER_TASKS_PREFIX}{user_id}", task_id)
            pipe.execute()
        else:
            _memory_store.pop(task_id, None)
            user_id = task.get("user_id", "")
            user_key = f"{self.USER_TASKS_PREFIX}{user_id}"
            if user_key in _memory_store:
                _memory_store[user_key].discard(task_id)

        return task


# 全局单例
video_task_manager = VideoTaskManager()
