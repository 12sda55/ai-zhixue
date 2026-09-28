# -*- coding: utf-8 -*-
"""报告生成 — Markdown 摘要报告（可直接引用进参赛材料"系统验证"章节）"""
import json
from datetime import datetime


def write_report(summary: dict, records: list[dict], path: str) -> None:
    lines = []
    lines.append("# 多智能体协同决策与个性化生成 — 系统自动化验证报告")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("> 验证方式：**基于仿真用户的多智能体系统自动化验证**（非真实用户教学实验）")
    lines.append("> 对应榜题：XH-202630 领域知识个性化生成与多智能体协同决策系统研究")
    lines.append("")
    lines.append("## 一、验证概述")
    lines.append("")
    lines.append(f"- 总请求数：{summary['total_requests']}")
    lines.append(f"- 端到端成功率：{summary['success_rate']:.1%}（{summary['success_count']} 成功）")
    lines.append(f"- 平均响应时间：{summary['avg_latency_s']}s（含多 Agent 并行生成）")
    lines.append(f"- LLM 辅助评测：{'启用' if summary.get('judge_enabled') else '未启用（规则评分）'}")
    lines.append("")
    lines.append("## 二、多智能体协同决策指标")
    lines.append("")
    lines.append("| 指标 | 数值 | 说明 |")
    lines.append("|------|------|------|")
    im = summary["intent_metrics"]
    lines.append(f"| 意图识别召回率 | {im['recall_avg']} | 预期调度的 Agent 被实际调度的比例 |")
    lines.append(f"| 调度精确率 | {im['precision_avg']} | 实际调度的 Agent 中符合预期的比例 |")
    lines.append(f"| F1 | {im['f1_avg']} | 召回率与精确率的调和平均 |")
    lines.append("")
    if im["top_missed"]:
        lines.append("**高频漏调度 Agent**：" + "、".join(f"{a}({c}次)" for a, c in im["top_missed"]))
    if im["top_extra"]:
        lines.append("**高频多余调度 Agent**：" + "、".join(f"{a}({c}次)" for a, c in im["top_extra"]))
    lines.append("")
    lines.append("## 三、领域知识个性化生成指标")
    lines.append("")
    if summary.get("quality"):
        q = summary["quality"]
        lines.append("| 指标 | 数值 | 说明 |")
        lines.append("|------|------|------|")
        lines.append(f"| 生成质量综合分 | {q['avg_score']} | 结构完整 + 内容长度 + 知识点覆盖 |")
        lines.append(f"| 结构完整度 | {q['avg_structure']} | Markdown 标题/列表/代码块 |")
        lines.append(f"| 内容充实度 | {q['avg_length']} | 回复长度达标比例 |")
        lines.append(f"| 知识点覆盖度 | {q['avg_coverage']} | 回复命中目标知识点比例 |")
        lines.append("")
    if summary.get("diversity"):
        lines.append("**个性化差异度**（同一知识点 × 不同认知风格画像的回复相似度，越低个性化越明显）：")
        lines.append("")
        lines.append("| 知识点 | 对比画像对数 | 平均相似度 | 视觉型一致性 | 文字型一致性 | 实践型一致性 |")
        lines.append("|--------|------------|-----------|-------------|-------------|-------------|")
        for kp, d in summary["diversity"].items():
            ps = d.get("per_style", {})
            lines.append(f"| {kp} | {d['pairs']} | {d['avg_similarity']} | {ps.get('视觉型', '-')} | {ps.get('文字型', '-')} | {ps.get('实践型', '-')} |")
        lines.append("")
    lines.append("## 四、Agent 调度分布")
    lines.append("")
    lines.append("| Agent | 调用次数 |")
    lines.append("|-------|---------|")
    for agent, cnt in summary.get("agent_call_distribution", {}).items():
        lines.append(f"| {agent} | {cnt} |")
    lines.append("")
    lines.append("---")
    lines.append("*注：本报告数据来源于仿真用户驱动的自动化评测，用于验证系统在多智能体协同决策与领域知识个性化生成方面的技术指标；不构成对真实教学效果的统计结论。*")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
