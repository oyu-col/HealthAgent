"""Metrics with explicit denominators; compare frozen protocols, never invented gains."""

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean, pstdev


def ratio(passed, total):
    return {"passed": passed, "total": total, "value": passed / total if total else None}


def distribution(values):
    return {
        "n": len(values),
        "mean": mean(values) if values else None,
        "stddev": pstdev(values) if values else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def summarize(results):
    metrics = {"task_success": ratio(sum(r["passed"] for r in results), len(results))}
    for name in ("tool_selection", "tool_arguments", "retrieval_hit", "grounded_answer"):
        rows = [r.get("metrics", {}).get(name, {}) for r in results]
        metrics[name] = ratio(
            sum(r.get("passed", 0) for r in rows), sum(r.get("total", 0) for r in rows)
        )
    attempts = [
        event
        for row in results
        for trace in row.get("traces", [])
        for event in trace.get("events", [])
        if event.get("event") == "tool.finished"
    ]
    metrics["tool_execution"] = ratio(
        sum(e.get("success") is True for e in attempts), len(attempts)
    )
    starts = sum(
        event.get("event") == "tool.started"
        for row in results
        for trace in row.get("traces", [])
        for event in trace.get("events", [])
    )
    metrics["tool_terminal_coverage"] = ratio(len(attempts), starts)
    eligible = [r for r in results if r.get("recovery_eligible") and r.get("fault_triggered", 0)]
    metrics["recovery"] = ratio(sum(r["passed"] for r in eligible), len(eligible))
    metrics["loop"] = ratio(sum(r["termination"] == "no_progress" for r in results), len(results))
    normal = [r for r in results if r["category"] != "loop_detection"]
    metrics["unexpected_loop"] = ratio(
        sum(r["termination"] == "no_progress" for r in normal), len(normal)
    )
    for label, key in (("tool_calls", "tool_calls"), ("agent_steps", "total_steps")):
        values = []
        for row in results:
            traces = row.get("traces", [])
            if traces and all(
                t.get("capture_complete") and isinstance(t.get(key), int) for t in traces
            ):
                values.append(sum(t[key] for t in traces))
        metrics[label] = distribution(values)
    metrics["latency_ms"] = distribution([r["latency_ms"] for r in results])
    metrics["agent_latency_ms"] = distribution(
        [
            sum(trace["latency_ms"] for trace in row["traces"])
            for row in results
            if row.get("traces")
            and all(isinstance(trace.get("latency_ms"), (int, float)) for trace in row["traces"])
        ]
    )
    reported_tokens = [
        trace.get("token_usage", {}).get("total_tokens")
        for row in results
        for trace in row.get("traces", [])
        if trace.get("token_usage", {}).get("total_tokens") is not None
    ]
    metrics["token_usage"] = {
        "reported_total": sum(reported_tokens) if reported_tokens else None,
        "complete": bool(results)
        and all(row.get("traces") for row in results)
        and all(
            t.get("token_usage", {}).get("complete") for r in results for t in r.get("traces", [])
        ),
    }
    categories = Counter(
        category for row in results for category in row.get("failure_categories", [])
    )
    by_category = {}
    for name in sorted({r["category"] for r in results}):
        rows = [r for r in results if r["category"] == name]
        by_category[name] = ratio(sum(r["passed"] for r in rows), len(rows))
    return {"metrics": metrics, "failure_categories": dict(categories), "by_category": by_category}


def markdown(report):
    lines = [
        "# HealthAgent 基准运行报告",
        "",
        f"模式：`{report['manifest']['mode']}`。",
        "",
        "contract 为脚本化工程契约验证，不能衡量自然语言规划；provider 才实际调用配置模型。",
        "固定事实/引用规则是 groundedness 代理指标，不是医学正确性评分。",
        "latency_ms 为含建库/种子准备的案例耗时；agent_latency_ms 来自持久 Trace。",
        "tool_execution 仅统计已观测终态的工具尝试，tool_terminal_coverage 显示终态可见比例。",
        "",
        "| 指标 | 实际结果 | 分母/样本数 |",
        "| --- | --- | --- |",
    ]
    for name, value in report["summary"]["metrics"].items():
        if "value" in value:
            shown = "N/A" if value["value"] is None else f"{value['value']:.2%}"
            lines.append(f"| {name} | {shown} | {value['passed']} / {value['total']} |")
        elif "mean" in value:
            shown = (
                "N/A"
                if value["mean"] is None
                else f"{value['mean']:.3f}（标准差 {value['stddev']:.3f}）"
            )
            lines.append(f"| {name} | {shown} | {value['n']} |")
    lines += [
        "",
        "## 各任务真实结果",
        "",
        "| 案例 | 次数 | 通过 | 终态 | 失败检查 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in report["results"]:
        failed = "; ".join(c["name"] for c in result.get("checks", []) if not c["passed"])
        lines.append(
            f"| {result['case_id']} | {result['repeat']} | {result['passed']} "
            f"| {result['termination']} | {failed.replace('|', '/')} |"
        )
    lines += [
        "",
        "完整摘要、源码/用例/判分器指纹和脱敏 Trace 见同目录 report.json。",
        "失败没有从分母排除；未知 token/不完整 Trace 不当作零。"
        "原始回答/参数只在临时评测内存中判分，不写此报告。",
        "",
    ]
    return "\n".join(lines)


def compare(before, after):
    if not before["manifest"].get("completed") or not after["manifest"].get("completed"):
        raise ValueError("Cannot compare incomplete runs")
    keys = (
        "schema_version",
        "python",
        "dependencies",
        "mode",
        "case_digest",
        "grader_digest",
        "protocol_digest",
        "settings_digest",
        "selected_cases",
        "repeats",
        "seed",
    )
    for report in (before, after):
        manifest = report["manifest"]
        for key in keys:
            if key not in manifest or manifest[key] is None:
                raise ValueError("Missing comparison provenance: " + key)
        for key in (
            "case_digest",
            "grader_digest",
            "protocol_digest",
            "settings_digest",
            "app_digest",
        ):
            if not isinstance(manifest.get(key), str) or not manifest[key]:
                raise ValueError("Missing comparison fingerprint: " + key)
        selected = manifest["selected_cases"]
        repeats = manifest["repeats"]
        if (
            not selected
            or len(selected) != len(set(selected))
            or type(repeats) is not int
            or repeats < 1
        ):
            raise ValueError("Invalid sample manifest")
        expected = {(case_id, repeat) for case_id in selected for repeat in range(1, repeats + 1)}
        actual = [(row["case_id"], row["repeat"]) for row in report["results"]]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ValueError("Duplicate, missing or unexpected result samples")
    mismatches = [key for key in keys if before["manifest"].get(key) != after["manifest"].get(key)]
    if mismatches:
        raise ValueError("Incomparable experiment fields: " + ", ".join(mismatches))
    old = {(r["case_id"], r["repeat"]): r for r in before["results"]}
    new = {(r["case_id"], r["repeat"]): r for r in after["results"]}
    if old.keys() != new.keys():
        raise ValueError("Incomparable result samples")
    return {
        "comparable": True,
        "mode": before["manifest"]["mode"],
        "baseline_app_digest": before["manifest"]["app_digest"],
        "candidate_app_digest": after["manifest"]["app_digest"],
        "improved": [list(key) for key in old if not old[key]["passed"] and new[key]["passed"]],
        "regressed": [list(key) for key in old if old[key]["passed"] and not new[key]["passed"]],
        "unchanged_failures": [
            list(key) for key in old if not old[key]["passed"] and not new[key]["passed"]
        ],
        "baseline": before["summary"],
        "candidate": after["summary"],
        "interpretation": (
            "Paired synthetic tasks; provider stochastic variation remains. No clinical validation."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare(
        json.loads(args.baseline.read_text(encoding="utf-8")),
        json.loads(args.candidate.read_text(encoding="utf-8")),
    )
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {
                key: result[key]
                for key in ("comparable", "mode", "improved", "regressed", "unchanged_failures")
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
