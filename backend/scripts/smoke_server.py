"""Smoke-only Uvicorn runner with a local file signal for graceful Windows shutdown."""

import asyncio
import sys
from pathlib import Path

import uvicorn


async def serve(port, signal_path):
    server = uvicorn.Server(
        uvicorn.Config(
            "app.main:create_app",
            factory=True,
            host="127.0.0.1",
            port=port,
            log_config="logging.json",
        )
    )

    async def shutdown_signal():
        # The signal comes from another process, so an in-process Event cannot observe it.
        while not await asyncio.to_thread(signal_path.exists):  # noqa: ASYNC110
            await asyncio.sleep(0.1)
        server.should_exit = True

    watcher = asyncio.create_task(shutdown_signal())
    try:
        await server.serve()
    finally:
        watcher.cancel()
        await asyncio.gather(watcher, return_exceptions=True)


if __name__ == "__main__":
    port = int(sys.argv[1])
    signal_path = Path(sys.argv[2]).resolve()
    backend = Path(__file__).resolve().parents[1]
    if not signal_path.is_relative_to(backend) or not signal_path.parent.name.startswith(".smoke-"):
        raise ValueError("Shutdown signal must stay in the smoke temporary directory")
    asyncio.run(serve(port, signal_path))
