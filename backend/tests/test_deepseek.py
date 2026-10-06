import json

import httpx
import pytest

from backend.app.deepseek import DeepSeekAPIError, analyze_with_deepseek, verify_deepseek_key


@pytest.fixture
def anyio_backend():
    return "asyncio"


def sample_hotspot():
    return {
        "title": "开源大模型发布新版推理能力",
        "content_excerpt": "官方发布开源大模型新版，新增人工智能推理能力并公开技术报告。",
        "source_platform": "官方博客",
        "source_url": "https://example.com/model-release",
        "published_at": "2026-10-03T00:00:00+00:00",
        "collected_at": "2026-10-03T01:00:00+00:00",
        "engagement_count": 1200,
    }


@pytest.mark.anyio
async def test_structured_model_result_is_validated_and_merged():
    async def handler(request):
        assert request.headers["Authorization"] == "Bearer sk-unit-test-key"
        request_payload = json.loads(request.content)
        assert request_payload["model"] == "deepseek-v4-flash"
        assert request_payload["response_format"] == {"type": "json_object"}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
            "category": "科技互联网", "attention_level": "medium",
            "summary": "官方发布了包含推理能力的新版本开源大模型。", "confidence": 0.94,
            "evidence": ["官方博客发布", "内容包含人工智能和推理能力"],
            "keywords": ["开源大模型", "推理"], "entities": [], "can_auto_handle": True,
            "action_type": "auto_categorize", "action_suggestion": "加入热点候选队列并人工抽检。",
            "missing_information": [],
        }, ensure_ascii=False)}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await analyze_with_deepseek(sample_hotspot(), "sk-unit-test-key", client)
    assert result["provider"] == "deepseek"
    assert result["category"] == "科技互联网"
    assert result["can_auto_handle"] is True
    assert any(item["name"] == "模型与规则一致性" for item in result["verification"])


@pytest.mark.anyio
async def test_invalid_json_and_upstream_errors_are_public_safe():
    async def invalid_handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": "not-json"}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(invalid_handler)) as client:
        with pytest.raises(DeepSeekAPIError) as error:
            await analyze_with_deepseek(sample_hotspot(), "sk-unit-test-key", client)
    assert error.value.status_code == 502
    assert "无效" in error.value.message

    async def rate_limit_handler(request):
        return httpx.Response(429, json={"error": {"message": "secret upstream detail"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(rate_limit_handler)) as client:
        with pytest.raises(DeepSeekAPIError) as error:
            await verify_deepseek_key("sk-unit-test-key", client)
    assert error.value.status_code == 429
    assert "secret" not in error.value.message


@pytest.mark.anyio
async def test_model_rule_conflict_blocks_auto_admission():
    async def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
            "category": "公共政策", "attention_level": "high",
            "summary": "模型给出了与本地规则不同的分类。", "confidence": 0.9,
            "evidence": ["模型证据"], "can_auto_handle": True,
            "action_type": "auto_categorize", "action_suggestion": "等待人工复核。",
            "missing_information": [],
        }, ensure_ascii=False)}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await analyze_with_deepseek(sample_hotspot(), "sk-unit-test-key", client)
    assert result["can_auto_handle"] is False
    assert "模型与规则结论不一致" in result["risk_flags"]
