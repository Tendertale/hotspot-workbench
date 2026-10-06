# 热点线索研判工作台

一个可演示的热点线索闭环：录入 → 服务端查询与筛选 → DeepSeek 或本地规则分析 → 人工修改 → 确认应用 → 跟踪 → 归档 → 统计。项目直接在用户自己的独立仓库维护，不需要 fork 原始仓库。

## 功能

- 热点线索录入：标题、内容摘录、来源平台、原文链接、发布时间、采集时间和互动量。
- 服务端分页、搜索和组合筛选，不在浏览器只取固定数量后再筛选。
- 本地规则检查来源与时间完整性、时效、重复来源、异常互动量和人工核验风险。
- 显式选择 DeepSeek 或本地规则；模型输出严格结构化校验，模型和规则不一致时不能自动准入。
- 人工修改与确认应用，所有创建、分析、修改、确认和状态变更写入审计时间线。
- 版本冲突返回 HTTP 409，前端提示刷新后重试。
- 空数据库首次启动自动写入 8 条热点线索演示数据。
- 不配置 hash 验证；重复来源按规范化原文链接判断。自动准入只表示候选，不自动对外发布。

## 启动

环境要求：Python 3.8+、Node.js 18+。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Set-Location frontend
npm install
npm run build
Set-Location ..

python -m uvicorn backend.app.main:app --reload
```

打开 <http://127.0.0.1:8000>，API 文档在 <http://127.0.0.1:8000/docs>。

前端开发模式需要另开一个终端运行后端，然后运行：

```powershell
Set-Location frontend
npm run dev
```

开发页面为 <http://127.0.0.1:5173>，Vite 会把 `/api` 代理到本机后端。

## 配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `TICKET_DB_PATH` | `data/tickets.db` | SQLite 路径，适合隔离测试数据库 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | OpenAI 兼容接口地址 |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 默认模型 |

API 密钥只在当前页面内存中保存，通过 `X-DeepSeek-API-Key` 请求头传给后端；不写入数据库、日志、源码、浏览器持久存储或构建产物。自动测试使用 `httpx.MockTransport`，不会访问真实模型服务。

## 主要 API

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康检查 |
| `GET` | `/api/hotspots` | 分页、搜索、筛选线索 |
| `POST` | `/api/hotspots` | 创建线索 |
| `GET` | `/api/hotspots/{id}` | 查看详情和审计事件 |
| `POST` | `/api/hotspots/{id}/analyze` | `rules` 或 `deepseek` 分析 |
| `PATCH` | `/api/hotspots/{id}/analysis` | 人工修改分析建议 |
| `POST` | `/api/hotspots/{id}/analysis/confirm` | 确认并应用分析结果 |
| `PATCH` | `/api/hotspots/{id}/status` | `pending → tracking → archived` |
| `GET` | `/api/stats` | 统计已应用结果和待复核建议 |
| `POST` | `/api/ai/verify` | 测试临时 DeepSeek 密钥 |

涉及分析、修改、确认和状态更新的请求都必须带 `expected_version`。版本过期时返回 409，避免旧结果覆盖新操作。

## 测试与本地部署验收

后端测试和前端构建：

```powershell
.\.venv\Scripts\python.exe -m pytest
Set-Location frontend
npm run build
Set-Location ..
```

本地部署验收使用生产构建后的 `frontend/dist`，由 FastAPI 静态托管；验证健康检查、页面加载、线索录入、服务端筛选、本地规则分析、人工确认、跟踪和归档。浏览器端不输入真实 API 密钥，DeepSeek 网络行为由自动化测试的本地 fake 覆盖。

架构、数据模型、接口契约和 PR 责任见 [`docs/architecture.md`](docs/architecture.md)；完整验收矩阵见 [`docs/requirements.md`](docs/requirements.md)。
