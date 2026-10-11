"""Strict, versioned synthetic benchmark input; no grader or model execution here."""

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CATEGORIES = frozenset(
    {
        "single_tool_query",
        "write_operation",
        "rag",
        "multi_tool",
        "multi_agent",
        "missing_parameters",
        "ambiguous_input",
        "tool_failure",
        "tool_timeout",
        "recovery",
        "safety",
        "loop_detection",
    }
)
TOOL_NAMES = frozenset(
    {
        "add_health_metric",
        "add_diet_record",
        "add_exercise_record",
        "query_health_metrics",
        "query_diet_records",
        "query_exercise_records",
        "query_health_documents",
        "calculate_health_trend",
        "search_health_knowledge",
        "delegate_health_task",
    }
)
AGENT_NAMES = frozenset({"health_lead_agent", "record_agent", "nutrition_agent", "research_agent"})
SETTING_RANGES = {
    "max_steps": (2, 100),
    "max_tool_calls": (1, 100),
    "max_delegations": (1, 6),
    "subagent_max_steps": (2, 50),
    "subagent_max_concurrency": (1, 4),
    "request_timeout_seconds": (0.001, 300),
    "model_timeout_seconds": (0.001, 300),
    "tool_timeout_seconds": (0.001, 120),
    "subagent_timeout_seconds": (0.001, 120),
    "tool_max_retries": (0, 3),
    "tool_retry_initial_delay": (0, 5),
}
DEFAULT_CASES = Path(__file__).resolve().parent / "cases" / "health-v1.json"
TERMINATIONS = frozenset(
    {
        "completed",
        "no_progress",
        "tool_limit",
        "step_limit",
        "timeout",
        "cancelled",
        "provider_unavailable",
        "provider_error",
        "internal_error",
        "invalid_model_output",
        "trace_unavailable",
        "delegation_limit",
    }
)
PREFERENCE_VALUES = {
    "response_style": {"concise", "detailed"},
    "language": {"zh", "en"},
    "diet_preference": {"light", "vegetarian", "no_spicy"},
    "exercise_preference": {"walking", "running", "swimming", "cycling", "yoga"},
}


def validate_preferences(values):
    if any(
        key not in PREFERENCE_VALUES or value not in PREFERENCE_VALUES[key]
        for key, value in values.items()
    ):
        raise ValueError("benchmark preference must use the product allowlist")
    return values


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SeedRecord(StrictModel):
    kind: Literal["metric", "diet", "exercise"]
    user_id: str = Field(default="benchmark-user", min_length=1, max_length=64)
    record: dict[str, Any]


class SeedDocument(StrictModel):
    key: str = Field(min_length=1, max_length=80)
    user_id: str = Field(default="benchmark-user", min_length=1, max_length=64)
    filename: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=20000)
    visibility: Literal["personal", "public"] = "personal"
    source: str = "synthetic-benchmark"


class Environment(StrictModel):
    records: list[SeedRecord] = Field(default_factory=list)
    documents: list[SeedDocument] = Field(default_factory=list)
    preferences: dict[str, str] = Field(default_factory=dict)

    @field_validator("preferences")
    @classmethod
    def allowed_preferences(cls, values):
        return validate_preferences(values)


