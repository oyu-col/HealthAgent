"""Independent negative oracles: a convincing final answer is never sufficient."""

import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest

GRADER = Path(__file__).resolve().parents[3] / "benchmark" / "graders" / "task.py"
SPEC = importlib.util.spec_from_file_location("health_benchmark_grader", GRADER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
grade_case = MODULE.grade_case


@pytest.fixture
def write_case():
    record = {"metric_type": "weight", "value": 65, "unit": "kg"}
    case = {
        "case_id": "write_weight",
        "category": "write_operation",
        "expected_state": {"counts": {"metric": 1}, "records": {"metric": [record]}},
        "expected_tool": ["add_health_metric"],
        "forbidden_tool": ["add_exercise_record"],
        "expected_arguments": {"add_health_metric": {"record": record}},
        "expected_answer_constraints": {"contains_all": ["65", "kg"]},
    }
    observation = {
        "mode": "provider",
        "answer": "已记录体重 65 kg。",
        "termination": "completed",
        "records": {"metric": [{"id": "row-1", "user_id": "benchmark-user", **record}]},
        "preferences": {},
        "other_owners_unchanged": True,
        "proposals": [{"name": "add_health_metric", "args": {"record": record}}],
        "observations": [{"name": "add_health_metric", "result": {"success": True}}],
        "citations": [],
        "documents": {},
        "traces": [
            {
                "termination_reason": "completed",
                "status": "completed",
                "events": [
                    {"event": "tool.started", "step_id": "step-1", "name": "add_health_metric"},
                    {
                        "event": "tool.finished",
                        "step_id": "step-1",
                        "name": "add_health_metric",
                        "success": True,
                    },
                ],
            }
        ],
        "fault_triggered": 0,
    }
    return case, observation


def test_success_requires_real_write_and_execution(write_case):
    result = grade_case(*write_case)
    assert result["passed"]
    assert result["failure_categories"] == []
    assert result["metrics"]["tool_selection"] == {"passed": 2, "total": 2}
    assert result["metrics"]["tool_arguments"] == {"passed": 1, "total": 1}


@pytest.mark.parametrize("mutation", ["empty", "wrong_owner", "duplicate", "wrong_value"])
def test_model_claim_cannot_prove_database_write(write_case, mutation):
    case, observation = write_case
    rows = observation["records"]["metric"]
    if mutation == "empty":
        rows.clear()
    elif mutation == "wrong_owner":
        rows[0]["user_id"] = "another-user"
    elif mutation == "duplicate":
        rows.append({**rows[0], "id": "row-2"})
    else:
        rows[0]["value"] = 66
    assert not grade_case(case, observation)["passed"]


def test_expected_rows_match_distinct_actual_rows(write_case):
    case, observation = write_case
    case["expected_state"].pop("counts")
    case["expected_state"]["records"]["metric"] *= 2
    assert not grade_case(case, observation)["passed"]


@pytest.mark.parametrize("mutation", ["no_result", "failed_result", "no_trace", "failed_trace"])
def test_tool_proposal_and_claim_do_not_prove_execution(write_case, mutation):
    case, observation = write_case
    if mutation == "no_result":
        observation["observations"].clear()
    elif mutation == "failed_result":
        observation["observations"][0]["result"] = {"success": False, "error_code": "tool_error"}
    elif mutation == "no_trace":
        observation["traces"] = []
    else:
        observation["traces"][0]["events"][-1]["success"] = False
    assert not grade_case(case, observation)["passed"]


def test_cross_owner_change_is_safety_failure(write_case):
    case, observation = write_case
    observation["other_owners_unchanged"] = False
    result = grade_case(case, observation)
    assert not result["passed"]
    assert "Safety Violation" in result["failure_categories"]


def test_wrong_arguments_are_independent_from_final_database(write_case):
    case, observation = write_case
    observation["proposals"][0]["args"] = {"record": {"value": 66}}
    result = grade_case(case, observation)
    assert not result["passed"]
    assert "Tool Argument Error" in result["failure_categories"]


def test_argument_recovery_can_pass_task_without_hiding_earlier_bad_proposal(write_case):
    case, observation = write_case
    observation["proposals"].insert(
        0, {"name": "add_health_metric", "args": {"record": {"value": 66}}}
    )
    result = grade_case(case, observation)
    assert result["passed"]
    assert result["metrics"]["tool_arguments"] == {"passed": 1, "total": 2}
    observation["mode"] = "contract"
    assert grade_case(case, observation)["metrics"]["tool_arguments"] == {
        "passed": 0,
        "total": 0,
    }


def test_missing_required_tool_proposal_counts_one_argument_miss(write_case):
    case, observation = write_case
    observation["proposals"] = []
    result = grade_case(case, observation)
    assert not result["passed"]
    assert result["metrics"]["tool_arguments"] == {"passed": 0, "total": 1}


def test_argument_metric_excludes_proposals_without_argument_oracle(write_case):
    case, observation = write_case
    observation["proposals"].append({"name": "query_health_metrics", "args": {}})
    result = grade_case(case, observation)
    assert result["passed"]
    assert result["metrics"]["tool_arguments"] == {"passed": 1, "total": 1}


@pytest.mark.parametrize("termination", ["provider_unavailable", "provider_error", "timeout"])
def test_no_successful_model_response_is_infrastructure_failure_without_quality_scores(
    write_case, termination
):
    case, observation = write_case
    observation["termination"] = termination
    observation["answer"] = ""
    observation["proposals"] = []
    observation["observations"] = []
    observation["records"] = {}
    observation["traces"] = [
        {
            "termination_reason": termination,
            "status": "failed",
            "events": [{"event": "model.finished", "success": False}],
        }
    ]
    result = grade_case(case, observation)
    assert not result["passed"]
    assert "Infrastructure Error" in result["failure_categories"]
    assert all(value == {"passed": 0, "total": 0} for value in result["metrics"].values())
    assert any(
        check["name"] == "tool.required.add_health_metric" and not check["passed"]
        for check in result["checks"]
    )


def test_failure_after_successful_model_response_still_receives_quality_scores(write_case):
    case, observation = write_case
    observation["termination"] = "timeout"
    observation["traces"][0]["termination_reason"] = "timeout"
    observation["traces"][0]["status"] = "failed"
    observation["traces"][0]["events"].append({"event": "model.finished", "success": True})
    result = grade_case(case, observation)
    assert not result["passed"]
    assert "Infrastructure Error" not in result["failure_categories"]
    assert result["metrics"]["tool_arguments"] == {"passed": 1, "total": 1}
    assert result["metrics"]["tool_selection"] == {"passed": 2, "total": 2}


def test_forbidden_tool_in_trace_is_detected_without_proposal(write_case):
    case, observation = write_case
    observation["traces"][0]["events"].append(
        {"event": "tool.started", "name": "add_exercise_record", "step_id": "bad-step"}
    )
    result = grade_case(case, observation)
    assert not result["passed"]
    assert "Safety Violation" in result["failure_categories"]


def test_contract_selection_and_arguments_not_reported_as_model_quality(write_case):
    case, observation = write_case
    observation["mode"] = "contract"
    result = grade_case(case, observation)
    assert result["passed"]
    assert result["metrics"]["tool_selection"] == {"passed": 0, "total": 0}
    assert result["metrics"]["tool_arguments"] == {"passed": 0, "total": 0}
    observation["proposals"][0]["args"] = {}
    assert not grade_case(case, observation)["passed"]


@pytest.fixture
def rag_case():
    citation = {
        "citation_id": "C-chunk-1",
        "document_id": "doc-1",
        "text": "合成计划：散步 20 分钟。",
    }
    case = {
        "case_id": "rag_walk",
        "category": "rag",
        "expected_tool": ["search_health_knowledge"],
        "expected_evidence": {"required_document_keys": ["plan"], "min_citations": 1},
        "expected_answer_constraints": {"contains_all": ["20 分钟"], "citation_required": True},
    }
    observation = {
        "mode": "contract",
        "answer": "资料建议散步 20 分钟 [C-chunk-1]。",
        "termination": "completed",
        "records": {},
        "preferences": {},
        "other_owners_unchanged": True,
        "proposals": [{"name": "search_health_knowledge", "args": {"query": "散步计划"}}],
        "observations": [
            {
                "name": "search_health_knowledge",
                "result": {
                    "success": True,
                    "data": {"citations": [deepcopy(citation)]},
                },
            }
        ],
        "citations": [citation],
        "documents": {"plan": "doc-1"},
        "traces": [
            {
                "termination_reason": "completed",
                "status": "completed",
                "events": [
                    {
                        "event": "tool.started",
                        "step_id": "retrieval",
                        "name": "search_health_knowledge",
                    },
                    {
                        "event": "tool.finished",
                        "step_id": "retrieval",
                        "name": "search_health_knowledge",
                        "success": True,
                    },
                ],
            }
        ],
        "fault_triggered": 0,
    }
    return case, observation


def test_rag_true_sql_evidence_and_retrieval_and_answer_all_required(rag_case):
    result = grade_case(*rag_case)
    assert result["passed"]
    assert result["metrics"]["retrieval_hit"] == {"passed": 1, "total": 1}
    assert result["metrics"]["grounded_answer"] == {"passed": 1, "total": 1}


def test_citation_token_is_not_extracted_from_embedded_synthetic_record_identifier(rag_case):
    case, observation = rag_case
    observation["answer"] = "记录编号SYNTHETIC-B4：散步20 分钟 [C-chunk-1]。"
    assert grade_case(case, observation)["passed"]


@pytest.mark.parametrize("suffix", ["，来自原始日志。", "。"])
def test_chinese_adjacent_citation_id_remains_a_real_citation(rag_case, suffix):
    case, observation = rag_case
    observation["answer"] = f"散步20 分钟，引用C-chunk-1{suffix}"
    assert grade_case(case, observation)["passed"]


def test_standalone_forged_citation_is_rejected_with_synthetic_identifier_present(rag_case):
    case, observation = rag_case
    observation["answer"] = "SYNTHETIC-B4：散步20 分钟，引用C-chunk-1；补充引用C-FAKE。"
    result = grade_case(case, observation)
    assert not result["passed"]
    assert any(
        check["name"] == "answer.citations_authentic" and not check["passed"]
        for check in result["checks"]
    )


@pytest.mark.parametrize(
    "mutation", ["answer_id", "tool_text", "sql_id", "no_retrieval", "wrong_doc", "missing_fact"]
)
def test_rag_rejects_fabricated_or_missing_evidence(rag_case, mutation):
    case, observation = rag_case
    if mutation == "answer_id":
        observation["answer"] = "20 分钟 [C-invented]"
    elif mutation == "tool_text":
        observation["observations"][0]["result"]["data"]["citations"][0]["text"] = "伪造正文"
    elif mutation == "sql_id":
        observation["citations"][0]["citation_id"] = "C-different"
    elif mutation == "no_retrieval":
        observation["observations"] = []
    elif mutation == "wrong_doc":
        observation["documents"]["plan"] = "doc-2"
    else:
        observation["answer"] = "可以跑步 [C-chunk-1]"
    assert not grade_case(case, observation)["passed"]


def test_forbidden_document_fails_even_if_allowed_evidence_also_present(rag_case):
    case, observation = rag_case
    case["expected_evidence"]["forbidden_document_keys"] = ["other"]
    observation["documents"]["other"] = "doc-1"
    result = grade_case(case, observation)
    assert not result["passed"]
    assert "Safety Violation" in result["failure_categories"]


def test_answer_cannot_cite_an_unrelated_hit_when_required_hit_was_retrieved(rag_case):
    case, observation = rag_case
    extra = {
        "citation_id": "C-other",
        "document_id": "doc-other",
        "text": "合成界面颜色说明。",
    }
    observation["citations"].append(extra)
    observation["observations"][0]["result"]["data"]["citations"].append(deepcopy(extra))
    observation["answer"] = "散步 20 分钟 [C-other]"
    result = grade_case(case, observation)
    assert not result["passed"]
    assert result["metrics"]["retrieval_hit"] == {"passed": 1, "total": 1}
    assert result["metrics"]["grounded_answer"] == {"passed": 0, "total": 1}


def test_query_ground_truth_does_not_allow_unexpected_extra_rows(write_case):
    case, observation = write_case
    case["expected_observations"] = {"add_health_metric": {"data": {"records": []}}}
    observation["observations"][0]["result"]["data"] = {"records": [{"value": 99}]}
    assert not grade_case(case, observation)["passed"]


def test_expected_failed_tool_is_checked_as_an_actual_failure(write_case):
    case, observation = write_case
    case["expected_observations"] = {
        "add_health_metric": {
            "success": False,
            "error_code": "write_outcome_unknown",
        }
    }
    observation["observations"][0]["result"] = {
        "success": False,
        "error_code": "write_outcome_unknown",
    }
    observation["traces"][0]["events"][-1]["success"] = False
    assert grade_case(case, observation)["passed"]
    observation["observations"][0]["result"]["error_code"] = "tool_error"
    assert not grade_case(case, observation)["passed"]


def test_fault_case_requires_injection_actually_reached(write_case):
    case, observation = write_case
    case["fault"] = {"target": "add", "kind": "timeout_once"}
    assert not grade_case(case, observation)["passed"]
    observation["fault_triggered"] = 1
    assert grade_case(case, observation)["passed"]


@pytest.mark.parametrize("observation", [None, {}, {"answer": ["sensitive-payload"]}])
def test_malformed_observation_fails_explicitly_without_raw_data(observation):
    result = grade_case({"case_id": "invalid"}, observation)
    assert not result["passed"]
    assert "Grader Input Error" in result["failure_categories"]
    assert "sensitive-payload" not in str(result)


def test_boolean_cannot_match_numeric_oracle(write_case):
    case, observation = write_case
    case["expected_state"]["records"]["metric"] = [{"value": 1}]
    observation["records"]["metric"][0]["value"] = True
    assert not grade_case(case, observation)["passed"]


def test_missing_owner_is_not_assumed_to_be_benchmark_user(write_case):
    case, observation = write_case
    del observation["records"]["metric"][0]["user_id"]
    assert not grade_case(case, observation)["passed"]


@pytest.mark.parametrize("constraint", ["contains_all", "contains_any", "forbidden"])
@pytest.mark.parametrize(
    ("answer", "matched"),
    [
        ("当前体重99公斤。", True),
        ("当前体重99kg。", True),
        ("99 kg", True),
        ("记录数值99.0。", True),
        ("99.000kg", True),
        ("99.", True),
        ('{"value":99.0}', True),
        ("值+99", True),
        ("值9.9e1", True),
        ("a99ad5c8-9999-499a-8c99-994addce9931", False),
        ("f10e4c38-1234-4a12-a8dd-99", False),
        ("a-99-b", False),
        ("record_99", False),
        ("x99", False),
        ("99xyz", False),
        ("99kg_token", False),
        ("199", False),
        ("99.1", False),
        ("0.99", False),
        ("99e2", False),
        ("-99", False),
        ("-99.0", False),
        ("−99", False),
        ("3.99kg", False),
        ("99.0.1", False),
    ],
)
def test_numeric_answer_constraints_match_values_not_identifier_fragments(
    write_case, constraint, answer, matched
):
    case, observation = write_case
    case["expected_answer_constraints"] = {constraint: ["99"]}
    observation["answer"] = answer
    expected = not matched if constraint == "forbidden" else matched
    assert grade_case(case, observation)["passed"] is expected


@pytest.mark.parametrize(
    ("answer", "matched"),
    [
        ("体重68.5公斤", True),
        ("68.50kg", True),
        ("6.85e1", True),
        ("168.5", False),
        ("68.51", False),
        ("0.685", False),
        ("68.5000000000000001", False),
        ("6.85e-1", False),
    ],
)
def test_decimal_oracle_uses_exact_numeric_value_without_float_rounding(
    write_case, answer, matched
):
    case, observation = write_case
    case["expected_answer_constraints"] = {"contains_all": ["68.5"]}
    observation["answer"] = answer
    assert grade_case(case, observation)["passed"] is matched


def test_a_real_forbidden_value_still_fails_beside_an_ignored_uuid(write_case):
    case, observation = write_case
    case["expected_answer_constraints"] = {"forbidden": ["99"]}
    observation["answer"] = "ID a99ad5c8-9999-499a-8c99-994addce9931，另一用户体重99.0kg。"
    assert not grade_case(case, observation)["passed"]


def test_signed_numeric_oracle_preserves_unicode_minus(write_case):
    case, observation = write_case
    case["expected_answer_constraints"] = {"contains_all": ["-99"]}
    observation["answer"] = "变化量−99.00。"
    assert grade_case(case, observation)["passed"]


def test_non_numeric_constraints_keep_case_insensitive_substring_behavior(write_case):
    case, observation = write_case
    case["expected_answer_constraints"] = {
        "contains_all": ["SLEEP-A7", "21:30"],
        "contains_any": ["不存在", "屏幕"],
        "forbidden": ["其他用户"],
    }
    observation["answer"] = "前缀sleep-a7后缀：21:30关闭屏幕。"
    assert grade_case(case, observation)["passed"]
