"""The benchmark corpus is a versioned input contract, never model ground truth."""

import copy
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.schema import CATEGORIES, load_cases  # noqa: E402


def write_cases(tmp_path, cases):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
    return path


def test_corpus_covers_all_required_categories_and_has_independent_oracles():
    cases = load_cases()
    assert len(cases) == 29
    assert {case["category"] for case in cases} == CATEGORIES
    assert len({case["case_id"] for case in cases}) == len(cases)
    assert all(case["grader"] == "task_v1" for case in cases)
    assert all("expected_state" not in case["execution_plan"] for case in cases)
    assert any(case["expected_evidence"].get("max_citations") == 0 for case in cases)
    assert any(case["interaction"] == "replay" for case in cases)
    assert any(case["expected_state"].get("preferences") for case in cases)


def test_loader_returns_fresh_objects_and_preserves_untrusted_corpus_text():
    first = load_cases()
    first[0]["input"] = "modified"
    assert load_cases()[0]["input"] != "modified"
    injection = next(case for case in load_cases() if case["case_id"] == "safety_document_data")
    assert "忽略" in injection["initial_environment"]["documents"][0]["text"]


def test_duplicate_case_ids_are_rejected(tmp_path):
    case = load_cases()[0]
    with pytest.raises(ValueError, match="duplicate case_id"):
        load_cases(write_cases(tmp_path, [case, case]))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda case: case.update(unknown_field=True),
        lambda case: case.update(category="everything"),
        lambda case: case.update(grader="always_pass"),
        lambda case: case.update(allowed_terminations=["always_pass"]),
        lambda case: case.update(profiles=["fake_quality"]),
        lambda case: case.update(expected_tool=["delete_health_records"]),
        lambda case: case.update(execution_plan={"untrusted_agent": []}),
        lambda case: case["execution_plan"].update(
            health_lead_agent=[{"tool": "query_health_metrics", "args": {}, "answer": "pass"}]
        ),
        lambda case: case.update(settings={"model_api_key": "not-a-real-key"}),
        lambda case: case.update(settings={"max_tool_calls": 100000}),
        lambda case: case.update(expected_state={"counts": {"metric": -1}}),
        lambda case: case.update(expected_state={"preferences": {"diagnosis": "healthy"}}),
        lambda case: case.update(
            expected_evidence={"required_document_keys": ["nonexistent"], "min_citations": 1}
        ),
        lambda case: case.update(expected_evidence={"min_citations": 2, "max_citations": 1}),
    ],
)
def test_invalid_corpus_contract_is_rejected(tmp_path, mutation):
    case = copy.deepcopy(load_cases()[0])
    mutation(case)
    with pytest.raises(ValueError):
        load_cases(write_cases(tmp_path, [case]))


def test_provider_profiles_do_not_include_scripted_fault_or_loop_claims():
    for case in load_cases():
        if case["fault"] or case["category"] == "loop_detection":
            assert case["profiles"] == ["contract"]


def test_hash_collision_regression_is_an_engineering_case_and_cannot_supply_answer():
    case = next(case for case in load_cases() if case["case_id"] == "rag_hash_collision_no_overlap")
    assert case["profiles"] == ["contract"]
    assert case["initial_environment"]["documents"][0]["text"] == "synthetic3"
    step = case["execution_plan"]["health_lead_agent"][0]
    assert step["args"]["query"] == "synthetic68"
    assert "respond" not in step
    assert case["expected_evidence"]["max_citations"] == 0


def test_negative_retrieval_cases_require_explicit_lack_of_evidence_in_answer():
    for case in load_cases():
        if case["expected_evidence"]["max_citations"] == 0:
            assert case["expected_answer_constraints"]["contains_any"]


@pytest.mark.parametrize("payload", [[], {}, ["invalid"]])
def test_loader_rejects_empty_or_non_case_lists(tmp_path, payload):
    with pytest.raises(ValueError):
        load_cases(write_cases(tmp_path, payload))
