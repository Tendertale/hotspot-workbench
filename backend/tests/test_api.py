from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from backend.app.main import create_app


def payload(url="https://example.com/hotspot-1"):
    return {
        "title": "开源大模型发布新版推理能力",
        "content_excerpt": "官方发布开源大模型新版，新增人工智能推理能力并公开技术报告。",
        "source_platform": "官方博客",
        "source_url": url,
        "published_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "engagement_count": 1200,
    }


def test_hotspot_complete_workflow_and_applied_stats(tmp_path):
    app = create_app(str(tmp_path / "workflow.db"), seed_data=False)
    with TestClient(app) as client:
        created = client.post("/api/hotspots", json=payload())
        assert created.status_code == 201
        hotspot = created.json()
        assert hotspot["hotspot_no"].startswith("HS-")
        assert hotspot["version"] == 1

        listed = client.get("/api/hotspots", params={"search": "大模型"})
        assert listed.json()["total"] == 1

        analyzed = client.post(f"/api/hotspots/{hotspot['id']}/analyze",
                               json={"mode": "rules", "expected_version": 1})
        assert analyzed.status_code == 200
        analysis = analyzed.json()
        assert analysis["provider"] == "rules"
        assert analysis["status"] == "generated"
        version = analysis["hotspot_version"]

        modified = client.patch(f"/api/hotspots/{hotspot['id']}/analysis", json={
            "expected_version": version, "attention_level": "high", "review_note": "人工提升关注等级",
        })
        assert modified.status_code == 200
        assert modified.json()["status"] == "modified"
        version = modified.json()["hotspot_version"]

        confirmed = client.post(f"/api/hotspots/{hotspot['id']}/analysis/confirm", json={
            "expected_version": version, "review_note": "已完成人工复核",
        })
        assert confirmed.status_code == 200
        confirmed_hotspot = confirmed.json()
        assert confirmed_hotspot["category"] == "科技互联网"
        assert confirmed_hotspot["attention_level"] == "high"
        assert confirmed_hotspot["status"] == "tracking"
        assert confirmed_hotspot["analysis"]["status"] == "confirmed"
        repeated_confirm = client.post(f"/api/hotspots/{hotspot['id']}/analysis/confirm", json={
            "expected_version": confirmed_hotspot["version"],
        })
        assert repeated_confirm.status_code == 409

        archived = client.patch(f"/api/hotspots/{hotspot['id']}/status", json={
            "expected_version": confirmed_hotspot["version"], "status": "archived", "note": "跟踪结束",
        })
        assert archived.status_code == 200
        assert archived.json()["status"] == "archived"
        assert len(archived.json()["events"]) >= 5

        stats = client.get("/api/stats").json()
        assert stats["total"] == 1
        assert stats["analyzed"] == 1
        assert stats["archived"] == 1
        assert stats["high_attention"] == 1


def test_validation_duplicate_and_version_conflict(tmp_path):
    app = create_app(str(tmp_path / "validation.db"), seed_data=False)
    with TestClient(app) as client:
        assert client.post("/api/hotspots", json={"title": "短", "content_excerpt": "少"}).status_code == 422
        first = client.post("/api/hotspots", json=payload()).json()
        duplicate = client.post("/api/hotspots", json=payload()).json()
        assert duplicate["detail"] == "该原文链接已录入，不能重复创建"
        stale = client.post(f"/api/hotspots/{first['id']}/analyze",
                            json={"mode": "rules", "expected_version": 99})
        assert stale.status_code == 409
        assert client.get("/api/hotspots/999").status_code == 404


def test_deepseek_mode_requires_key_and_key_is_not_persisted(tmp_path, monkeypatch):
    from backend.app import main as main_module
    from backend.app.analyzer import analyze_hotspot

    received = {}

    async def fake_deepseek(hotspot, api_key):
        received["key"] = api_key
        result = analyze_hotspot(hotspot)
        result.update({"provider": "deepseek", "model": "deepseek-v4-flash"})
        return result

    monkeypatch.setattr(main_module, "analyze_with_deepseek", fake_deepseek)
    db_path = tmp_path / "secret.db"
    app = create_app(str(db_path), seed_data=False)
    with TestClient(app) as client:
        first = client.post("/api/hotspots", json=payload("https://example.com/secret")).json()
        missing = client.post(f"/api/hotspots/{first['id']}/analyze",
                              json={"mode": "deepseek", "expected_version": 1})
        assert missing.status_code == 400
        response = client.post(f"/api/hotspots/{first['id']}/analyze",
                               json={"mode": "deepseek", "expected_version": 1},
                               headers={"X-DeepSeek-API-Key": "sk-test-only-not-persisted"})
        assert response.status_code == 200
    assert received["key"] == "sk-test-only-not-persisted"
    assert b"sk-test-only-not-persisted" not in db_path.read_bytes()


def test_pagination_and_time_engagement_boundaries(tmp_path):
    app = create_app(str(tmp_path / "boundaries.db"), seed_data=False)
    with TestClient(app) as client:
        for index in range(3):
            response = client.post("/api/hotspots", json=payload(f"https://example.com/page-{index}"))
            assert response.status_code == 201
        listed = client.get("/api/hotspots", params={"page": 2, "page_size": 1}).json()
        assert listed["total"] == 3
        assert len(listed["items"]) == 1

        future = payload("https://example.com/future")
        future["published_at"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        future_hotspot = client.post("/api/hotspots", json=future).json()
        analysis = client.post(f"/api/hotspots/{future_hotspot['id']}/analyze",
                               json={"mode": "rules", "expected_version": 1}).json()
        assert "发布时间晚于采集时间" in analysis["risk_flags"]
        assert analysis["can_auto_handle"] is False

        negative = payload("https://example.com/negative")
        negative["engagement_count"] = -1
        assert client.post("/api/hotspots", json=negative).status_code == 422


def test_model_result_becomes_stale_if_hotspot_changes_during_request(tmp_path, monkeypatch):
    from backend.app import main as main_module
    from backend.app.analyzer import analyze_hotspot

    app = create_app(str(tmp_path / "stale.db"), seed_data=False)
    database = app.state.database

    async def fake_deepseek(hotspot, api_key):
        database.update_status(hotspot["id"], "tracking", hotspot["version"])
        return {**analyze_hotspot(hotspot), "provider": "deepseek", "model": "deepseek-v4-flash"}

    monkeypatch.setattr(main_module, "analyze_with_deepseek", fake_deepseek)
    with TestClient(app) as client:
        first = client.post("/api/hotspots", json=payload("https://example.com/stale")).json()
        response = client.post(f"/api/hotspots/{first['id']}/analyze",
                               json={"mode": "deepseek", "expected_version": 1},
                               headers={"X-DeepSeek-API-Key": "sk-stale-result-test"})
        assert response.status_code == 409
