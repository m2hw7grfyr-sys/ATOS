# ATOS

ATOS（AI Traffic Operating System）v0.5 本地可运行 MVP。

当前版本包含 FastAPI 后端、React/TypeScript 前端、SQLite 本地数据库、Apify 数据源接入、Post Pool、可配置 AI Provider、AI Approved 到 Scheduler Queue 的调度闭环，以及可配置 Account Center / TGE Profile 绑定。

v0.5 仍然保持 human-in-the-loop：不连接 TGE，不运行 Playwright，不自动粘贴，不自动评论。

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
| Integrations | Apify、Mock Provider、OpenAI Provider（可选） |

## 已实现

- 统一 API 返回结构和 Trace ID
- Dashboard 基础统计
- Data Center 可添加、编辑、测试、运行 Apify 数据源
- Apify Actor Input JSON 透传
- Apify dataset items 拉取、标准化、入库
- Post Pool 显示真实采集帖，并支持 AI actions
- AI Workspace 支持分析、生成回复、重新生成、编辑、批准、拒绝
- LLM Provider 配置中心，支持 Mock / OpenAI / Anthropic / Gemini / Ollama / Custom 类型占位
- API Key 前端 masked 显示，后端不返回明文
- Mock Provider 无 key 可完整跑通
- OpenAI Provider 有 key 时可真实调用，失败自动 fallback 到 Mock
- AI 调用日志、Prompt Template、Analysis Result 数据结构
- Scheduler 数据库状态队列
- AI Approved Reply 可手动或自动加入 Scheduler
- Scheduler 支持随机延迟、平台轮询、权重轮询、账号选择
- Scheduler READY 后仅写入 mock execution placeholder，不执行浏览器
- Account Center 支持账号编辑、暂停/恢复、Health 计算、每日限额、工作时间
- TGE Profile 支持配置和一对一绑定
- Scheduler 账号选择读取 Account Center 正式数据
- Account Center 初版
- Execution、Engagement、Statistics 占位页面

## 目录

```text
ATOS/
├── backend/       FastAPI、SQLAlchemy、Alembic
├── frontend/      React、TypeScript、Tailwind、Vite
├── docs/          产品、工程与验收文档
├── architecture/  架构资产
├── database/      数据库设计资产
├── diagram/       Mermaid 与流程图
├── openapi/       API 契约
└── prompt/        Prompt 与版本记录
```

## 环境要求

- Python 3.9+
- Node.js 18+
- npm 9+ 或 pnpm

## 环境变量

复制示例文件：

```bash
cp .env.example .env
```

| Variable | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | Yes | SQLAlchemy 数据库连接；默认 SQLite |
| `APP_ENV` | Yes | 应用环境，例如 `development` |
| `API_BASE_URL` | Yes | API 对外地址 |
| `VITE_API_BASE_URL` | Yes | 前端访问 API 的地址 |
| `APIFY_TOKEN` | No | Apify Token；也可在 Data Center 单独配置 |
| `APIFY_API_BASE_URL` | No | Apify API 地址 |
| `OPENAI_API_KEY` | No | OpenAI Key；可留空使用 Mock Provider |
| `TGE_API_BASE_URL` | No | TGE 本地 API 地址；v0.3 不连接 |
| `TGE_API_KEY` | No | TGE API Key；v0.3 不使用 |

不要提交真实 `.env`。

## 后端启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cd backend
../.venv/bin/python -m alembic upgrade head
../.venv/bin/python -m scripts.seed_data
../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## 前端启动

新开一个终端：

```bash
cd frontend
npm install
npm run dev
```

Console: http://127.0.0.1:5173

如果 Vite 自动切到其他端口，请同步更新后端 `CORS_ORIGINS` 或改回 5173。

## Apify 使用流程

1. 在 `.env` 填写 `APIFY_TOKEN`，或在 Data Center 新建数据源时填写 Token。
2. 打开 Data Center，点击“新建数据源”。
3. 填写 Actor ID、Actor Name、Platform、Input JSON、Max Items。
4. 点击“测试”，确认 Actor 可访问。
5. 点击“运行”，系统会调用 Actor、读取 dataset items、标准化并写入 `posts`。
6. 打开 Post Pool 查看采集结果。

