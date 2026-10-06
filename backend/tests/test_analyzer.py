from datetime import datetime, timedelta, timezone

from backend.app.analyzer import analyze_hotspot


def hotspot(**overrides):
    item = {
        "title": "开源大模型发布新版推理能力",
        "content_excerpt": "官方发布开源大模型新版，新增人工智能推理能力并公开技术报告。",
        "source_platform": "官方博客",
        "source_url": "https://example.com/model-release",
        "published_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "engagement_count": 1200,
    }
    item.update(overrides)
    return item


def test_rules_high_confidence_candidate_requires_complete_source():
    result = analyze_hotspot(hotspot())
    assert result["category"] == "科技互联网"
    assert result["confidence"] >= 0.8
    assert result["can_auto_handle"] is True
    assert result["missing_information"] == []
    assert not result["risk_flags"]


def test_rules_missing_and_risky_hotspot_requires_human_review():
    result = analyze_hotspot(hotspot(
        source_platform="",
        source_url=None,
        published_at=None,
        content_excerpt="网络传闻称发生伤亡事故，个人信息正在泄露，目前没有官方核实。",
        engagement_count=-1,
    ))
    assert result["can_auto_handle"] is False
    assert result["risk_flags"]
    assert result["missing_information"]
