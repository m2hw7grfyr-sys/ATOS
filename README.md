# ATOS

ATOS（AI Traffic Operating System）v0.1 本地可运行骨架。

当前版本实现 FastAPI、React/TypeScript、SQLite、本地数据库队列和十个 Console 页面。平台、模型、数据源、账号及执行环境均采用配置化数据结构；浏览器执行和自动互动仅保留模块边界，不在 v0.1 中自动运行。

## 技术栈

| Layer | Technology |
| --- | --- |
| Backend | Python 3.9+、FastAPI、Pydantic |
| ORM / Migration | SQLAlchemy 2、Alembic |
| Local Database | SQLite |
| Production-ready Database | PostgreSQL（通过 `DATABASE_URL` 切换） |
| Frontend | React 18、TypeScript、Vite |
| UI | TailwindCSS、Lucide Icons |
| Queue | SQLite 数据库状态队列 |
| Future integrations | Apify、Ollama/OpenAI、TGE（v0.1 默认关闭） |

## 已实现

- FastAPI + SQLAlchemy + Alembic
- SQLite 本地开发数据库，可切换 PostgreSQL
- 统一 API 返回结构和 Trace ID
- Dashboard 聚合接口
- Apify 数据源配置模型
- Post Pool
- AI Workspace 初版
- Scheduler 数据库状态队列
- Account Center
- Execution、Engagement、Statistics 占位页面
- System Settings 配置中心初版
- React + TypeScript + Tailwind Console
- 初始化与演示数据脚本

## 目录

```text
ATOS/
├── backend/       FastAPI、SQLAlchemy、Alembic
├── frontend/      React、TypeScript、Tailwind、Vite
├── docs/          产品、工程与架构规范
├── architecture/  架构资产
├── database/      数据库设计资产
├── diagram/       Mermaid 与流程图
├── openapi/       API 契约
└── prompt/        Prompt 与版本记录
```

## 环境要求

- Python 3.9+
- Node.js 18+
- npm 9+

## 快速启动

### 1. 配置环境变量

```bash
cd /path/to/ATOS
cp .env.example .env
```

默认使用 SQLite，不需要安装 PostgreSQL。

## 环境变量

| Variable | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | Yes | SQLAlchemy 数据库连接；默认 `sqlite:///atos.db` |
| `APP_ENV` | Yes | 应用环境，例如 `development` |
| `API_BASE_URL` | Yes | API 对外地址，供部署与工具使用 |
| `VITE_API_BASE_URL` | Yes | 前端构建时使用的 API 地址 |
| `APIFY_TOKEN` | No | Apify Token；v0.1 不发起真实 Run |
| `OPENAI_API_KEY` | No | OpenAI Key；v0.1 使用 Mock Provider |
| `TGE_API_BASE_URL` | No | TGE 本地 API 地址；v0.1 不连接 |
| `TGE_API_KEY` | No | TGE API Key；可以留空 |

API Key 字段可以为空。不要将真实 `.env` 提交到 Git。

### 2. 安装后端

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 3. 初始化数据库

推荐使用 Alembic：

```bash
cd backend
../.venv/bin/python -m alembic upgrade head
../.venv/bin/python -m scripts.seed_data
cd ..
```

也可以运行基础初始化脚本：

```bash
cd backend
../.venv/bin/python -m scripts.init_db
```

### 4. 启动后端

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

### 5. 安装并启动前端

新开一个终端：

```bash
cd /path/to/ATOS/frontend
npm install
npm run dev
```

Console: http://127.0.0.1:5173

## Makefile

也可以使用：

```bash
make install
make init-db
make seed
```

然后分别运行：

```bash
make backend
make frontend
```

## 初始 API

- `GET /health`
- `GET /dashboard/summary`
- `GET|POST /data-sources`
- `GET /posts`
- `GET /ai/tasks`
- `POST /ai/generate-mock`
- `POST /ai/tasks/{id}/approve`
- `GET|POST /scheduler/tasks`
- `POST /scheduler/tasks/from-approved`
- `GET|POST /accounts`
- `GET /settings`
- `PUT /settings/{key}`
- `GET /statistics`

统一返回结构：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {},
  "trace_id": "..."
}
```

## PostgreSQL

将 `.env` 中 `DATABASE_URL` 改为 PostgreSQL URL，并安装对应驱动即可：

```text
DATABASE_URL=postgresql+psycopg://atos:password@localhost:5432/atos
```

之后执行 Alembic migration。业务模型无需修改。

## v0.1 边界

- Data Center 只负责数据源和帖子入池，不直接调用 AI。
- AI Workspace 不直接调用 Execution。
- Scheduler 是进入 Execution 的唯一入口。
- Execution 不决定业务逻辑。
- 页面只访问 API，不直接访问数据库。
- Apify、LLM 和 TGE 均为可配置集成，默认关闭。

## 本地 MVP 流程

1. 在 Data Center 保存 Apify Actor 配置。本版本只保存配置，不运行 Actor。
2. 在 Account Center 添加账号与 TGE Environment ID。本版本不连接 TGE。
3. 在 System Settings 选择 LLM Provider；建议本地测试使用 Mock Provider。
4. 在 AI Workspace 为种子帖子生成 Mock 回复并人工批准。
5. 在 Scheduler 选择已批准 AI Task 和账号，将任务加入数据库队列。
6. 在 Execution Center 查看任务状态。本版本不会执行、粘贴或提交任何内容。

## Seed 数据

`python -m scripts.seed_data` 可重复执行；脚本使用版本标记避免重复插入。全新数据库将生成：

- 3 个平台
- 2 个数据源
- 10 条帖子
- 3 个 AI 任务及回复
- 3 个 Scheduler 任务
- 3 个账号
- 2 个 TGE Profile
- 6 条统计快照

## 常见问题

### `python3` 找不到 `app`

请先进入 `backend/`，并使用模块方式运行：

```bash
cd backend
../.venv/bin/python -m scripts.seed_data
```

### 前端显示 API 不可用

确认后端运行在 `http://127.0.0.1:8000`，并检查 `.env` 中：

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

修改前端环境变量后需要重启 Vite。

### 端口已被占用

先关闭旧进程，或为 Uvicorn/Vite 指定其他端口，并同步更新 `VITE_API_BASE_URL` 和 `CORS_ORIGINS`。

### Seed 重复执行是否会产生重复数据

不会。验收 seed 使用 `seed.version` 标记；检测到相同版本时会安全跳过。

### SQLite 文件在哪里

按 README 命令从 `backend/` 启动时，默认数据库位于 `backend/atos.db`。该文件已被 `.gitignore` 排除。

### 为什么 Apify、LLM、TGE 没有真正执行

这些集成在 v0.1 中只提供配置、数据结构和页面边界。真实网络调用及浏览器执行属于后续版本。
