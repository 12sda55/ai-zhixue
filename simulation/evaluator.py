# -*- coding: utf-8 -*-
"""评测器 — 多智能体协同决策 + 领域知识个性化生成的自动化指标计算

指标体系（对应榜题 XH-202630 两大主题）：
A. 多智能体协同决策：
   A1 意图识别准确率  = 命中预期Agent数 / 预期Agent数（召回视角）
   A2 调度精确率      = 命中预期Agent数 / 实际调度Agent数（精确视角）
   A3 端到端成功率    = 无错误响应的请求占比
   A4 决策延迟        = 平均响应时间
B. 领域知识个性化生成：
   B1 个性化差异度    = 同知识点不同画像下，回复文本的字符 n-gram 相似度（越低越个性化）
   B2 生成质量分      = 规则评分(0-1)：结构完整性 + 长度充足 + 知识点覆盖
   B3 画像一致性      = 请求带认知风格提示时，回复是否体现相应特征（如视觉型含图示/类比词）
"""
import json
import re
import urllib.request
from config import EVAL_QUALITY, EVAL_DIVERSITY, JUDGE_API_KEY, JUDGE_BASE_URL, JUDGE_MODEL

# ---------- 通用工具 ----------

def char_ngrams(text: str, n: int = 2) -> set:
    """字符 n-gram（中文场景下比词级别更稳健）"""
    text = re.sub(r"\s+", "", text or "")
    if len(text) <= n:
        return {text}
    return {text[i:i + n] for i in range(len(text) - n + 1)}


def jaccard_sim(a: str, b: str, n: int = 2) -> float:
    """字符 n-gram Jaccard 相似度 [0,1]"""
    ga, gb = char_ngrams(a, n), char_ngrams(b, n)
    if not ga or not gb:
        return 0.0
    inter = len(ga & gb)
    union = len(ga | gb)
    return inter / union if union else 0.0


# ---------- A. 多智能体协同决策指标 ----------

def eval_intent_consistency(expected: list[str], actual: list[str]) -> dict:
    """预期 Agent 集合 vs 实际调度 Agent 集合的一致性"""
    exp_set, act_set = set(expected), set(actual)
    if not exp_set:
        return {"recall": 0.0, "precision": 0.0, "f1": 0.0, "missed": [], "extra": []}
    hit = len(exp_set & act_set)
    recall = hit / len(exp_set)
    precision = hit / len(act_set) if act_set else 0.0
    f1 = 2 * recall * precision / (recall + precision) if (recall + precision) > 0 else 0.0
    return {
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "f1": round(f1, 3),
        "missed": sorted(exp_set - act_set),
        "extra": sorted(act_set - exp_set),
    }


def aggregate_intent_metrics(records: list[dict]) -> dict:
    """汇总所有请求的意图-调度一致性"""
    recalls, precisions, f1s = [], [], []
    miss_counts, extra_counts = {}, {}
    for r in records:
        m = r["intent"]
        recalls.append(m["recall"])
        precisions.append(m["precision"])
        f1s.append(m["f1"])
        for a in m["missed"]:
            miss_counts[a] = miss_counts.get(a, 0) + 1
        for a in m["extra"]:
            extra_counts[a] = extra_counts.get(a, 0) + 1
    return {
        "recall_avg": round(sum(recalls) / len(recalls), 3) if recalls else 0,
        "precision_avg": round(sum(precisions) / len(precisions), 3) if precisions else 0,
        "f1_avg": round(sum(f1s) / len(f1s), 3) if f1s else 0,
        "top_missed": sorted(miss_counts.items(), key=lambda x: -x[1])[:5],
        "top_extra": sorted(extra_counts.items(), key=lambda x: -x[1])[:5],
    }


# ---------- B. 个性化生成指标 ----------

def quality_rules(reply: str, kp: str) -> dict:
    """规则质量评分（不依赖外部LLM，保证可复现）

    维度：
    1. 结构完整性：Markdown 标题/列表/代码块等结构标记
    2. 长度充足性：回复长度达到教学讲解的最低要求
    3. 知识点覆盖：回复中是否出现知识点相关关键词
    """
    reply = reply or ""
    score_parts = {}
    # 1. 结构完整性
    has_heading = bool(re.search(r"#{1,4}\s", reply))
    has_list = bool(re.search(r"(^|\n)\s*[-*]\s|\d+\.\s", reply))
    has_code = bool(re.search(r"```|`[^`]+`", reply))
    structure = 0.3 * has_heading + 0.3 * has_list + 0.4 * has_code
    # 2. 长度充足性（中文 400 字起）
    length = min(1.0, len(reply) / 800.0)
    # 3. 知识点覆盖：抽取 kp 的字符（取前 2 个字符防匹配过严），要求出现
    kp_key = kp[:2]
    coverage = 1.0 if (kp_key and kp_key in reply) else 0.0
    score = round(0.4 * structure + 0.3 * length + 0.3 * coverage, 3)
    return {"score": score, "structure": round(structure, 3),
            "length": round(length, 3), "coverage": coverage}


