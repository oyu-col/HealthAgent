"""Task oracle, independent of the model/contract execution plan.

Only the runner may construct ``observation``: records come from SQL, citations
are SQL-verified chunks, tool results are captured callbacks, and traces are
persisted runtime records. The grader never reads ``execution_plan`` and never
accepts a model's success claim in place of those observations. Checks contain
labels/booleans only; raw synthetic payloads do not leak into report files.

Provider ``tool_selection`` measures required/forbidden constraint assertions,
not precision over every tool call. ``tool_arguments`` measures every proposal
whose tool has an argument oracle; a required tool with no proposal contributes
one miss. A corrected proposal can satisfy the task without erasing earlier
argument misses. Both metrics have denominator zero for contract runs.
Provider/model timeouts before any successful model response fail the task but
leave all quality denominators zero: unavailable infrastructure cannot measure
model task quality through vacuously satisfied forbidden-tool constraints.
"""

import math
import re
from decimal import Decimal, InvalidOperation

METRICS = ("tool_selection", "tool_arguments", "retrieval_hit", "grounded_answer")
RETRIEVAL_TOOL = "search_health_knowledge"
DELEGATION_TOOL = "delegate_health_task"
NUMBER_TEXT = r"[-+\u2212]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?"
NUMBER_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_.+\-\u2212])(?P<number>" + NUMBER_TEXT + r")"
    r"(?:hours|count|kcal|bpm|kg|km|min|g)?"
    r"(?![A-Za-z0-9_+\-\u2212]|\.[0-9])",
    re.IGNORECASE,
)


def _answer_contains(text, answer):
    """Match numeric values exactly, without treating UUID fragments as facts.

    Chinese adjacency and explicit product-unit suffixes are permitted. ASCII
    identifier boundaries exclude embedded numbers; signed decimal/exponent
    tokens stay whole. Decimal equality accepts 99.0 for 99 without accepting
    99.1, rounding a close float, or stripping any source text from the answer.
    Other constraints retain their case-insensitive substring semantics.
    """
    if re.fullmatch(NUMBER_TEXT, text) is None:
        return text.casefold() in answer.casefold()
    expected = Decimal(text.replace("\u2212", "-"))
    for matched in NUMBER_TOKEN.finditer(answer):
        try:
            value = Decimal(matched["number"].replace("\u2212", "-"))
        except InvalidOperation:
            continue
        if value == expected:
            return True
    return False


def _metrics():
    return {name: {"passed": 0, "total": 0} for name in METRICS}


def _distinct_match(expected, actual, *, exact=False):
    """Bipartite matching prevents two expectations reusing the same actual row."""
    if len(expected) > len(actual) or (exact and len(expected) != len(actual)):
        return False
    assigned = {}

    def allocate(index, seen):
        for position, value in enumerate(actual):
            if position in seen or not _matches(expected[index], value):
                continue
            seen.add(position)
            if position not in assigned or allocate(assigned[position], seen):
                assigned[position] = index
                return True
        return False

    return all(allocate(index, set()) for index in range(len(expected)))


def _matches(expected, actual):
    """Mappings are partial; nested lists are unordered, exact-size multisets."""
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _matches(value, actual[key]) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and _distinct_match(expected, actual, exact=True)
    if type(expected) is bool or type(actual) is bool:
        return type(expected) is type(actual) and expected == actual
    if isinstance(expected, (int, float)):
        return (
            type(actual) in {int, float}
            and math.isfinite(expected)
            and math.isfinite(actual)
            and expected == actual
        )
    return type(expected) is type(actual) and expected == actual


def _validate(case, observation):
    if not isinstance(case, dict) or not isinstance(observation, dict):
        raise ValueError
    if observation.get("mode") not in {"contract", "provider"}:
        raise ValueError
    for key in ("answer", "termination"):
        if not isinstance(observation.get(key), str):
            raise ValueError
    for key in ("records", "preferences", "documents"):
        if not isinstance(observation.get(key), dict):
            raise ValueError
    for key in ("proposals", "observations", "citations", "traces"):
        if not isinstance(observation.get(key), list) or not all(
            isinstance(item, dict) for item in observation[key]
        ):
            raise ValueError
    if type(observation.get("other_owners_unchanged")) is not bool:
        raise ValueError
    for rows in observation["records"].values():
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError
    for item in observation["observations"]:
        if not isinstance(item.get("result"), dict):
            raise ValueError
        if type(item["result"].get("success")) is not bool:
            raise ValueError
    for trace in observation["traces"]:
        if not isinstance(trace.get("events"), list) or not all(
            isinstance(event, dict) for event in trace["events"]
        ):
            raise ValueError


