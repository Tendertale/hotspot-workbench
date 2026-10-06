# 热点线索研判工作台架构

## 边界与仓库策略

本项目在当前目录作为独立仓库维护，直接在用户自己的仓库创建和提交分支；不 fork 原始仓库，也不把原始仓库作为运行时依赖。SQLite 是唯一持久化存储，不配置 hash 验证；来源去重使用规范化原文链接 `source_key`。

## 分层

```text
Vue 3 + Vite + Tailwind
        │ JSON / X-DeepSeek-API-Key
        ▼
FastAPI 路由（backend/app/main.py）
        ├── Pydantic 请求校验（schemas.py）
        ├── 规则与模型融合（analyzer.py / deepseek.py）
        └── SQLite 数据访问与审计（database.py）
```

模型请求只读取当前线索快照。网络请求完成后才进入 SQLite 写事务；写入分析、人工修改、确认和状态更新都必须使用客户端传来的线索 `version` 做条件更新，失败返回 HTTP 409。

## 数据模型

- `hotspots`：标题、内容摘录、来源平台、原文链接、发布时间、采集时间、互动量、已应用的类别/关注等级、状态和版本。
- `hotspot_analyses`：模型或规则产生的建议、摘要、关键词、实体、置信度、证据、缺失信息、风险、校验结果、分析状态和分析版本。
- `hotspot_events`：创建、分析、人工修改、确认应用、状态更新等审计事件。

线索状态只能按 `pending → tracking → archived` 流转。分析状态按 `generated → modified → confirmed` 流转。分析建议在确认前不会改写线索的已应用类别和关注等级；统计中的 `high_attention`、`by_category` 只读取已应用字段，`pending_review` 和 `auto_eligible` 读取尚未确认的分析建议。

## API 契约

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 服务存活检查 |
| GET | `/api/stats` | 统计已应用结果与待复核建议 |
| GET | `/api/ai/config` | 返回模型配置和密钥仅内存说明 |
| POST | `/api/ai/verify` | 用请求头临时密钥测试 DeepSeek |
| GET | `/api/hotspots` | 服务端分页、搜索、来源、类别、关注等级、状态筛选 |
| POST | `/api/hotspots` | 创建线索，按规范化原文链接去重 |
| GET | `/api/hotspots/{id}` | 详情、分析和审计时间线 |
| POST | `/api/hotspots/{id}/analyze` | 规则或 DeepSeek 分析，检查版本 |
| PATCH | `/api/hotspots/{id}/analysis` | 人工修改建议，检查版本 |
| POST | `/api/hotspots/{id}/analysis/confirm` | 确认建议并应用到线索，检查版本 |
| PATCH | `/api/hotspots/{id}/status` | 跟踪或归档，检查版本 |

API 密钥只从 `X-DeepSeek-API-Key` 读取，前端只放在当前页面内存中；后端不写入数据库、日志或构建产物。模型非法 JSON、缺字段、枚举越界、超时、限流和上游不可用都返回公开安全错误，不把上游正文透传给用户，也不伪装成本地规则成功。

## 工作流与 PR 责任

1. 主 Agent 读取需求、架构、源码和测试，输出 implementation plan，并明确每个文件的唯一所有者。
2. 数据分析责任人先确定字段、分类、时效、风险、去重和统计口径。
3. 后端实现责任人完成 API、规则/模型融合、事务、版本冲突和种子数据。
4. 前端实现责任人完成服务端查询、复核闭环、错误和 409 刷新提示。
5. 测试责任人只修改测试文件，运行后端测试和前端生产构建，不调用真实模型；发现缺陷交回对应实现责任人。
6. Review 责任人独立检查需求覆盖、接口兼容性、并发、密钥、统计口径和可维护性。
7. 主 Agent 集成并执行最终验收：测试、构建、本地部署和浏览器主流程。
8. **PR 创建与提交责任人**：在独立仓库的功能分支上确认工作区、测试、构建和 review 证据，创建 PR，填写变更摘要、验收命令、风险与未解决限制；收到 review 意见后负责补提交并更新 PR，禁止把 fork 原仓库作为交付前提。只有 PR 证据完整、无高优先级未解决问题时，主 Agent 才报告完成。