class ToolStep(StrictModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tool")
    @classmethod
    def known_tool(cls, value):
        if value not in TOOL_NAMES:
            raise ValueError("unknown benchmark tool")
        return value


class ResponseStep(StrictModel):
    # A contract-only explicit response tests plumbing/clarification; it is not model reasoning.
    respond: str = Field(min_length=1, max_length=6000)


class ExpectedState(StrictModel):
    counts: dict[Literal["metric", "diet", "exercise"], int] = Field(default_factory=dict)
    records: dict[Literal["metric", "diet", "exercise"], list[dict[str, Any]]] = Field(
        default_factory=dict
    )
    preferences: dict[str, str] = Field(default_factory=dict)

    @field_validator("preferences")
    @classmethod
    def allowed_preferences(cls, values):
        return validate_preferences(values)

    @field_validator("counts")
    @classmethod
    def nonnegative_counts(cls, values):
        if any(value < 0 for value in values.values()):
            raise ValueError("negative expected record count")
        return values


class AnswerConstraints(StrictModel):
    contains_all: list[str] = Field(default_factory=list)
    contains_any: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    citation_required: bool = False


class Evidence(StrictModel):
    required_document_keys: list[str] = Field(default_factory=list)
    forbidden_document_keys: list[str] = Field(default_factory=list)
    min_citations: int = Field(default=0, ge=0, le=100)
    max_citations: int | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def consistent(self):
        if self.max_citations is not None and self.min_citations > self.max_citations:
            raise ValueError("inverted citation bounds")
        if set(self.required_document_keys) & set(self.forbidden_document_keys):
            raise ValueError("same evidence is required and forbidden")
        return self


class Fault(StrictModel):
    target: Literal["query", "search", "add", "trace_finish"]
    kind: Literal["transient_once", "permanent", "timeout_once", "finish_once"]
    record_kind: Literal["metric", "diet", "exercise"] | None = None


class BenchmarkCase(StrictModel):
    case_id: str = Field(pattern=r"^[a-z][a-z0-9_]{2,79}$")
    category: str
    input: str = Field(min_length=1, max_length=8000)
    initial_environment: Environment = Field(default_factory=Environment)
    execution_plan: dict[str, list[ToolStep | ResponseStep]] = Field(default_factory=dict)
    expected_state: ExpectedState = Field(default_factory=ExpectedState)
    expected_tool: list[str] = Field(default_factory=list)
    forbidden_tool: list[str] = Field(default_factory=list)
    expected_arguments: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # Predicates match the full ToolResult envelope, including success/data/error_code.
    expected_observations: dict[str, dict[str, Any]] = Field(default_factory=dict)
    expected_answer_constraints: AnswerConstraints = Field(default_factory=AnswerConstraints)
    expected_evidence: Evidence = Field(default_factory=Evidence)
    allowed_terminations: list[str] = Field(default_factory=lambda: ["completed"])
    interaction: Literal["single", "replay", "resume"] = "single"
    fault: Fault | None = None
    settings: dict[str, int | float | bool] = Field(default_factory=dict)
    profiles: list[Literal["contract", "provider"]] = Field(
        default_factory=lambda: ["contract", "provider"], min_length=1
    )
    grader: Literal["task_v1"] = "task_v1"

    @field_validator("category")
    @classmethod
    def known_category(cls, value):
        if value not in CATEGORIES:
            raise ValueError("unknown benchmark category")
        return value

    @field_validator("allowed_terminations")
    @classmethod
    def known_terminations(cls, values):
        if not values or set(values) - TERMINATIONS:
            raise ValueError("unknown or empty termination oracle")
        return values

    @field_validator("execution_plan")
    @classmethod
    def known_agents(cls, values):
        if set(values) - AGENT_NAMES:
            raise ValueError("unknown execution-plan agent")
        return values

    @field_validator("expected_tool", "forbidden_tool")
    @classmethod
    def known_tools(cls, values):
        if set(values) - TOOL_NAMES:
            raise ValueError("unknown expected or forbidden tool")
        return values

    @field_validator("expected_arguments", "expected_observations")
    @classmethod
    def known_predicate_tools(cls, values):
        if set(values) - TOOL_NAMES:
            raise ValueError("unknown predicate tool")
        return values

    @field_validator("settings")
    @classmethod
    def bounded_settings(cls, values):
        for name, value in values.items():
            if name in {"memory_enabled", "subagents_enabled"}:
                if type(value) is not bool:
                    raise ValueError("feature switch must be boolean")
                continue
            if name not in SETTING_RANGES or type(value) is bool:
                raise ValueError("benchmark may only override bounded execution settings")
            lower, upper = SETTING_RANGES[name]
            if not lower <= value <= upper:
                raise ValueError("benchmark execution setting outside safe bounds")
            if name.startswith("max_") or name in {
                "subagent_max_steps",
                "subagent_max_concurrency",
                "tool_max_retries",
            }:
                if type(value) is not int:
                    raise ValueError("execution count must be an integer")
        return values

    @model_validator(mode="after")
    def coherent(self):
        keys = [document.key for document in self.initial_environment.documents]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate initial document key")
        evidence_keys = (
            self.expected_evidence.required_document_keys
            + self.expected_evidence.forbidden_document_keys
        )
        if set(evidence_keys) - set(keys):
            raise ValueError("evidence oracle references an unknown document key")
        if set(self.expected_tool) & set(self.forbidden_tool):
            raise ValueError("same tool is required and forbidden")
        if len(set(self.profiles)) != len(self.profiles):
            raise ValueError("duplicate profile")
        if (self.fault or self.category == "loop_detection") and self.profiles != ["contract"]:
            raise ValueError("scripted fault/loop protection cases are contract-only")
        if not self.allowed_terminations:
            raise ValueError("at least one termination oracle is required")
        return self


def load_cases(path: str | Path | None = None) -> list[dict]:
    """Return fresh validated dictionaries; never pass entire cases into the model."""
    payload = json.loads(Path(path or DEFAULT_CASES).read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("benchmark corpus must be a nonempty list")
    cases = [BenchmarkCase.model_validate(item).model_dump(mode="json") for item in payload]
    ids = [case["case_id"] for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate case_id")
    return cases