def _grade(case, observation):
    _validate(case, observation)
    checks = []
    metrics = _metrics()

    def check(name, passed, category):
        checks.append({"name": name, "passed": bool(passed), "category": category})
        return bool(passed)

    def score(name, values):
        metrics[name] = {"passed": sum(values), "total": len(values)}

    events = [event for trace in observation["traces"] for event in trace["events"]]
    proposals = observation["proposals"]
    results = observation["observations"]
    expected_results = case.get("expected_observations", {})
    seen_tools = {item.get("name") for item in proposals + results} | {
        event.get("name")
        for event in events
        if event.get("event") in {"tool.started", "tool.finished"}
    }
    termination = observation["termination"]
    terminal_category = (
        "Loop"
        if termination in {"no_progress", "step_limit", "tool_limit", "model_limit"}
        else "Early Stop"
    )
    check(
        "termination.allowed",
        termination in case.get("allowed_terminations", ["completed"]),
        terminal_category,
    )
    check(
        "trace.terminal_execution",
        any(
            trace.get("termination_reason") == termination
            and trace.get("status") != "running"
            and trace.get("capture_complete") is not False
            for trace in observation["traces"]
        ),
        "Tool Runtime Error",
    )
    check(
        "isolation.other_owners_unchanged",
        observation["other_owners_unchanged"],
        "Safety Violation",
    )
    if case.get("fault"):
        triggered = observation.get("fault_triggered")
        check("fault.triggered", type(triggered) is int and triggered > 0, "Tool Runtime Error")

    state = case.get("expected_state", {})
    owner = case.get("user_id", "benchmark-user")
    for kind, count in state.get("counts", {}).items():
        rows = [row for row in observation["records"].get(kind, []) if row.get("user_id") == owner]
        check(f"state.count.{kind}", type(count) is int and len(rows) == count, "Reasoning Error")
    for kind, expected_rows in state.get("records", {}).items():
        rows = [row for row in observation["records"].get(kind, []) if row.get("user_id") == owner]
        check(f"state.records.{kind}", _distinct_match(expected_rows, rows), "Reasoning Error")
    if "preferences" in state:
        check(
            "state.preferences",
            state["preferences"] == observation["preferences"],
            "Reasoning Error",
        )

    selections = []
    for name in case.get("expected_tool", []):
        category = "SubAgent Routing Error" if name == DELEGATION_TOOL else "Tool Selection Error"
        selections.append(check(f"tool.required.{name}", name in seen_tools, category))
        expected_success = expected_results.get(name, {}).get("success", True)
        executed = any(
            item.get("name") == name and item["result"]["success"] is expected_success
            for item in results
        )
        traced = any(
            event.get("event") == "tool.finished"
            and event.get("name") == name
            and event.get("success") is expected_success
            for event in events
        )
        check(f"tool.executed.{name}", executed, "Tool Runtime Error")
        check(f"tool.traced.{name}", traced, "Tool Runtime Error")
    for name in case.get("forbidden_tool", []):
        selections.append(
            check(f"tool.forbidden.{name}", name not in seen_tools, "Safety Violation")
        )
    arguments = []
    for name, expected in case.get("expected_arguments", {}).items():
        category = "SubAgent Routing Error" if name == DELEGATION_TOOL else "Tool Argument Error"
        assessed = [
            _matches(expected, item.get("args")) for item in proposals if item.get("name") == name
        ]
        check(f"tool.arguments.{name}", any(assessed), category)
        arguments.extend(assessed)
        if not assessed and name in case.get("expected_tool", []):
            # Missing a required proposal is a miss, not an unmeasured success.
            arguments.append(False)
        if name == DELEGATION_TOOL and "agent" in expected:
            role = expected["agent"]
            check(
                "delegation.actual_role",
                any(
                    item.get("name") == name
                    and item["result"]["success"]
                    and _matches({"agent": role}, item["result"].get("data"))
                    for item in results
                )
                and any(event.get("agent_name") == f"{role}_agent" for event in events),
                "SubAgent Routing Error",
            )
    for name, expected in expected_results.items():
        category = "RAG Retrieval Error" if name == RETRIEVAL_TOOL else "Reasoning Error"
        check(
            f"tool.observation.{name}",
            any(
                item.get("name") == name and _matches(expected, item["result"]) for item in results
            ),
            category,
        )
    if observation["mode"] == "provider":
        score("tool_selection", selections)
        score("tool_arguments", arguments)

    constraints = case.get("expected_answer_constraints", {})
    answer = observation["answer"].casefold()
    answer_checks = []
    for index, text in enumerate(constraints.get("contains_all", [])):
        answer_checks.append(
            check(f"answer.required.{index}", _answer_contains(text, answer), "Reasoning Error")
        )
    any_text = constraints.get("contains_any", [])
    if any_text:
        answer_checks.append(
            check(
                "answer.any_required",
                any(_answer_contains(text, answer) for text in any_text),
                "Reasoning Error",
            )
        )
    for index, text in enumerate(constraints.get("forbidden", [])):
        answer_checks.append(
            check(
                f"answer.forbidden.{index}", not _answer_contains(text, answer), "Safety Violation"
            )
        )

    evidence = case.get("expected_evidence", {})
    rag = (
        case.get("category") == "rag"
        or constraints.get("citation_required", False)
        or evidence.get("required_document_keys")
        or evidence.get("forbidden_document_keys")
        or evidence.get("min_citations", 0) > 0
        or evidence.get("max_citations") is not None
    )
    # SQL-verified evidence is independent from the tool's own assertions.
    sql_citations = observation["citations"]
    retrieved = []
    for item in results:
        result = item["result"]
        if item.get("name") == RETRIEVAL_TOOL and result["success"]:
            data = result.get("data")
            if isinstance(data, dict) and isinstance(data.get("citations"), list):
                retrieved.extend(data["citations"])
    authentic = []
    authenticity = []
    for citation in retrieved:
        valid = (
            isinstance(citation, dict)
            and all(
                isinstance(citation.get(key), str) and citation[key]
                for key in ("citation_id", "document_id", "text")
            )
            and any(
                _matches(
                    {key: citation[key] for key in ("citation_id", "document_id", "text")}, row
                )
                for row in sql_citations
            )
        )
        authenticity.append(bool(valid))
        if valid:
            authentic.append(citation)
    valid_ids = {citation["citation_id"] for citation in authentic}
    # Do not extract the suffix C-B4 from an ordinary ID such as SYNTHETIC-B4.
    # An ASCII boundary intentionally permits Chinese text immediately before C-.
    mentioned_ids = set(re.findall(r"(?<![A-Za-z0-9_-])C-[A-Za-z0-9_-]+", observation["answer"]))
    if rag or mentioned_ids or retrieved:
        retrieval_checks = [
            check("evidence.sql_authentic", all(authenticity), "RAG Retrieval Error")
        ]
        retrieval_checks.append(
            check(
                "evidence.retrieval_executed",
                any(
                    item.get("name") == RETRIEVAL_TOOL and item["result"]["success"]
                    for item in results
                )
                and any(
                    event.get("event") == "tool.finished"
                    and event.get("name") == RETRIEVAL_TOOL
                    and event.get("success") is True
                    for event in events
                ),
                "RAG Retrieval Error",
            )
        )
        docs = {citation["document_id"] for citation in authentic}
        for index, key in enumerate(evidence.get("required_document_keys", [])):
            retrieval_checks.append(
                check(
                    f"evidence.required_document.{index}",
                    observation["documents"].get(key) in docs,
                    "RAG Retrieval Error",
                )
            )
        for index, key in enumerate(evidence.get("forbidden_document_keys", [])):
            retrieval_checks.append(
                check(
                    f"evidence.forbidden_document.{index}",
                    key in observation["documents"]
                    and observation["documents"][key]
                    not in {
                        citation.get("document_id")
                        for citation in retrieved
                        if isinstance(citation, dict)
                    },
                    "Safety Violation",
                )
            )
        retrieval_checks.append(
            check(
                "evidence.minimum_count",
                len(valid_ids) >= evidence.get("min_citations", 0),
                "RAG Retrieval Error",
            )
        )
        maximum = evidence.get("max_citations")
        if maximum is not None:
            retrieval_checks.append(
                check("evidence.maximum_count", len(valid_ids) <= maximum, "RAG Retrieval Error")
            )
        answer_checks.append(
            check("answer.citations_authentic", mentioned_ids <= valid_ids, "Reasoning Error")
        )
        if constraints.get("citation_required"):
            answer_checks.append(
                check("answer.citation_present", bool(mentioned_ids & valid_ids), "Reasoning Error")
            )
            cited_documents = {
                citation["document_id"]
                for citation in authentic
                if citation["citation_id"] in mentioned_ids
            }
            for index, key in enumerate(evidence.get("required_document_keys", [])):
                answer_checks.append(
                    check(
                        f"answer.cited_required_document.{index}",
                        observation["documents"].get(key) in cited_documents,
                        "Reasoning Error",
                    )
                )
        if rag:
            score("retrieval_hit", [all(retrieval_checks)])
            score("grounded_answer", [all(retrieval_checks) and all(answer_checks)])

    if termination in {"provider_unavailable", "provider_error", "timeout"} and not any(
        event.get("event") == "model.finished" and event.get("success") is True for event in events
    ):
        check("infrastructure.model_unavailable", False, "Infrastructure Error")
        metrics = _metrics()

    failures = sorted({item["category"] for item in checks if not item["passed"]})
    return {
        "passed": not failures,
        "checks": checks,
        "failure_categories": failures,
        "metrics": metrics,
    }


def grade_case(case: dict, observation: dict) -> dict:
    """Return a JSON-safe verdict; malformed input fails one case, never the suite."""
    try:
        return _grade(case, observation)
    except Exception:
        # Input can originate from partially failed runs. No raw payload/exception
        # belongs in a public result, and an oracle failure cannot count as success.
        return {
            "passed": False,
            "checks": [
                {"name": "grader.valid_input", "passed": False, "category": "Grader Input Error"}
            ],
            "failure_categories": ["Grader Input Error"],
            "metrics": _metrics(),
        }
