import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .analyzer import analyze_hotspot
from .database import Database, DuplicateSource, InvalidTransition, VersionConflict
from .deepseek import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DeepSeekAPIError,
    analyze_with_deepseek,
    verify_deepseek_key,
)
from .schemas import AnalysisConfirm, AnalysisEdit, AnalysisRun, HotspotCreate, HotspotStatusUpdate


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _handle_database_error(error: Exception) -> None:
    if isinstance(error, VersionConflict):
        raise HTTPException(status_code=409, detail="线索已被其他操作更新，请刷新后重试") from error
    if isinstance(error, DuplicateSource):
        raise HTTPException(status_code=409, detail="该原文链接已录入，不能重复创建") from error
    if isinstance(error, InvalidTransition):
        raise HTTPException(status_code=409, detail=str(error)) from error
    raise error


def create_app(db_path: Optional[str] = None, seed_data: bool = True) -> FastAPI:
    resolved_db_path = db_path or os.getenv("TICKET_DB_PATH", str(PROJECT_ROOT / "data" / "tickets.db"))
    database = Database(resolved_db_path)
    database.initialize()
    seeded_ids = database.seed() if seed_data else []
    for hotspot_id in seeded_ids[:2]:
        hotspot = database.get_hotspot(hotspot_id)
        if hotspot:
            database.save_analysis(hotspot_id, analyze_hotspot(hotspot), hotspot["version"], actor="演示数据初始化")

    app = FastAPI(title="热点线索研判工作台 API", version="2.0.0")
    app.state.database = database
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["system"])
    def health():
        return {"status": "ok", "service": "hotspot-workbench"}

    @app.get("/api/stats", tags=["hotspots"])
    def get_stats():
        return database.stats()

    @app.get("/api/ai/config", tags=["analysis"])
    def get_ai_config():
        return {"provider": "deepseek", "base_url": DEEPSEEK_BASE_URL, "model": DEEPSEEK_MODEL,
                "key_persistence": "memory_only", "fallback_mode": "rules"}

    @app.post("/api/ai/verify", tags=["analysis"])
    async def verify_ai_connection(api_key: Optional[str] = Header(default=None, alias="X-DeepSeek-API-Key")):
        if not api_key or len(api_key.strip()) < 16:
            raise HTTPException(status_code=400, detail="请输入有效的 DeepSeek API 密钥")
        try:
            return await verify_deepseek_key(api_key.strip())
        except DeepSeekAPIError as error:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error

    @app.get("/api/hotspots", tags=["hotspots"])
    def list_hotspots(
        search: str = "", source_platform: str = "", category: str = "", attention_level: str = "",
        status_filter: str = Query(default="", alias="status"), analysis_status: str = "",
        page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
    ):
        return database.list_hotspots(search=search.strip(), source_platform=source_platform.strip(), category=category,
                                      attention_level=attention_level, status=status_filter,
                                      analysis_status=analysis_status, page=page, page_size=page_size)

    @app.post("/api/hotspots", status_code=status.HTTP_201_CREATED, tags=["hotspots"])
    def create_hotspot(payload: HotspotCreate):
        try:
            return database.create_hotspot(payload.model_dump())
        except Exception as error:
            _handle_database_error(error)

    @app.get("/api/hotspots/{hotspot_id}", tags=["hotspots"])
    def get_hotspot(hotspot_id: int):
        hotspot = database.get_hotspot(hotspot_id)
        if hotspot is None:
            raise HTTPException(status_code=404, detail="热点线索不存在")
        return hotspot

    @app.post("/api/hotspots/{hotspot_id}/analyze", tags=["analysis"])
    async def run_analysis(hotspot_id: int, payload: AnalysisRun,
                           api_key: Optional[str] = Header(default=None, alias="X-DeepSeek-API-Key")):
        hotspot = database.get_hotspot(hotspot_id)
        if hotspot is None:
            raise HTTPException(status_code=404, detail="热点线索不存在")
        try:
            if payload.mode == "rules":
                result = analyze_hotspot(hotspot)
            else:
                if not api_key or len(api_key.strip()) < 16:
                    raise HTTPException(status_code=400, detail="请先配置 DeepSeek API 密钥")
                result = await analyze_with_deepseek(hotspot, api_key.strip())
            return database.save_analysis(hotspot_id, result, payload.expected_version,
                                         actor="本地规则分析器" if payload.mode == "rules" else "DeepSeek")
        except HTTPException:
            raise
        except DeepSeekAPIError as error:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        except Exception as error:
            _handle_database_error(error)

    @app.patch("/api/hotspots/{hotspot_id}/analysis", tags=["analysis"])
    def edit_analysis(hotspot_id: int, payload: AnalysisEdit):
        if database.get_hotspot(hotspot_id) is None:
            raise HTTPException(status_code=404, detail="热点线索不存在")
        try:
            return database.update_analysis(hotspot_id, payload.model_dump(exclude_none=True), payload.expected_version)
        except Exception as error:
            _handle_database_error(error)

    @app.post("/api/hotspots/{hotspot_id}/analysis/confirm", tags=["analysis"])
    def confirm_analysis(hotspot_id: int, payload: AnalysisConfirm):
        if database.get_hotspot(hotspot_id) is None:
            raise HTTPException(status_code=404, detail="热点线索不存在")
        try:
            return database.confirm_analysis(hotspot_id, payload.expected_version, payload.review_note)
        except Exception as error:
            _handle_database_error(error)

    @app.patch("/api/hotspots/{hotspot_id}/status", tags=["hotspots"])
    def update_hotspot_status(hotspot_id: int, payload: HotspotStatusUpdate):
        if database.get_hotspot(hotspot_id) is None:
            raise HTTPException(status_code=404, detail="热点线索不存在")
        try:
            return database.update_status(hotspot_id, payload.status, payload.expected_version, payload.note)
        except Exception as error:
            _handle_database_error(error)

    frontend_dist = PROJECT_ROOT / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    return app


app = create_app()
