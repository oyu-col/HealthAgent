"""Start a real local Uvicorn server, check the API, then shut down our own process."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

from app.api.sse import SSEDecoder


def main() -> None:
    backend = Path(__file__).resolve().parents[1]
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    env = {key: value for key, value in os.environ.items() if not key.startswith("HEALTH_AGENT_")}
    env["HEALTH_AGENT_MODEL_MODE"] = "fake"
    env["HEALTH_AGENT_AUTH_MODE"] = "local"
    env["HEALTH_AGENT_EMBEDDING_MODE"] = "local_hash"
    env["HEALTH_AGENT_MEMORY_ENABLED"] = "true"
    env["PYTHONUTF8"] = "1"
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    with (
        tempfile.TemporaryDirectory(prefix=".smoke-", dir=backend) as data_dir,
        tempfile.TemporaryFile(mode="w+b", dir=backend) as log,
    ):
        # Validate the precise cleanup target before TemporaryDirectory removes its contents.
        data_root = Path(data_dir).resolve()
        if not data_root.is_relative_to(backend.resolve()):
            raise RuntimeError("Temporary data directory is outside the workspace")
        env["HEALTH_AGENT_DATA_DIR"] = str(data_root)
        shutdown_signal = data_root / "stop"
        process = subprocess.Popen(
            [
                sys.executable,
                "scripts/smoke_server.py",
                str(port),
                str(shutdown_signal),
            ],
            cwd=backend,
            env=env,
            stdout=log,
            stderr=log,
            creationflags=flags,
        )
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}", timeout=2, trust_env=False
            ) as client:
                deadline = time.monotonic() + 30
                while True:
                    if process.poll() is not None:
                        raise RuntimeError("Local server exited before readiness")
                    try:
                        health = client.get("/healthz")
                        health.raise_for_status()
                        break
                    except httpx.HTTPError:
                        if time.monotonic() >= deadline:
                            raise RuntimeError(
                                "Local server did not become ready within 30s"
                            ) from None
                        time.sleep(0.1)
                assert health.json() == {"status": "ok", "phase": 12, "model_mode": "fake"}
                schema = client.get("/openapi.json")
                schema.raise_for_status()
                assert "/api/chat" in schema.json()["paths"]
                response = client.post("/api/chat", json={"message": "请记住：我喜欢简短的回答。"})
                response.raise_for_status()
                assert response.json()["model_mode"] == "fake"
                assert "[FAKE 演示模式]" in response.json()["answer"]
                assert response.json()["trace_id"] == response.headers["X-Trace-ID"]
                thread_id = response.json()["thread_id"]
                state = client.get("/api/threads/" + thread_id).json()
                assert len(state["messages"]) == 2
                assert client.get("/api/memory").json()["preferences"][0]["value"] == "concise"
                document = client.post(
                    "/api/documents/text",
                    json={"filename": "smoke.md", "text": "合成步行测试文档，仅供软件验证。"},
                )
                document.raise_for_status()
                assert document.json()["index_status"] == "indexed"
                decoder = SSEDecoder()
                events = []
                with client.stream(
                    "POST",
                    "/api/chat/stream",
                    json={"message": "Phase 10 流式启动验证", "thread_id": thread_id},
                ) as streamed:
                    streamed.raise_for_status()
                    for chunk in streamed.iter_bytes():
                        events.extend(decoder.feed(chunk))
                assert events[0]["event"] == "run.started"
                assert events[-1]["event"] == "run.completed"
                assert "[FAKE 演示模式]" in events[-1]["data"]["answer"]
                assert len(client.get("/api/threads/" + thread_id).json()["messages"]) == 4
                client.delete("/api/memory/response_style").raise_for_status()
                assert not client.get("/api/memory").json()["preferences"]
                if process.poll() is not None:
                    raise RuntimeError("Server exited during smoke")
                report = {
                    "status": "passed",
                    "model_mode": "fake",
                    "port": port,
                    "checks": [
                        "healthz",
                        "openapi",
                        "chat",
                        "trace_header",
                        "thread_history",
                        "memory_extraction",
                        "document_index",
                        "tcp_sse",
                        "memory_delete",
                    ],
                    "trace_id": response.json()["trace_id"],
                }
                trace = client.get("/api/traces/" + response.json()["trace_id"])
                trace.raise_for_status()
                assert trace.json()["termination_reason"] == "completed"
                assert trace.json()["model_calls"] >= 1
                report["checks"].append("persistent_trace")
                if "--ui" in sys.argv:
                    # Exercises the built UI against this real isolated API, without mocks.
                    completed = subprocess.run(
                        ["node", "scripts/smoke.mjs", f"http://127.0.0.1:{port}"],
                        cwd=backend.parent / "frontend",
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=90,
                        creationflags=flags,
                    )
                    if completed.returncode:
                        raise RuntimeError("Browser smoke failed: " + completed.stderr[-3000:])
                    report["browser"] = json.loads(completed.stdout)
                    report["checks"].append("real_browser_ui")
        finally:
            # Gracefully stop the actual server, not merely Windows' venv launcher.
            shutdown_signal.touch()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        check=False,
                        stdout=log,
                        stderr=log,
                        creationflags=flags,
                    )
                else:
                    process.kill()
                process.wait(timeout=5)
            if process.returncode != 0:
                raise RuntimeError("Smoke server did not exit cleanly")
        with socket.socket() as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError("Smoke server port is still listening")
        report["checks"].append("graceful_shutdown")
    # Report success only after process exit AND temporary data cleanup succeed.
    print(json.dumps(report))


if __name__ == "__main__":
    main()
