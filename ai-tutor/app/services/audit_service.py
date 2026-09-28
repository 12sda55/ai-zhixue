# -*- coding: utf-8 -*-
"""协同决策审计日志 — 记录每次对话的「意图 → 调度 Agent → 结果」

用途（对应榜题 XH-202630 多智能体协同决策）：
- 答辩/评审时展示协同决策的可审计性
- 为仿真评测提供真实运行数据的交叉验证
- 赛后数据分析（意图识别、调度分布、失败模式）

存储：JSONL 追加写（ai-tutor/data/decision_audit.jsonl），线程安全
"""
import json
import logging
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_AUDIT_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_AUDIT_FILE = _AUDIT_DIR / "decision_audit.jsonl"
_lock = threading.Lock()


def _ensure_file() -> None:
    _AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def record_decision(entry: dict) -> None:
    """追加一条协同决策记录（线程安全，失败不影响主流程）"""
    try:
        _ensure_file()
        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **entry,
        }
        with _lock:
            with open(_AUDIT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"审计日志写入失败: {e}")


def list_decisions(limit: int = 20, user_id: str = None) -> list[dict]:
    """读取最近 N 条决策记录（新 → 旧）"""
    if not _AUDIT_FILE.exists():
        return []
    records = []
    with open(_AUDIT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if user_id:
        records = [r for r in records if r.get("user_id") == user_id]
    return records[-limit:][::-1]


def count_decisions() -> int:
    """审计记录总数（快速统计用）"""
    if not _AUDIT_FILE.exists():
        return 0
    with open(_AUDIT_FILE, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())
