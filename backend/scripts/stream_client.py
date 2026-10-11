"""Run from backend: python scripts/stream_client.py --message '你好'."""

import argparse
import os
import sys

import httpx

from app.api.sse import SSEDecoder


def main():
    parser = argparse.ArgumentParser(description="HealthAgent SSE test client")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--message", required=True)
    parser.add_argument("--thread-id")
    parser.add_argument("--request-id")
    args = parser.parse_args()
    payload = {"message": args.message, "thread_id": args.thread_id, "request_id": args.request_id}
    token = os.environ.get("HEALTH_AGENT_CLIENT_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    decoder = SSEDecoder()
    completed = False
    with httpx.stream(
        "POST",
        args.url.rstrip("/") + "/api/chat/stream",
        json=payload,
        headers=headers,
        timeout=310,
    ) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            for event in decoder.feed(chunk):
                kind, data = event["event"], event["data"]
                if kind == "message.delta":
                    print(data["text"], end="", flush=True)
                elif kind == "run.started":
                    print(
                        f"thread_id={data['thread_id']} request_id={data['request_id']}",
                        file=sys.stderr,
                    )
                elif kind == "run.completed":
                    print("\n最终回答：" + data["answer"])
                    completed = True
                elif kind == "run.failed":
                    raise SystemExit(data["error_code"] + ": " + data["error_message"])
    if not completed:
        raise SystemExit("Stream ended without a terminal completion; resume with request_id.")


if __name__ == "__main__":
    main()
