# -*- coding: utf-8 -*-
"""执行器 — 调用系统对话接口，收集评测原始数据

零第三方依赖（仅标准库 urllib），并发受控，与后端 Semaphore(2) 匹配。
"""
import json
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import API_BASE, CHAT_ENDPOINT, REQUEST_TIMEOUT, MAX_CONCURRENT, USER_ID_PREFIX


def call_chat(user_id: str, message: str) -> dict:
    """调用 ai-tutor 非流式对话接口

    Returns:
        {"ok": bool, "reply": str, "agent_calls": list, "dag": dict,
         "status_bar": list, "latency_s": float, "error": str}
    """
    url = API_BASE + CHAT_ENDPOINT
    body = json.dumps({"user_id": user_id, "message": message}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "ok": True,
            "reply": data.get("reply", ""),
            "agent_calls": data.get("agent_calls", []),
            "dag": data.get("dag", {}),
            "status_bar": data.get("status_bar", []),
            "latency_s": round(time.time() - t0, 2),
            "error": "",
        }
    except urllib.error.HTTPError as e:
        return {
            "ok": False, "reply": "", "agent_calls": [], "dag": {},
            "status_bar": [], "latency_s": round(time.time() - t0, 2),
            "error": f"HTTP {e.code}: {e.read().decode('utf-8')[:200]}",
        }
    except Exception as e:
        return {
            "ok": False, "reply": "", "agent_calls": [], "dag": {},
            "status_bar": [], "latency_s": round(time.time() - t0, 2),
            "error": f"{type(e).__name__}: {e}",
        }


def run_batch(tasks: list[dict], max_workers: int = None) -> list[dict]:
    """批量执行任务列表

    Args:
        tasks: [{"user_id": str, "message": str, "meta": dict}]
        max_workers: 并发数，默认取配置 MAX_CONCURRENT

    Returns:
        [{"meta": dict, "result": dict}]  — 与输入顺序一致
    """
    max_workers = max_workers or MAX_CONCURRENT
    results = [None] * len(tasks)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {}
        for i, task in enumerate(tasks):
            fut = pool.submit(call_chat, task["user_id"], task["message"])
            future_map[fut] = i
        for fut in as_completed(future_map):
            idx = future_map[fut]
            try:
                res = fut.result()
            except Exception as e:  # 防御：线程内异常不中断整体
                res = {"ok": False, "reply": "", "agent_calls": [], "dag": {},
                       "status_bar": [], "latency_s": 0.0, "error": f"thread: {e}"}
            results[idx] = {"meta": tasks[idx]["meta"], "result": res}
    return results


if __name__ == "__main__":
    # 自测：单条请求
    r = call_chat(f"{USER_ID_PREFIX}000", "请详细讲解二叉树，最好有图示帮助理解")
    print(json.dumps(r, ensure_ascii=False, indent=2)[:600])
