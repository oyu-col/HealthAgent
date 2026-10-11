"""Reject incomparable/incomplete experiments and preserve failed real samples."""

import copy
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.report import compare, markdown, summarize  # noqa: E402


def trace(*, complete=True, tool_calls=2, success=(True, False), tokens=15):
    return {
        "capture_complete": complete,
        "tool_calls": tool_calls,
        "total_steps": tool_calls + 2,
        "events": [{"event": "tool.finished", "success": value} for value in success]
        + [{"event": "model.finished", "success": True}],
        "token_usage": {"total_tokens": tokens, "complete": tokens is not None},
    }


def result(case_id="case_a", repeat=1, passed=True, *, traces=None):
    return {
        "case_id": case_id,
        "repeat": repeat,
        "category": "single_tool_query",
        "passed": passed,
        "termination": "completed" if passed else "harness_error",
        "latency_ms": 25,
        "traces": [trace()] if traces is None else traces,
        "checks": [{"name": "independent_state_check", "passed": passed}],
        "failure_categories": [] if passed else ["Harness Error"],
        "metrics": {},
    }


def report(rows=None):
    rows = rows if rows is not None else [result()]
    return {
        "manifest": {
            "schema_version": 1,
            "completed": True,
            "mode": "contract",
            "case_digest": "case-v1",
            "grader_digest": "grader-v1",
            "protocol_digest": "protocol-v1",
            "settings_digest": "config-v1",
            "app_digest": "source-v1",
            "selected_cases": sorted({row["case_id"] for row in rows}),
            "repeats": max(row["repeat"] for row in rows),
            "seed": 3,
            "python": "3.12.10",
            "dependencies": {"langchain": "1.3.0", "langgraph": "1.2.0"},
        },
        "results": rows,
        "summary": summarize(rows),
    }


def test_execution_accuracy_uses_actual_tool_finished_events():
    rows = [result()]
    rows[0]["traces"][0]["events"].extend(
        [
            {"type": "tool.finished", "success": True},
            {"event": "tool.started", "success": True},
        ]
    )
    metrics = summarize(rows)["metrics"]
    assert metrics["tool_execution"] == {"passed": 1, "total": 2, "value": 0.5}
    assert metrics["tool_calls"]["mean"] == 2
    assert metrics["agent_steps"]["mean"] == 4


def test_not_applicable_metrics_have_null_denominators_including_empty_run():
    metrics = summarize([])["metrics"]
    for name in (
        "task_success",
        "tool_selection",
        "tool_arguments",
        "tool_execution",
        "retrieval_hit",
        "grounded_answer",
        "recovery",
        "loop",
        "unexpected_loop",
    ):
        assert metrics[name] == {"passed": 0, "total": 0, "value": None}
    assert metrics["agent_steps"]["mean"] is None
    assert metrics["token_usage"]["reported_total"] is None
    assert metrics["token_usage"]["complete"] is False


def test_harness_failure_stays_in_success_and_category_denominators_and_markdown():
    rows = [result(), result("case_b", passed=False, traces=[])]
    current = report(rows)
    assert current["summary"]["metrics"]["task_success"]["value"] == 0.5
    assert current["summary"]["by_category"]["single_tool_query"]["total"] == 2
    assert current["summary"]["failure_categories"] == {"Harness Error": 1}
    rendered = markdown(current)
    assert "case_b" in rendered and "harness_error" in rendered
    assert "independent_state_check" in rendered


def test_missing_trace_is_unknown_usage_not_complete_zero():
    metrics = summarize([result(traces=[])])["metrics"]
    assert metrics["token_usage"] == {"reported_total": None, "complete": False}
    assert metrics["tool_calls"]["n"] == 0
    assert metrics["tool_execution"]["value"] is None


def test_partial_usage_and_incomplete_trace_do_not_become_zero_observations():
    rows = [result(), result("case_b", traces=[trace(complete=False, tokens=None)])]
    metrics = summarize(rows)["metrics"]
    assert metrics["token_usage"] == {"reported_total": 15, "complete": False}
    assert metrics["tool_calls"]["n"] == 1
    assert metrics["tool_calls"]["mean"] == 2


