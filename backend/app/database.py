import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class VersionConflict(Exception):
    pass


class DuplicateSource(Exception):
    pass


class InvalidTransition(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    parsed = urlsplit(str(value))
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    port = ":{0}".format(parsed.port) if parsed.port else ""
    query = urlencode(sorted(
        (key, item) for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in ("fbclid", "gclid")
    ))
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), host + port, path, query, ""))


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


class Database:
    def __init__(self, path: str):
        self.path = str(Path(path).resolve())

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS hotspots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hotspot_no TEXT UNIQUE,
                    title TEXT NOT NULL,
                    content_excerpt TEXT NOT NULL,
                    source_platform TEXT NOT NULL DEFAULT '',
                    source_url TEXT,
                    source_key TEXT UNIQUE,
                    published_at TEXT,
                    collected_at TEXT NOT NULL,
                    engagement_count INTEGER,
                    category TEXT NOT NULL DEFAULT '待分类',
                    attention_level TEXT NOT NULL DEFAULT 'low',
                    status TEXT NOT NULL DEFAULT 'pending',
                    version INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS hotspot_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hotspot_id INTEGER NOT NULL UNIQUE REFERENCES hotspots(id) ON DELETE CASCADE,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    category TEXT NOT NULL,
                    attention_level TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    evidence_json TEXT NOT NULL,
                    keywords_json TEXT NOT NULL,
                    entities_json TEXT NOT NULL,
                    can_auto_handle INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    action_suggestion TEXT NOT NULL,
                    missing_information_json TEXT NOT NULL,
                    verification_json TEXT NOT NULL,
                    risk_flags_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'generated',
                    version INTEGER NOT NULL DEFAULT 1,
                    review_note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    confirmed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS hotspot_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hotspot_id INTEGER NOT NULL REFERENCES hotspots(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    detail TEXT NOT NULL DEFAULT '',
                    actor TEXT NOT NULL DEFAULT '系统',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_hotspots_status ON hotspots(status);
                CREATE INDEX IF NOT EXISTS idx_hotspots_category ON hotspots(category);
                CREATE INDEX IF NOT EXISTS idx_hotspot_events_id ON hotspot_events(hotspot_id);
            """)

    @staticmethod
    def _event(connection: sqlite3.Connection, hotspot_id: int, event_type: str,
               title: str, detail: str, actor: str, timestamp: str) -> None:
        connection.execute(
            "INSERT INTO hotspot_events (hotspot_id,event_type,title,detail,actor,created_at) VALUES (?,?,?,?,?,?)",
            (hotspot_id, event_type, title, detail, actor, timestamp),
        )

    @staticmethod
    def _claim(connection: sqlite3.Connection, hotspot_id: int, expected_version: int,
               timestamp: str) -> None:
        cursor = connection.execute(
            "UPDATE hotspots SET version=version+1,updated_at=? WHERE id=? AND version=?",
            (timestamp, hotspot_id, expected_version),
        )
        if cursor.rowcount == 0:
            if connection.execute("SELECT 1 FROM hotspots WHERE id=?", (hotspot_id,)).fetchone():
                raise VersionConflict()
            raise KeyError(hotspot_id)

    @staticmethod
    def _hotspot(row: sqlite3.Row) -> Dict[str, Any]:
        result = dict(row)
        result.pop("source_key", None)
        return result

    @staticmethod
    def _analysis(row: sqlite3.Row, hotspot_version: int) -> Dict[str, Any]:
        result = dict(row)
        for field in ("evidence", "keywords", "entities", "missing_information", "verification", "risk_flags"):
            result[field] = json.loads(result.pop(field + "_json"))
        result["can_auto_handle"] = bool(result["can_auto_handle"])
        result["hotspot_version"] = hotspot_version
        return result

    def create_hotspot(self, payload: Dict[str, Any], collected_at: Optional[str] = None) -> Dict[str, Any]:
        timestamp = collected_at or utc_now()
        source_url = str(payload["source_url"]) if payload.get("source_url") else None
        source_key = normalize_url(source_url)
        published = payload.get("published_at")
        if isinstance(published, datetime):
            published = published.isoformat()
        try:
            with self.connect() as connection:
                cursor = connection.execute("""
                    INSERT INTO hotspots (hotspot_no,title,content_excerpt,source_platform,source_url,source_key,
                        published_at,collected_at,engagement_count,created_at,updated_at)
                    VALUES (NULL,?,?,?,?,?,?,?,?,?,?)
                """, (payload["title"], payload["content_excerpt"], payload.get("source_platform", ""),
                      source_url, source_key, published, timestamp, payload.get("engagement_count"),
                      timestamp, timestamp))
                hotspot_id = int(cursor.lastrowid)
                hotspot_no = "HS-{0}-{1:04d}".format(datetime.now().year, hotspot_id)
                connection.execute("UPDATE hotspots SET hotspot_no=? WHERE id=?", (hotspot_no, hotspot_id))
                self._event(connection, hotspot_id, "created", "热点线索已创建",
                            "来源：{0}".format(payload.get("source_platform") or "未填写"), "系统", timestamp)
        except sqlite3.IntegrityError as error:
            if "source_key" in str(error):
                raise DuplicateSource() from error
            raise
        return self.get_hotspot(hotspot_id)

    def get_hotspot(self, hotspot_id: int) -> Optional[Dict[str, Any]]:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM hotspots WHERE id=?", (hotspot_id,)).fetchone()
            if row is None:
                return None
            analysis = connection.execute("SELECT * FROM hotspot_analyses WHERE hotspot_id=?", (hotspot_id,)).fetchone()
            events = connection.execute("SELECT * FROM hotspot_events WHERE hotspot_id=? ORDER BY id DESC", (hotspot_id,)).fetchall()
        result = self._hotspot(row)
        result["analysis"] = self._analysis(analysis, result["version"]) if analysis else None
        result["events"] = [dict(event) for event in events]
        return result

    def get_analysis(self, hotspot_id: int) -> Optional[Dict[str, Any]]:
        with self.connect() as connection:
            row = connection.execute("""
                SELECT a.*, h.version AS hotspot_version FROM hotspot_analyses a
                JOIN hotspots h ON h.id=a.hotspot_id WHERE a.hotspot_id=?
            """, (hotspot_id,)).fetchone()
        return self._analysis(row, row["hotspot_version"]) if row else None

    def list_hotspots(self, search: str = "", source_platform: str = "", category: str = "",
                      attention_level: str = "", status: str = "", analysis_status: str = "",
                      page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        clauses: List[str] = []
        params: List[Any] = []
        if search:
            clauses.append("(h.title LIKE ? OR h.content_excerpt LIKE ? OR h.hotspot_no LIKE ?)")
            params.extend(["%" + search + "%"] * 3)
        for column, value in (("source_platform", source_platform), ("category", category),
                              ("attention_level", attention_level), ("status", status)):
            if value:
                clauses.append("h." + column + "=?")
                params.append(value)
        if analysis_status == "unanalyzed":
            clauses.append("a.id IS NULL")
        elif analysis_status:
            clauses.append("a.status=?")
            params.append(analysis_status)
        base = " FROM hotspots h LEFT JOIN hotspot_analyses a ON a.hotspot_id=h.id"
        if clauses:
            base += " WHERE " + " AND ".join(clauses)
        with self.connect() as connection:
            total = connection.execute("SELECT COUNT(*) AS total" + base, params).fetchone()["total"]
            rows = connection.execute("""
                SELECT h.*, a.status AS analysis_status, a.confidence AS analysis_confidence,
                    a.provider AS analysis_provider, a.can_auto_handle AS analysis_can_auto_handle
            """ + base + " ORDER BY h.collected_at DESC,h.id DESC LIMIT ? OFFSET ?",
                params + [page_size, (page - 1) * page_size]).fetchall()
        items = [self._hotspot(row) for row in rows]
        for item in items:
            if item["analysis_can_auto_handle"] is not None:
                item["analysis_can_auto_handle"] = bool(item["analysis_can_auto_handle"])
        return {"items": items, "total": int(total), "page": page, "page_size": page_size}

    def save_analysis(self, hotspot_id: int, result: Dict[str, Any], expected_version: int,
                      actor: str = "分析器") -> Dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            self._claim(connection, hotspot_id, expected_version, timestamp)
            existing = connection.execute("SELECT version FROM hotspot_analyses WHERE hotspot_id=?", (hotspot_id,)).fetchone()
            version = int(existing["version"]) + 1 if existing else 1
            fields = ("provider", "model", "category", "attention_level", "summary", "confidence",
                      "evidence_json", "keywords_json", "entities_json", "can_auto_handle", "action_type",
                      "action_suggestion", "missing_information_json", "verification_json", "risk_flags_json")
            values = (result["provider"], result["model"], result["category"], result["attention_level"],
                      result["summary"], result["confidence"], _json(result["evidence"]),
                      _json(result["keywords"]), _json(result["entities"]), int(result["can_auto_handle"]),
                      result["action_type"], result["action_suggestion"],
                      _json(result["missing_information"]), _json(result["verification"]), _json(result["risk_flags"]))
            if existing:
                assignments = ",".join(field + "=?" for field in fields)
                connection.execute("UPDATE hotspot_analyses SET " + assignments +
                                   ",status='generated',version=?,review_note='',updated_at=?,confirmed_at=NULL WHERE hotspot_id=?",
                                   values + (version, timestamp, hotspot_id))
            else:
                columns = ",".join(("hotspot_id",) + fields + ("status", "version", "created_at", "updated_at"))
                placeholders = ",".join("?" for _ in range(len(fields) + 5))
                connection.execute("INSERT INTO hotspot_analyses (" + columns + ") VALUES (" + placeholders + ")",
                                   (hotspot_id,) + values + ("generated", version, timestamp, timestamp))
            self._event(connection, hotspot_id, "analysis_generated", "热点分析已完成",
                        "版本 v{0}，模型 {1}".format(version, result["model"]), actor, timestamp)
        return self.get_analysis(hotspot_id)

    def update_analysis(self, hotspot_id: int, changes: Dict[str, Any], expected_version: int) -> Optional[Dict[str, Any]]:
        timestamp = utc_now()
        allowed = {"category": "category", "attention_level": "attention_level", "summary": "summary",
                   "keywords": "keywords_json", "entities": "entities_json", "can_auto_handle": "can_auto_handle",
                   "action_suggestion": "action_suggestion", "missing_information": "missing_information_json"}
        with self.connect() as connection:
            self._claim(connection, hotspot_id, expected_version, timestamp)
            existing = connection.execute("SELECT * FROM hotspot_analyses WHERE hotspot_id=?", (hotspot_id,)).fetchone()
            if existing is None:
                raise InvalidTransition("请先分析线索")
            if existing["status"] == "confirmed":
                raise InvalidTransition("已确认的分析请重新分析后再修改")
            assignments: List[str] = []
            params: List[Any] = []
            changed: List[str] = []
            for field, column in allowed.items():
                if changes.get(field) is None:
                    continue
                value = changes[field]
                if field in ("keywords", "entities", "missing_information"):
                    value = _json(value)
                elif field == "can_auto_handle":
                    value = int(value)
                assignments.append(column + "=?")
                params.append(value)
                changed.append(field)
            if changes.get("can_auto_handle") is True:
                if json.loads(existing["risk_flags_json"]) or json.loads(existing["missing_information_json"]):
                    raise InvalidTransition("存在风险或缺失信息，不能标记为自动归类")
                if any(item["status"] != "passed" for item in json.loads(existing["verification_json"])):
                    raise InvalidTransition("校验未全部通过，不能标记为自动归类")
            connection.execute("UPDATE hotspot_analyses SET " + ",".join(assignments) +
                               ",status='modified',version=version+1,review_note=?,updated_at=?,confirmed_at=NULL WHERE hotspot_id=?",
                               params + [changes.get("review_note", ""), timestamp, hotspot_id])
            self._event(connection, hotspot_id, "analysis_modified", "热点分析已人工修改",
                        "修改字段：" + "、".join(changed) + ("；备注：" + changes["review_note"] if changes.get("review_note") else ""),
                        "分析员", timestamp)
        return self.get_analysis(hotspot_id)

    def confirm_analysis(self, hotspot_id: int, expected_version: int, review_note: str = "") -> Dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            self._claim(connection, hotspot_id, expected_version, timestamp)
            existing = connection.execute("SELECT * FROM hotspot_analyses WHERE hotspot_id=?", (hotspot_id,)).fetchone()
            if existing is None:
                raise InvalidTransition("请先分析线索")
            if existing["status"] == "confirmed":
                raise InvalidTransition("分析已确认")
            connection.execute("""
                UPDATE hotspot_analyses SET status='confirmed',version=version+1,review_note=?,
                    confirmed_at=?,updated_at=? WHERE hotspot_id=?
            """, (review_note, timestamp, timestamp, hotspot_id))
            connection.execute("""
                UPDATE hotspots SET category=?,attention_level=?,
                    status=CASE WHEN status='pending' THEN 'tracking' ELSE status END WHERE id=?
            """, (existing["category"], existing["attention_level"], hotspot_id))
            self._event(connection, hotspot_id, "analysis_confirmed", "分析已确认并应用",
                        "应用类别 {0}、关注等级 {1}".format(existing["category"], existing["attention_level"])
                        + ("；备注：" + review_note if review_note else ""), "分析员", timestamp)
        return self.get_hotspot(hotspot_id)

    def update_status(self, hotspot_id: int, new_status: str, expected_version: int,
                      note: str = "") -> Dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            self._claim(connection, hotspot_id, expected_version, timestamp)
            row = connection.execute("SELECT status FROM hotspots WHERE id=?", (hotspot_id,)).fetchone()
            old_status = row["status"]
            if (old_status, new_status) not in (("pending", "tracking"), ("tracking", "archived")):
                raise InvalidTransition("状态只能从待研判流转到跟踪中，再流转到已归档")
            connection.execute("UPDATE hotspots SET status=? WHERE id=?", (new_status, hotspot_id))
            self._event(connection, hotspot_id, "status_changed", "线索状态已更新",
                        old_status + " → " + new_status + ("；备注：" + note if note else ""), "分析员", timestamp)
        return self.get_hotspot(hotspot_id)

    def stats(self) -> Dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute("""
                SELECT COUNT(*) AS total,
                    SUM(h.status='pending') AS pending,
                    SUM(h.status='tracking') AS tracking,
                    SUM(h.status='archived') AS archived,
                    SUM(h.attention_level='high') AS high_attention,
                    SUM(a.id IS NOT NULL) AS analyzed,
                    SUM(a.status IN ('generated','modified')) AS pending_review,
                    SUM(a.can_auto_handle=1 AND a.status IN ('generated','modified')) AS auto_eligible
                FROM hotspots h LEFT JOIN hotspot_analyses a ON a.hotspot_id=h.id
            """).fetchone()
            categories = connection.execute("SELECT category,COUNT(*) AS count FROM hotspots GROUP BY category ORDER BY count DESC,category").fetchall()
            sources = connection.execute("SELECT source_platform,COUNT(*) AS count FROM hotspots GROUP BY source_platform ORDER BY count DESC,source_platform").fetchall()
        result = {key: int(row[key] or 0) for key in ("total", "pending", "tracking", "archived",
                                                     "high_attention", "analyzed", "pending_review", "auto_eligible")}
        result["by_category"] = [dict(item) for item in categories]
        result["by_source"] = [dict(item) for item in sources]
        return result

    def seed(self) -> List[int]:
        with self.connect() as connection:
            if connection.execute("SELECT 1 FROM hotspots LIMIT 1").fetchone():
                return []
        now = datetime.now(timezone.utc).replace(microsecond=0)
        samples = [
            ("开源大模型发布新版推理能力", "某科技公司在官方博客发布新版开源大模型，新增推理能力和公开技术报告，开发者可下载试用。", "官方博客", "https://example.com/blog/model-release", 1, 18000),
            ("城市新增夜间公共交通线路", "市交通部门发布公告，新增夜间公交线路，覆盖医院和主要居民区，首班车于本周运行。", "政务公告", "https://example.com/city/night-bus", 2, 1200),
            ("上市公司公布季度业绩", "公司发布季度财报，营业收入和利润数据已在官方公告披露，投资者关注后续经营计划。", "公司公告", "https://example.com/finance/quarterly", 3, 5500),
            ("新款手机与产业政策引发讨论", "新款手机发布后，市场讨论产业政策和补贴影响，多个角度交织，尚需核验主要议题。", "新闻网站", "https://example.com/news/phone-policy", 4, 800),
            ("社区运动场开放时间调整", "社区公告称运动场开放时间调整，居民可以查询新的开放安排与预约说明。", "", None, 5, 30),
            ("上月文娱活动回顾", "主办方发布上月演出活动回顾，包含节目安排和现场照片，相关信息已过时。", "活动官网", "https://example.com/events/last-month", 240, 90),
            ("某消息称发生严重事故", "网络传闻称某地发生伤亡事故，目前尚无官方核实信息，个人身份资料也在传播。", "社交平台", "https://example.com/social/unverified", 2, 9000),
            ("体育赛事公布赛程", "赛事主办方官网发布新赛季赛程，列出比赛时间和参赛队伍，观众可查阅公告。", "赛事官网", "https://example.com/sports/schedule", 6, 2300),
        ]
        ids: List[int] = []
        for title, excerpt, platform, url, hours, engagement in samples:
            published = (now - timedelta(hours=hours)).isoformat()
            ids.append(self.create_hotspot({"title": title, "content_excerpt": excerpt,
                                            "source_platform": platform, "source_url": url,
                                            "published_at": published, "engagement_count": engagement},
                                           collected_at=now.isoformat())["id"])
        return ids