安全规则：

- 前端不会显示完整 `APIFY_TOKEN`。
- 后端日志不打印完整 Token。
- Actor Input JSON 不做字段硬编码，系统只负责透传。

## AI Provider 使用流程

### Mock Provider

Seed 默认创建 Mock Provider。无需 API Key。

使用方式：

1. 打开 AI Workspace。
2. 选择帖子。
3. 点击 Analyze。
4. 点击 Generate。
5. 编辑草稿。
6. 点击批准或拒绝。

### OpenAI Provider

1. 打开 System Settings。
2. 在 LLM Providers 中新增或编辑 OpenAI Provider。
3. 填写 `api_base_url`、`api_key`、`model_name`。
4. 启用 `use_for_analysis` 和 `use_for_reply`。
5. 设置比 Mock 更高的优先级，例如 `10`。
6. 保存后回到 AI Workspace 运行 Analyze / Generate。

如果 OpenAI 调用失败，系统会自动 fallback 到 Mock Provider，并在 `ai_generation_logs` 记录失败原因。

## Scheduler 使用流程

### 从 AI Workspace 加入 Scheduler

1. 在 AI Workspace 中生成回复。
2. 点击批准。
3. 如果 System Settings 中开启 `Auto Queue Approved`，批准后会自动创建 Scheduler Task。
4. 如果未开启自动入队，可在已批准任务旁点击 `Add to Scheduler`。

### 从 Post Pool 批量加入 Scheduler

Post Pool 顶部提供 `批量加入 Scheduler`。它只会把当前列表中已有 approved reply 的帖子加入队列，不会生成回复，也不会执行浏览器动作。

### 配置随机延迟

打开 System Settings：

1. 勾选 `Random Delay`。
2. 设置 `Min Delay` 和 `Max Delay`。
3. Scheduler Run Once 时，任务会先进入 `DELAYED`。
4. 系统会写入 `delay_seconds` 和 `earliest_execute_at`。

### 配置平台权重

打开 System Settings 的 `Platform Weights`：

- Reddit 默认 50
- Facebook 默认 30
- X 默认 20
- Instagram 默认 15
- TikTok 默认 10

启用 `Weighted Round Robin` 后，Scheduler 会按权重生成平台调度顺序。平台来自数据库，不硬编码业务逻辑。

### 运行 Scheduler 一次

打开 Scheduler 页面，点击 `Run Once`。

当前 v0.4 行为：

1. 从 `NEW / QUEUED` 中选择任务。
2. 根据平台轮询或权重轮询选择下一个平台任务。
3. 如开启随机延迟，则写入延迟并进入 `DELAYED`。
4. 选择可用账号。
5. 标记 `READY`。
6. 立即写入 mock execution placeholder。
7. 标记 `DISPATCHED`。

Execution 页面只显示“已接收任务，等待未来执行引擎”，不会连接 TGE 或 Playwright。

## Account Center 使用流程

### 添加账号

1. 打开 Account Center。
2. 点击“添加账号”。
3. 选择平台，填写 username、display name、profile url。
4. 设置 risk status、reply daily limit、current reply count。
5. 配置一个工作时间窗口。
6. 保存。

### 绑定 TGE Profile

1. 在 Account Center 点击某个账号的“详情”。
2. 在 TGE Profile 区域选择未绑定或当前账号已绑定的 Profile。
3. 点击“绑定”。
4. 如需解除绑定，点击“解绑”。

绑定规则：

- 一个账号最多绑定一个 TGE Profile。
- 一个 TGE Profile 最多绑定一个账号。
- 前端过滤已绑定 Profile。
- 后端用唯一约束和 409 错误防止重复绑定。

### 配置每日限额

账号表单中可配置 `reply_daily_limit` 和 `current_reply_count`。

后端已提供完整接口：

- `GET /accounts/{id}/limits`
- `PUT /accounts/{id}/limits`

当前 Scheduler 选择账号时会检查 reply daily limit。

### 配置工作时间

账号表单中可配置一个 MVP 工作窗口。

后端支持同一天多个时间段：

