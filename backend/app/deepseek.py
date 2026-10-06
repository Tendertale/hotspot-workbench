import json
import os
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .analyzer import analyze_hotspot


DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")


class DeepSeekAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class ModelAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    category: str = Field(min_length=1)
    attention_level: str = Field(default="medium")
    summary: str = Field(min_length=4, max_length=500)
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(min_length=1, max_length=10)
    keywords: list[str] = Field(default_factory=list, max_length=10)
    entities: list[str] = Field(default_factory=list, max_length=10)
    can_auto_handle: bool = False
    action_type: str = "human_review"
    action_suggestion: str = Field(min_length=4, max_length=1000)
    missing_information: list[str] = Field(default_factory=list, max_length=10)


def _public_error(response: httpx.Response) -> DeepSeekAPIError:
    if response.status_code == 401:
        return DeepSeekAPIError(401, "DeepSeek API 密钥无效或已失效")
    if response.status_code == 429:
        return DeepSeekAPIError(429, "DeepSeek 服务当前限流，请稍后重试")
    return DeepSeekAPIError(502, "DeepSeek 服务暂时不可用")


async def _request(client: httpx.AsyncClient, method: str, path: str, api_key: str,
                   **kwargs: Any) -> httpx.Response:
    try:
        response = await client.request(method, DEEPSEEK_BASE_URL + path,
                                        headers={"Authorization": "Bearer " + api_key,
                                                 "Content-Type": "application/json"}, **kwargs)
    except httpx.TimeoutException as error:
        raise DeepSeekAPIError(504, "DeepSeek 服务响应超时") from error
    except httpx.HTTPError as error:
        raise DeepSeekAPIError(502, "DeepSeek 服务暂时不可用") from error
    if response.status_code >= 400:
        raise _public_error(response)
    return response


async def verify_deepseek_key(api_key: str, client: Optional[httpx.AsyncClient] = None) -> Dict[str, str]:
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=8, trust_env=False)
    try:
        await _request(client, "GET", "/models", api_key)
        return {"provider": "deepseek", "model": DEEPSEEK_MODEL, "status": "ok"}
    finally:
        if owns_client:
            await client.aclose()


async def analyze_with_deepseek(hotspot: Dict[str, Any], api_key: str,
                                client: Optional[httpx.AsyncClient] = None) -> Dict[str, Any]:
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=30, trust_env=False)
    payload = {
        "model": DEEPSEEK_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "你是热点线索研判员。只输出 JSON，不要输出 Markdown。category 只能是社会民生、科技互联网、商业财经、公共政策、文娱体育、其他；attention_level 只能是 high、medium、low。"},
            {"role": "user", "content": json.dumps({"title": hotspot["title"], "content_excerpt": hotspot["content_excerpt"], "source_platform": hotspot.get("source_platform", ""), "source_url": hotspot.get("source_url"), "published_at": hotspot.get("published_at")}, ensure_ascii=False)},
        ],
    }
    try:
        response = await _request(client, "POST", "/chat/completions", api_key, json=payload)
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        model_result = ModelAnalysis.model_validate(json.loads(content))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, ValidationError) as error:
        raise DeepSeekAPIError(502, "DeepSeek 返回的分析结果格式无效") from error
    finally:
        if owns_client:
            await client.aclose()

    rules = analyze_hotspot(hotspot)
    model = model_result.model_dump()
    valid_categories = ("社会民生", "科技互联网", "商业财经", "公共政策", "文娱体育", "其他")
    if model["category"] not in valid_categories:
        raise DeepSeekAPIError(502, "DeepSeek 返回的热点类别无效")
    if model["attention_level"] not in ("high", "medium", "low"):
        raise DeepSeekAPIError(502, "DeepSeek 返回的关注等级无效")
    consistent = model["category"] == rules["category"] and model["attention_level"] == rules["attention_level"]
    risk_flags = list(dict.fromkeys(rules["risk_flags"]))
    missing = list(dict.fromkeys(rules["missing_information"] + model["missing_information"]))
    can_auto = bool(model["can_auto_handle"] and rules["can_auto_handle"] and consistent and not risk_flags and not missing)
    return {**model, "provider": "deepseek", "model": DEEPSEEK_MODEL,
            "verification": [
                {"name": "来源与时间完整性", "status": "passed" if not missing else "warning", "detail": "信息完整" if not missing else "待补充：" + "、".join(missing)},
                {"name": "模型与规则一致性", "status": "passed" if consistent else "blocked", "detail": "模型与本地规则一致" if consistent else "模型与本地规则不一致，需人工复核"},
                *rules["verification"],
            ],
            "risk_flags": risk_flags + ([] if consistent else ["模型与规则结论不一致"]),
            "missing_information": missing, "can_auto_handle": can_auto,
            "action_type": "auto_categorize" if can_auto else "human_review",
            "action_suggestion": model["action_suggestion"] if can_auto else "模型结论需人工复核后再应用。"}
