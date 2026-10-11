"""Run bounded, isolated synthetic tasks through the actual HealthAgent HTTP/graph stack."""
# ruff: noqa: E402 -- CLI bootstrap adds the independent benchmark package before imports.

import argparse
import asyncio
import hashlib
import json
import logging
import os
import random
import sys
import tempfile
from contextlib import AsyncExitStack, contextmanager
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx
from langchain_core.messages import ToolMessage

from app.config import Settings, load_settings
from app.main import create_app
from app.models.factory import model_session
from benchmark.environment import inject_fault, seed
from benchmark.graders.task import grade_case
from benchmark.model import ContractModel
from benchmark.observation import OWNER, Capture, snapshot, verified_evidence
from benchmark.report import markdown, summarize
from benchmark.schema import load_cases

BASE_SETTINGS = {
    "auth_mode": "local",
    "local_user_id": OWNER,
    "timezone": "Asia/Shanghai",
    "embedding_mode": "local_hash",
    "embedding_dimensions": 1024,
    "request_timeout_seconds": 90,
    "model_timeout_seconds": 30,
    "model_max_retries": 0,
    "max_steps": 16,
    "max_tool_calls": 12,
    "subagent_timeout_seconds": 30,
    "subagent_max_steps": 8,
    "tool_timeout_seconds": 2,
    "tool_max_retries": 2,
    "tool_retry_initial_delay": 0,
    "memory_enabled": True,
    "subagents_enabled": True,
}


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def file_digest(paths):
    return digest(
        {
            str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(paths)
        }
    )


@contextmanager
def isolated_environment():
    prefixes = ("HEALTH_AGENT_", "OPENAI_", "LANGCHAIN_", "LANGSMITH_")
    saved = {key: value for key, value in os.environ.items() if key.startswith(prefixes)}
    for key in saved:
        del os.environ[key]
    os.environ["LANGSMITH_TRACING"] = "false"
    try:
        yield
    finally:
        for key in list(os.environ):
            if key.startswith(prefixes):
                del os.environ[key]
        os.environ.update(saved)


async def run_case(case, mode, provider=None):
    start = perf_counter()
    with tempfile.TemporaryDirectory(prefix=".benchmark-", dir=ROOT / "backend") as temporary:
        settings_values = {**BASE_SETTINGS, **case.get("settings", {}), "data_dir": Path(temporary)}
        if provider:
            settings_values.update(
                model_mode="provider",
                model_name=provider.model_name,
                model_base_url=provider.model_base_url,
                model_api_key=provider.model_api_key,
            )
        else:
            settings_values["model_mode"] = "fake"
        settings = Settings(_env_file=None, **settings_values)
        capture = Capture()
        async with AsyncExitStack() as stack:
            if mode == "contract":
                model = ContractModel(execution_plan=case["execution_plan"], cache=False)
            else:
                model = await stack.enter_async_context(model_session(settings))
                model.temperature = 0
                model.max_tokens = 1200
            app = create_app(settings=settings, model=model)
            await stack.enter_async_context(app.router.lifespan_context(app))
            documents = await seed(app, case)
            before, _ = await snapshot(app.state.sessions)
            graph_config = app.state.runtime.graph_config

            def observed_config(context):
                config = graph_config(context)
                config["callbacks"] = [*config.get("callbacks", []), capture]
                return config

            app.state.runtime.graph_config = observed_config
            request_id = str(uuid4())
            answer, termination, thread_id = "", "harness_error", None
            attempts = []
            with inject_fault(app, case.get("fault"), settings) as injected:
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://benchmark"
                ) as client:
                    payload = {"message": case["input"], "request_id": request_id}
                    response = await client.post("/api/chat", json=payload)
                    data = response.json()
                    thread_id = data.get("thread_id") or data.get("error", {}).get("thread_id")
                    attempts.append(
                        {"status": response.status_code, "code": data.get("error", {}).get("code")}
                    )
                    if case.get("interaction") == "replay" and response.is_success:
                        payload["thread_id"] = thread_id
                        response = await client.post("/api/chat", json=payload)
                        data = response.json()
                        attempts.append(
                            {
                                "status": response.status_code,
                                "code": data.get("error", {}).get("code"),
                            }
                        )
                    elif (
                        case.get("interaction") == "resume"
                        and not response.is_success
                        and thread_id
                    ):
                        response = await client.post(
                            f"/api/threads/{thread_id}/resume", json={"request_id": request_id}
                        )
                        data = response.json()
                        attempts.append(
                            {
                                "status": response.status_code,
                                "code": data.get("error", {}).get("code"),
                            }
                        )
                    if response.is_success:
                        answer, termination = data["answer"], "completed"
                    else:
                        termination = data.get("error", {}).get("code", "http_error")
            if thread_id:
                state = await app.state.runtime.graph.aget_state(
                    {"configurable": {"thread_id": thread_id}}
                )
                for message in state.values.get("messages", []):
                    if isinstance(message, ToolMessage):
                        capture.add(
                            {"name": message.name, "agent_name": "health_lead_agent"}, message
                        )
            records, preferences = await snapshot(app.state.sessions)
            summaries = await app.state.traces.list(OWNER, limit=100)
            traces = [await app.state.traces.get(OWNER, row["trace_id"]) for row in summaries]
            other_before = {
                kind: [r for r in rows if r["user_id"] != OWNER] for kind, rows in before.items()
            }
            other_after = {
                kind: [r for r in rows if r["user_id"] != OWNER] for kind, rows in records.items()
            }
            observed = {
                "mode": mode,
                "answer": answer,
                "termination": termination,
                "records": records,
                "preferences": preferences,
                "other_owners_unchanged": other_before == other_after,
                "proposals": capture.proposals,
                "observations": capture.observations,
                "citations": await verified_evidence(app.state.sessions, capture.observations),
                "documents": documents,
                "traces": traces,
                "fault_triggered": injected["triggered"],
            }
            graded = grade_case(case, observed)
            return {
                "case_id": case["case_id"],
                "category": case["category"],
                **graded,
                "termination": termination,
                "latency_ms": round((perf_counter() - start) * 1000, 3),
                "traces": traces,
                "attempts": attempts,
                "model_errors": capture.model_errors,
                "fault_triggered": injected["triggered"],
                "recovery_eligible": case["category"] == "recovery"
                or (case.get("fault") or {}).get("kind") == "transient_once",
                "observed_counts": {
                    kind: sum(r["user_id"] == OWNER for r in rows) for kind, rows in records.items()
                },
                "retrieved_document_keys": [
                    key
                    for key, value in documents.items()
                    if any(c["document_id"] == value for c in observed["citations"])
                ],
            }


