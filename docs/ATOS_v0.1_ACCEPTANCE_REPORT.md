# ATOS v0.1 验收报告

验收日期：2026-07-09

## 已完成内容

- FastAPI 后端可本地启动，API 默认地址为 `http://127.0.0.1:8000`。
- React + TypeScript + Tailwind 前端可本地启动，默认地址为 `http://127.0.0.1:5173`。
- 前端可通过统一 API Client 访问后端。
- Alembic 可在全新 SQLite 数据库中完成建表和升级。
- Seed 脚本可重复执行，并通过版本标记避免重复写入。
- Dashboard 可展示帖子、AI、Scheduler、账号和执行状态摘要。
- Data Center、Post Pool、AI Workspace、Scheduler、Account Center、Execution、Engagement、Statistics、System Settings 均有可用初版页面。
- Data Center 支持保存本地数据源配置。
- Account Center 支持保存账号和 TGE Environment ID。
- Scheduler 支持将已批准的 AI 任务加入本地数据库队列。
- AI Workspace 使用 Mock Provider 展示初版生成与审核流程。
- Statistics 使用统计快照表和 `/statistics` API 展示 Seed 指标。

## Seed 数据

在全新数据库中验证的 Seed 数据如下：

| 数据类型 | 数量 |
| --- | ---: |
| 平台 | 3 |
| 数据源 | 2 |
| 帖子 | 10 |
| AI 任务 | 3 |
| Scheduler 任务 | 3 |
| 账号 | 3 |
| TGE Profile | 2 |
| 统计快照 | 6 |

Seed 数据包含 Reddit、X、Facebook 三个平台。第二次执行 Seed 命令不会重复写入。

## 未完成内容

- 真实 Apify Run 与外部数据采集。
- 真实 LLM Provider 调用。
- Playwright 和 TGE 实际连接。
- 自动填写、提交、投票或消息操作。
- Redis、Celery 和分布式 Worker。
- 多租户、生产级登录、RBAC 权限校验。
- PostgreSQL 生产部署验证。

这些能力已保留配置、字段或页面入口，但不属于 ATOS v0.1 的可运行 MVP 范围。

## 已知问题

- 本地队列基于数据库状态，不具备 Redis 队列的并发和故障恢复能力。
- 当前 AI 输出来自 Mock Provider，不代表真实模型质量。
- API 暂未覆盖完整的自动化单元测试和集成测试；本轮采用全新数据库、HTTP Smoke Test、前端生产构建和浏览器逐页验收。
- 已使用过的开发数据库可能保留人工测试数据。删除本地数据库并重新执行迁移和 Seed，可得到本报告中的精确演示数据数量。

## 启动方式

### 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
alembic upgrade head
python scripts/seed_data.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

完整环境变量和常见问题见仓库根目录 `README.md`。

## 测试过的 API

以下接口均返回 HTTP 200，并符合统一响应结构：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {},
  "trace_id": "..."
}
```

- `GET /health`
- `GET /dashboard/summary`
- `GET /posts`
- `GET /data-sources`
- `GET /ai/tasks`
- `GET /scheduler/tasks`
- `GET /accounts`
- `GET /settings`
- `GET /statistics`

## 测试过的页面

以下页面已在真实浏览器中逐页打开，均非空白、无页面告警且未出现加载失败：

- Dashboard
- Data Center
- Post Pool
- AI Workspace
- Scheduler
- Account Center
- Execution
- Engagement
- Statistics
- System Settings

同时已通过：

- Python 源码编译检查。
- TypeScript 类型检查。
- Vite 生产构建。
- Alembic 全新数据库迁移。
- Seed 精确数量与幂等性检查。

## 下一步建议

1. 为核心 API 和数据库 Service 增加 pytest 自动化测试。
2. 增加 PostgreSQL 和 Docker Compose 的开发环境验收。
3. 实现 Apify Adapter 的测试连接与手动 Run。
4. 在 Mock Provider 稳定后接入第一个可配置 LLM Provider。
5. 保持 Scheduler 是进入 Execution 的唯一任务入口，再逐步开发执行层。