def test_only_triggered_faults_enter_recovery_rate_and_intentional_loops_are_separate():
    recovered = result()
    recovered.update(recovery_eligible=True, fault_triggered=1)
    untriggered = result("case_b", passed=False)
    untriggered.update(recovery_eligible=True, fault_triggered=0)
    intentional = result("case_c")
    intentional.update(category="loop_detection", termination="no_progress")
    metrics = summarize([recovered, untriggered, intentional])["metrics"]
    assert metrics["recovery"] == {"passed": 1, "total": 1, "value": 1}
    assert metrics["loop"]["passed"] == 1
    assert metrics["unexpected_loop"] == {"passed": 0, "total": 2, "value": 0}


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("mode", "provider"),
        ("case_digest", "other-cases"),
        ("grader_digest", "other-grader"),
        ("protocol_digest", "other-protocol"),
        ("settings_digest", "other-config"),
        ("selected_cases", ["other-case"]),
        ("repeats", 2),
        ("seed", 9),
        ("schema_version", 2),
        ("python", "3.13.0"),
        ("dependencies", {"langchain": "9.9.0"}),
    ],
)
def test_compare_rejects_incomparable_protocol_or_runtime(field, changed):
    baseline = report()
    candidate = copy.deepcopy(baseline)
    candidate["manifest"][field] = changed
    with pytest.raises(ValueError):
        compare(baseline, candidate)


@pytest.mark.parametrize("side", ["baseline", "candidate"])
def test_compare_rejects_explicitly_incomplete_runs(side):
    reports = {"baseline": report(), "candidate": report()}
    reports[side]["manifest"]["completed"] = False
    with pytest.raises(ValueError, match="incomplete"):
        compare(reports["baseline"], reports["candidate"])


def test_comparison_pairs_case_and_repeat_instead_of_averaging_away_regressions():
    baseline = report(
        [result("case_a", 1, False), result("case_a", 2), result("case_b", 1), result("case_b", 2)]
    )
    candidate = report(
        [result("case_b", 2), result("case_a", 2, False), result("case_b", 1), result("case_a", 1)]
    )
    candidate["manifest"]["app_digest"] = "source-v2"
    compared = compare(baseline, candidate)
    assert compared["improved"] == [["case_a", 1]]
    assert compared["regressed"] == [["case_a", 2]]
    assert compared["unchanged_failures"] == []
    assert compared["baseline"]["metrics"]["task_success"]["value"] == 0.75
    assert compared["candidate"]["metrics"]["task_success"]["value"] == 0.75


def test_compare_rejects_duplicate_samples_instead_of_silently_overwriting():
    duplicate = report([result(), result()])
    with pytest.raises(ValueError):
        compare(duplicate, copy.deepcopy(duplicate))


def test_compare_rejects_both_runs_missing_the_same_declared_sample():
    partial = report([result("case_a", 1), result("case_a", 2), result("case_b", 1)])
    assert partial["manifest"]["selected_cases"] == ["case_a", "case_b"]
    assert partial["manifest"]["repeats"] == 2
    with pytest.raises(ValueError):
        compare(partial, copy.deepcopy(partial))


def test_compare_rejects_samples_not_selected_in_manifest():
    unexpected = report([result(), result("case_b")])
    unexpected["manifest"]["selected_cases"] = ["case_a"]
    with pytest.raises(ValueError):
        compare(unexpected, copy.deepcopy(unexpected))


@pytest.mark.parametrize("field", ["grader_digest", "protocol_digest", "settings_digest"])
def test_compare_rejects_missing_fingerprints_even_when_both_manifests_omit_them(field):
    missing = report()
    missing["manifest"].pop(field)
    with pytest.raises(ValueError):
        compare(missing, copy.deepcopy(missing))