async def run_suite(args):
    cases = load_cases(args.cases)
    selected = [
        case
        for case in cases
        if args.mode in case.get("profiles", ["contract", "provider"])
        and (not args.case_id or case["case_id"] in args.case_id)
    ]
    if not selected or (args.case_id and set(args.case_id) != {c["case_id"] for c in selected}):
        raise ValueError("Unknown or inapplicable selected cases")
    provider = None
    if args.mode == "provider":
        if not args.allow_provider:
            raise ValueError("Provider mode requires explicit --allow-provider")
        provider = load_settings()
        if provider.model_mode != "provider":
            raise ValueError("Explicit provider configuration is required; no fake fallback")
    if args.output.exists():
        raise ValueError("Run output already exists; baseline reports are immutable")
    args.output.mkdir(parents=True)
    bench = ROOT / "benchmark"
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "mode": args.mode,
        "seed": args.seed,
        "repeats": args.repeats,
        "selected_cases": [case["case_id"] for case in selected],
        "profile_excluded_cases": [
            case["case_id"]
            for case in cases
            if args.mode not in case.get("profiles", ["contract", "provider"])
        ],
        "case_digest": digest(cases),
        "grader_digest": file_digest((bench / "graders").glob("*.py")),
        "protocol_digest": file_digest(
            [
                bench / name
                for name in (
                    "runner.py",
                    "model.py",
                    "environment.py",
                    "observation.py",
                    "report.py",
                    "schema.py",
                )
            ]
        ),
        "app_digest": file_digest((ROOT / "backend" / "app").rglob("*.py")),
        "settings_digest": digest(
            {
                **BASE_SETTINGS,
                "model": provider.model_name if provider else "contract",
                "endpoint_fingerprint": digest(str(provider.model_base_url)) if provider else None,
                "temperature": 0,
                "max_tokens": 1200,
            }
        ),
        "model": provider.model_name if provider else "contract-script-v1",
        "settings": BASE_SETTINGS,
        "python": sys.version.split()[0],
        "dependencies": {
            name: version(name)
            for name in ("langchain", "langgraph", "langchain-openai", "sqlalchemy")
        },
        "limitations": [
            "Synthetic fixtures only",
            "No clinical validation",
            "Contract decisions are prescribed",
            "Provider seed unsupported; temperature=0 does not ensure determinism",
        ],
    }
    results = []
    with isolated_environment():
        for repeat in range(1, args.repeats + 1):
            random.seed(args.seed + repeat - 1)
            for case in selected:
                case_started = perf_counter()
                try:
                    async with asyncio.timeout(220):
                        result = await run_case(case, args.mode, provider)
                except Exception as error:
                    result = {
                        "case_id": case["case_id"],
                        "category": case["category"],
                        "passed": False,
                        "termination": "harness_error",
                        "latency_ms": round((perf_counter() - case_started) * 1000, 3),
                        "harness_error_type": type(error).__name__,
                        "traces": [],
                        "checks": [
                            {
                                "name": "harness_completed",
                                "passed": False,
                                "category": "Harness Error",
                            }
                        ],
                        "failure_categories": ["Harness Error"],
                        "metrics": {},
                    }
                result["repeat"] = repeat
                results.append(result)
                report = {"manifest": manifest, "summary": summarize(results), "results": results}
                temp = args.output / "report.tmp"
                temp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                temp.replace(args.output / "report.json")
                print(
                    json.dumps(
                        {
                            key: result[key]
                            for key in (
                                "case_id",
                                "repeat",
                                "passed",
                                "termination",
                                "failure_categories",
                            )
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
    report["manifest"]["completed"] = True
    (args.output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output / "report.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False), flush=True)
    return 0 if all(row["passed"] for row in results) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("contract", "provider"), default="contract")
    parser.add_argument("--allow-provider", action="store_true")
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--seed", type=int, default=20261011)
    args = parser.parse_args()
    logging.basicConfig(level=logging.CRITICAL)
    try:
        status = asyncio.run(run_suite(args))
    except (ValueError, RuntimeError):
        print(
            "Benchmark setup failed; check mode, configuration, cases and a new output path.",
            file=sys.stderr,
        )
        status = 2
    raise SystemExit(status)


if __name__ == "__main__":
    main()