def llm_judge(reply: str, kp: str) -> float:
    """LLM-as-Judge：用外部大模型对生成内容 1-5 打分（可选，需配置 JUDGE_API_KEY）"""
    if not JUDGE_API_KEY:
        return None
    prompt = (
        f"请对下面这段关于「{kp}」的教学讲解打分（1-5整数），"
        "评分标准：内容准确性、结构清晰度、讲解深度。只输出数字。\n\n" + reply[:2000]
    )
    body = json.dumps({
        "model": JUDGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 10, "stream": False,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        JUDGE_BASE_URL + "/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + JUDGE_API_KEY},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"].strip()
            m = re.search(r"[1-5]", content)
            return int(m.group(0)) / 5.0 if m else None
    except Exception:
        return None


# 画像一致性检测：视觉型 → 图示/类比词；文字型 → 公式/推导词；实践型 → 代码/应用词
STYLE_MARKERS = {
    "视觉型": ["图", "示", "类比", "示意", "示意", "表格", "结构"],
    "文字型": ["推导", "证明", "定理", "公式", "定义", "因为", "所以"],
    "实践型": ["代码", "示例", "实现", "运行", "应用", "场景", "调试"],
}


def style_consistency(reply: str, style: str) -> float:
    """回复是否体现认知风格特征：命中标记词占比"""
    markers = STYLE_MARKERS.get(style, [])
    if not markers:
        return 0.0
    hit = sum(1 for m in markers if m in (reply or ""))
    return round(hit / len(markers), 3)


# ---------- 汇总 ----------

def summarize(records: list[dict], diversity_groups: list[dict]) -> dict:
    """生成完整评测报告数据结构"""
    ok = [r for r in records if r["result"]["ok"]]
    report = {
        "total_requests": len(records),
        "success_count": len(ok),
        "success_rate": round(len(ok) / len(records), 3) if records else 0,
        "avg_latency_s": round(sum(r["result"]["latency_s"] for r in ok) / len(ok), 2) if ok else 0,
        "agent_call_distribution": _agent_distribution(records),
        "intent_metrics": aggregate_intent_metrics(records),
        "quality": {},
        "diversity": {},
    }
    if EVAL_QUALITY and ok:
        qs = [r["quality"] for r in ok if r.get("quality")]
        if qs:
            report["quality"] = {
                "avg_score": round(sum(q["score"] for q in qs) / len(qs), 3),
                "avg_structure": round(sum(q["structure"] for q in qs) / len(qs), 3),
                "avg_length": round(sum(q["length"] for q in qs) / len(qs), 3),
                "avg_coverage": round(sum(q["coverage"] for q in qs) / len(qs), 3),
            }
    if EVAL_DIVERSITY and diversity_groups:
        report["diversity"] = _diversity_summary(diversity_groups)
    return report


def _agent_distribution(records: list[dict]) -> dict:
    dist = {}
    for r in records:
        for a in r["result"]["agent_calls"]:
            dist[a] = dist.get(a, 0) + 1
    return dict(sorted(dist.items(), key=lambda x: -x[1]))


def _diversity_summary(groups: list[dict]) -> dict:
    """同一知识点不同画像的回复相似度（越低=个性化差异越明显）"""
    by_kp = {}
    for g in groups:
        by_kp.setdefault(g["knowledge_point"], []).append(g)
    result = {}
    for kp, items in by_kp.items():
        replies = [g["reply"] for g in items if g.get("reply")]
        if len(replies) < 2:
            result[kp] = {"pairs": 0, "avg_similarity": None}
            continue
        sims = []
        for i in range(len(replies)):
            for j in range(i + 1, len(replies)):
                sims.append(jaccard_sim(replies[i], replies[j]))
        result[kp] = {
            "pairs": len(sims),
            "avg_similarity": round(sum(sims) / len(sims), 3),
            "per_style": {g["style"]: g.get("style_score", 0) for g in items},
        }
    return result