```json
[
  {"day_of_week": "MON", "start_time": "09:00", "end_time": "12:00", "timezone": "Asia/Shanghai", "enabled": true}
]
```

### Scheduler 如何选择账号

Scheduler 选择账号时必须满足：

- `account.status = ACTIVE`
- `risk_status` 不为 `HIGH / CRITICAL`
- `cooling_down_until` 为空或已过期
- 当前时间在 enabled working window 内
- 今日对应动作限额未超
- 平台匹配
- 已绑定 TGE Profile

不满足时不会选择该账号，并写入 `scheduler_logs`。

## 常用 API

- `GET /health`
- `GET /dashboard/summary`
- `GET|POST /data-sources`
- `PUT /data-sources/{id}`
- `POST /data-sources/{id}/test`
- `POST /data-sources/{id}/run`
- `GET /data-sources/{id}/logs`
- `GET /posts?platform=&source_id=&status=`
- `GET /ai/tasks`
- `POST /ai/tasks/{post_id}/analyze`
- `POST /ai/tasks/{post_id}/generate-reply`
- `POST /ai/tasks/{task_id}/regenerate`
- `POST /ai/tasks/{task_id}/approve`
- `POST /ai/tasks/{task_id}/reject`
- `PUT /ai/replies/{reply_id}`
- `POST /scheduler/tasks/from-approved`
- `POST /scheduler/tasks/bulk-from-approved`
- `POST /scheduler/tasks/{id}/cancel`
- `POST /scheduler/tasks/{id}/retry`
- `POST /scheduler/run-once`
- `GET /scheduler/logs`
- `GET /settings/scheduler`
- `PUT /settings/scheduler`
- `GET /settings/platform-weights`
- `PUT /settings/platform-weights`
- `GET /settings/llm-providers`
- `POST /settings/llm-providers`
- `PUT /settings/llm-providers/{id}`
- `GET|POST /scheduler/tasks`
- `POST /scheduler/tasks/from-approved`
- `GET|POST /accounts`
- `GET /accounts/{id}`
- `PUT /accounts/{id}`
- `POST /accounts/{id}/pause`
- `POST /accounts/{id}/resume`
- `POST /accounts/{id}/recalculate-health`
- `POST /accounts/{id}/bind-tge-profile`
- `DELETE /accounts/{id}/unbind-tge-profile`
- `GET /accounts/{id}/limits`
- `PUT /accounts/{id}/limits`
- `GET /accounts/{id}/working-windows`
- `PUT /accounts/{id}/working-windows`
- `GET /tge-profiles`
- `POST /tge-profiles`
- `PUT /tge-profiles/{id}`
- `GET /settings`
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

## Seed 数据

`python -m scripts.seed_data` 可重复执行；脚本使用版本标记避免重复插入。全新数据库将生成：

- 3 个平台
- 2 个 Apify 数据源
- 10 条帖子
- 3 个 AI 任务及回复
- 2 个 LLM Provider
- 2 个 Prompt Template
- 3 个 Scheduler 任务
- 4 个账号
- 4 个 TGE Profile
- 4 组每日限额
- 28 个工作时间窗口
- 6 条统计快照

## v0.5 边界

- 不做 TGE 连接。
- 不做 Playwright 执行。
- 不自动粘贴评论框。
- 不自动评论、点赞、私信、发帖。
- 不引入 Redis/Celery。
- 不做 Embedding 相似度。
- 不做复杂 Prompt 版本管理。

## 常见问题

### 前端显示 API 不可用

确认后端运行在 `http://127.0.0.1:8000`，并检查：

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

修改前端环境变量后需要重启 Vite。

### 端口已被占用

先关闭旧进程，或为 Uvicorn/Vite 指定其他端口，并同步更新 `VITE_API_BASE_URL` 和 `CORS_ORIGINS`。

### 为什么没有真实 OpenAI 调用

默认 Mock Provider 优先可用。要真实调用，请在 System Settings 中启用 OpenAI Provider 并填写 API Key。

### SQLite 文件在哪里

按 README 命令从 `backend/` 启动时，默认数据库位于 `backend/atos.db`。该文件已被 `.gitignore` 排除。
