# -*- coding: utf-8 -*-
"""一键运行：虚拟用户仿真 → 系统交互 → 自动评测 → 生成报告

用法:
    python run_simulation.py            # 完整流程
    python run_simulation.py --dry      # 仅生成虚拟用户与剧本，不调用系统（先看剧本）
    python run_simulation.py --users 5  # 指定虚拟用户数

输出:
    output/simulation_report.json       全量原始数据 + 指标
    output/simulation_report.md         Markdown 摘要（可直接引用进参赛材料）
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from user_generator import generate_users, get_diversity_pairs
from runner import run_batch
from evaluator import (
    eval_intent_consistency, quality_rules, llm_judge, style_consistency, summarize,
)
from report import write_report


def main():
    parser = argparse.ArgumentParser(description="XH-202630 仿真验证框架")
    parser.add_argument("--dry", action="store_true", help="只生成剧本不调用系统")
    parser.add_argument("--users", type=int, default=None, help="虚拟用户数（覆盖配置）")
    parser.add_argument("--skip-diversity", action="store_true", help="跳过个性化差异度评测")
    args = parser.parse_args()

    n_users = args.users or config.NUM_USERS
    print(f"[1/5] 生成 {n_users} 个虚拟用户...")
    users = generate_users(n_users)
    tasks = []
    for u in users:
        for s in u["scenarios"]:
            tasks.append({
                "user_id": u["user_id"],
                "message": s["message"],
                "meta": {
                    "scenario_id": s["scenario_id"],
                    "scenario": s["name"],
                    "knowledge_point": s["knowledge_point"],
                    "expected_agents": s["expected_agents"],
                    "profile": u["profile"],
                    "style": u["profile"]["style"],
                },
            })

    # 个性化差异度对比组：同一知识点 × 不同画像
    diversity_tasks = []
    if not args.skip_diversity and config.EVAL_DIVERSITY:
        pairs = get_diversity_pairs(config.DIVERSITY_KNOWLEDGE_POINTS)
        for idx, p in enumerate(pairs):
            diversity_tasks.append({
                "user_id": f"div_user_{idx:03d}",
                "message": p["message"],
                "meta": {
                    "scenario_id": f"div-{idx}",
                    "scenario": "diversity",
                    "knowledge_point": p["knowledge_point"],
                    "expected_agents": p["expected_agents"],
                    "style": p["style"],
                },
            })

    if args.dry:
        print(f"\n共 {len(tasks)} 个剧本任务 + {len(diversity_tasks)} 个差异度任务（未调用系统）")
        for t in tasks[:6]:
            print(f"  {t['user_id']} [{t['meta']['scenario']}] {t['message'][:50]}")
        print("  ...")
        return

    all_tasks = tasks + diversity_tasks
    print(f"[2/5] 调用系统接口（共 {len(all_tasks)} 个请求，并发 {config.MAX_CONCURRENT}）...")
    t0 = time.time()
    raw = run_batch(all_tasks, max_workers=config.MAX_CONCURRENT)
    print(f"[3/5] 交互完成，耗时 {time.time() - t0:.1f}s，开始评测...")

    # 逐条评测
    records = []
    diversity_groups = []
    for item in raw:
        meta, res = item["meta"], item["result"]
        rec = {"meta": meta, "result": res}
        # A. 意图-调度一致性
        rec["intent"] = eval_intent_consistency(meta["expected_agents"], res["agent_calls"])
        # B. 生成质量
        if config.EVAL_QUALITY and res["ok"]:
            q = quality_rules(res["reply"], meta["knowledge_point"])
            j = llm_judge(res["reply"], meta["knowledge_point"]) if config.JUDGE_API_KEY else None
            q["llm_score"] = j
            rec["quality"] = q
        # B. 画像一致性（仅差异度组）
        if meta.get("scenario") == "diversity":
            style_s = style_consistency(res["reply"], meta["style"]) if res["ok"] else 0.0
            diversity_groups.append({
                "knowledge_point": meta["knowledge_point"],
                "style": meta["style"],
                "reply": res["reply"],
                "style_score": style_s,
            })
        records.append(rec)

    print("[4/5] 汇总指标...")
    summary = summarize(records, diversity_groups)
    summary["judge_enabled"] = bool(config.JUDGE_API_KEY)

    print("[5/5] 生成报告...")
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    out_json = os.path.join(config.OUTPUT_DIR, "simulation_report.json")
    out_md = os.path.join(config.OUTPUT_DIR, "simulation_report.md")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "records": records, "config": {
            "num_users": n_users, "concurrency": config.MAX_CONCURRENT,
            "api_base": config.API_BASE}}, f, ensure_ascii=False, indent=2)
    write_report(summary, records, out_md)

    # 终端打印核心指标
    print("\n===== 评测结果摘要 =====")
    print(f"端到端成功率   : {summary['success_rate']:.1%} ({summary['success_count']}/{summary['total_requests']})")
    print(f"平均响应时间   : {summary['avg_latency_s']}s")
    im = summary["intent_metrics"]
    print(f"意图-调度召回率: {im['recall_avg']}   精确率: {im['precision_avg']}   F1: {im['f1_avg']}")
    if summary.get("quality"):
        q = summary["quality"]
        print(f"生成质量分     : {q['avg_score']} (结构 {q['avg_structure']} / 长度 {q['avg_length']} / 覆盖 {q['avg_coverage']})")
    if summary.get("diversity"):
        for kp, d in summary["diversity"].items():
            print(f"差异度[{kp}]    : 平均相似度 {d['avg_similarity']}（越低=个性化越明显）")
    print(f"\n完整报告: {out_json}\nMarkdown: {out_md}")


if __name__ == "__main__":
    main()
