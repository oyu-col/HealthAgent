"""Exercise the actual provider adapter/SDK through a local mock HTTP transport."""

import json

import httpx
from langchain_openai import ChatOpenAI

from app.api.sse import SSEDecoder
from app.config import Settings
from app.domain.schemas import QueryInput
from app.main import create_app


async def test_actual_sdk_tool_call_and_observation(settings):
    calls = []

    def provider(request):
        payload = json.loads(request.content)
        calls.append(payload)
        if len(calls) == 1:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-real-sdk",
                        "type": "function",
                        "function": {
                            "name": "add_health_metric",
                            "arguments": json.dumps(
                                {"record": {"metric_type": "weight", "value": 70, "unit": "kg"}}
                            ),
                        },
                    }
                ],
            }
            finish = "tool_calls"
        else:
            assert payload["messages"][-1]["role"] == "tool"
            assert json.loads(payload["messages"][-1]["content"])["success"] is True
            message = {"role": "assistant", "content": "合成记录已保存。"}
            finish = "stop"
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1,
                "model": "test-model",
                "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as provider_client:
        model = ChatOpenAI(
            model="test-model",
            api_key="synthetic-key",
            base_url="https://mock.invalid/v1",
            http_async_client=provider_client,
            use_responses_api=False,
            max_retries=0,
        )
        app = create_app(settings=settings, model=model)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                result = await client.post("/api/chat", json={"message": "记录合成体重"})
                assert result.status_code == 200 and result.json()["answer"] == "合成记录已保存。"
            assert (
                len(
                    (await app.state.health.query("metric", "local-user", QueryInput())).data[
                        "records"
                    ]
                )
                == 1
            )
    assert len(calls) == 2


async def test_actual_sdk_streaming_is_incremental(settings):
    def provider(request):
        assert json.loads(request.content)["stream"] is True
        frames = []
        for text, finish in (("合成", None), ("中文流", None), ("", "stop")):
            event = {
                "id": "chatcmpl-stream",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": text},
                        "finish_reason": finish,
                    }
                ],
            }
            frames.append("data: " + json.dumps(event) + "\n\n")
        return httpx.Response(
            200,
            content=("".join(frames) + "data: [DONE]\n\n").encode(),
            headers={"Content-Type": "text/event-stream"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as provider_client:
        model = ChatOpenAI(
            model="test-model",
            api_key="synthetic-key",
            base_url="https://mock.invalid/v1",
            http_async_client=provider_client,
            use_responses_api=False,
            max_retries=0,
        )
        app = create_app(settings=settings, model=model)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post("/api/chat/stream", json={"message": "合成流"})
                events = SSEDecoder().feed(response.content)
                assert [e["data"]["text"] for e in events if e["event"] == "message.delta"] == [
                    "合成",
                    "中文流",
                ]
                assert events[-1]["data"]["answer"] == "合成中文流"


async def test_chatopenai_request_and_answer_through_real_graph(tmp_path):
    requests = []

    def provider(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "我可以帮助整理健康信息。"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
            },
        )

    settings = Settings(
        model_mode="provider",
        model_name="test-model",
        model_base_url="https://mock.invalid/v1",
        model_api_key="synthetic-key",
        data_dir=tmp_path,
        _env_file=None,
    )
    with httpx.Client(transport=httpx.MockTransport(provider)) as sync_client:
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as async_client:
            model = ChatOpenAI(
                model=settings.model_name,
                api_key=settings.model_api_key,
                base_url=str(settings.model_base_url),
                http_client=sync_client,
                http_async_client=async_client,
                use_responses_api=False,
                max_retries=0,
            )
            app = create_app(settings=settings, model=model)
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post("/api/chat", json={"message": "介绍你自己"})
    assert response.status_code == 200
    assert response.json()["answer"] == "我可以帮助整理健康信息。"
    assert response.json()["model_mode"] == "provider"
    assert len(requests) == 1
    request = requests[0]
    assert request.url.path == "/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer synthetic-key"
    body = json.loads(request.content)
    assert body["model"] == "test-model"
    assert body["messages"][-1] == {"role": "user", "content": "介绍你自己"}
    assert body["messages"][0]["role"] == "system"
    assert "不是医生" in body["messages"][0]["content"]
    assert len(body["tools"]) == 10
    assert any(item["function"]["name"] == "delegate_health_task" for item in body["tools"])
    assert "user_id" not in json.dumps(body["tools"])
    assert "synthetic-key" not in response.text
