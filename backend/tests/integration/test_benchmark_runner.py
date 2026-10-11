"""The evaluator observes real writes/citations and does not consult its answer oracle."""

import copy
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.runner import run_case  # noqa: E402
from benchmark.schema import load_cases  # noqa: E402


async def test_runner_real_query_and_changed_oracle_cannot_change_decisions():
    case = next(case for case in load_cases() if case["case_id"] == "query_owner_weight")
    result = await run_case(case, "contract")
    assert result["passed"], result["checks"]
    assert result["observed_counts"]["metric"] == 2
    assert sum(trace["model_calls"] for trace in result["traces"]) == 2
    mutated = copy.deepcopy(case)
    mutated["expected_state"]["counts"]["metric"] = 0
    mutated["expected_answer_constraints"]["contains_all"] = ["ORACLE_LEAK_MARKER"]
    wrong = await run_case(mutated, "contract")
    assert not wrong["passed"]
    assert wrong["observed_counts"] == result["observed_counts"]
    assert sum(trace["model_calls"] for trace in wrong["traces"]) == 2


async def test_runner_replay_does_not_duplicate_real_write():
    case = next(case for case in load_cases() if case["interaction"] == "replay")
    result = await run_case(case, "contract")
    assert result["passed"], result["checks"]
    assert len(result["attempts"]) == 2
    assert len(result["traces"]) == 2
    cached = next(t for t in result["traces"] if t["task_kind"] == "cached")
    assert cached["tool_calls"] == cached["model_calls"] == 0


async def test_runner_rag_uses_actual_indexed_citations():
    case = next(
        case
        for case in load_cases()
        if case["category"] == "rag" and case["expected_evidence"]["min_citations"] > 0
    )
    result = await run_case(case, "contract")
    assert result["passed"], result["checks"]
    assert set(case["expected_evidence"]["required_document_keys"]) <= set(
        result["retrieved_document_keys"]
    )


async def test_verified_citations_reject_forged_chunk_text(settings):
    from benchmark.observation import OWNER, verified_evidence

    from app.main import create_app

    app = create_app(settings=settings)
    async with app.router.lifespan_context(app):
        await app.state.knowledge.ingest(OWNER, "fixture.txt", b"Synthetic walking diary")
        actual = (await app.state.knowledge.search(OWNER, "walking diary")).model_dump()
        observation = [{"name": "search_health_knowledge", "result": actual}]
        assert await verified_evidence(app.state.sessions, observation)
        forged = copy.deepcopy(observation)
        forged[0]["result"]["data"]["citations"][0]["text"] = "Fabricated claim"
        assert await verified_evidence(app.state.sessions, forged) == []


@pytest.mark.parametrize("kind", ["contract"])
async def test_runner_does_not_leave_temporary_databases(kind):
    root = PROJECT_ROOT / "backend"
    before = set(root.glob(".benchmark-*"))
    case = next(case for case in load_cases() if case["category"] == "missing_parameters")
    result = await run_case(case, kind)
    assert result["passed"], result["checks"]
    assert set(root.glob(".benchmark-*")) == before
