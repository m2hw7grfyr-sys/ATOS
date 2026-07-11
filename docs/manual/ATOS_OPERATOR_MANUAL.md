# ATOS Operator Manual

Version: 0.1

Status: Draft

Audience: Operator / Reviewer / Administrator

---

## 1. 手册目标

本手册用于指导运营人员使用 ATOS。

ATOS 当前是一个 Human-in-the-loop AI Traffic Operating System。

当前版本的核心原则：

- 系统可以采集、分析、评分、排队、生成建议。
- 系统可以准备半自动回复流程。
- 系统不自动提交评论。
- 最终平台提交动作必须由人工完成。

---

## 2. 本地启动

### 2.1 后端启动

```bash
cd /Users/zhangkaikai/Documents/INDEX/ATOS/backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

后端地址：

```text
http://127.0.0.1:8000
```

API 文档：

```text
http://127.0.0.1:8000/docs
```

### 2.2 前端启动

```bash
cd /Users/zhangkaikai/Documents/INDEX/ATOS/frontend
pnpm dev
```

前端地址：

```text
http://127.0.0.1:5173
```

### 2.3 数据库初始化

```bash
cd /Users/zhangkaikai/Documents/INDEX/ATOS
.venv/bin/python scripts/migrate.py
```

### 2.4 初始化演示数据

```bash
cd /Users/zhangkaikai/Documents/INDEX/ATOS
.venv/bin/python scripts/seed.py
```

Seed 可以重复执行，不会重复插入演示数据。

---

## 3. 每日运营流程

推荐每日流程：

```text
Dashboard
↓
Data Center
↓
Post Pool
↓
AI Workspace
↓
Scheduler
↓
Worker Center
↓
Execution
↓
人工确认
↓
Intelligence
```

### 3.1 查看系统状态

进入 Dashboard。

重点查看：

- Posts
- AI Pending
- Scheduler Queue
- Execution Queue
- Workers Online
- Automation Queue
- Recommendations
- Reply Score
- Content Score

如果 Dashboard 出现大量红色状态，先不要继续派发任务。

---

## 4. Data Center

Data Center 用于管理数据源。

当前支持：

- Apify 数据源配置
- Actor Mapping
- 手动运行采集
- 查看采集日志

运营动作：

1. 配置 Apify Token。
2. 添加 Actor ID。
3. 配置 Actor Mapping。
4. 点击 Test。
5. 点击 Run。
6. 到 Post Pool 检查帖子是否入库。

注意：

- 不同 Apify Actor 返回字段不同，必须配置 Mapping。
- 如果字段缺失，帖子可能进入 `INCOMPLETE` 状态。
- 原始数据保存在 `raw_json`，方便排错。

---

## 5. Post Pool

Post Pool 是帖子池。

运营人员在这里查看：

- platform
- title
- author
- community
- status
- source
- raw_json

常见动作：

- Analyze
- Generate Reply
- Send to AI Workspace
- Batch Analyze
- Batch Approve
- Send To Scheduler
- Archive

推荐：

先筛选高相关帖子，再送入 AI Workspace。

---

## 6. AI Workspace

AI Workspace 用于分析帖子和生成回复。

支持：

- Mock Provider
- OpenAI Provider
- Provider Routing
- Prompt Version
- Prompt Preview
- Fallback

运营动作：

1. 查看待分析帖子。
2. 生成分析结果。
3. 生成回复草稿。
4. 查看 Prompt Preview。
5. 编辑不合适的回复。
6. Approve 或 Reject。

Approve 后，回复可以进入 Scheduler。

注意：

- 没有 OpenAI Key 时会走 Mock Provider。
- Fallback 被触发时，应检查 Provider 配置。
- 不要直接复制低质量 Mock 回复用于真实运营。

---

## 7. Scheduler

Scheduler 是任务进入 Execution 的唯一入口。

Scheduler 负责：

- 选择时间
- 选择账号
- 应用延迟
- 进入 Execution Queue

运营人员查看：

- NEW
- QUEUED
- WAITING_ACCOUNT
- WAITING_TIME
- DELAYED
- READY
- DISPATCHED
- FAILED

如果出现 `WAITING_ACCOUNT`：

- 检查 Account Center。
- 检查账号是否 Active。
- 检查 TGE Profile 是否绑定。
- 检查 Daily Limit。
- 检查 Working Windows。
- 检查 risk_status。

---

## 8. Account Center

Account Center 管理账号资产。

重点字段：

- platform
- username
- health_score
- risk_status
- status
- TGE Environment ID
- reply_daily_limit
- current_reply_count

运营动作：

- 添加账号。
- 绑定 TGE Profile。
- 配置 Daily Limit。
- 配置 Working Windows。
- 暂停高风险账号。
- Recalculate Health。

账号状态建议：

- `ACTIVE`：可调度。
- `PAUSED`：暂不使用。
- `DISABLED`：停用。
- `COOLING_DOWN`：只做低风险动作。
- `HIGH / CRITICAL`：不要回复。

---

## 9. Platform Center

Platform Center 管理平台 Adapter。

当前平台：

- Reddit
- X
- Facebook
- Instagram
- TikTok

可查看：

- Adapter Discovery
- Platform Registry
- Capability Check
- Platform Health
- Platform Statistics

Capability 示例：

- REPLY
- BROWSE
- LIKE
- PROFILE_VISIT

注意：

- 业务层不应直接知道 Reddit Selector。
- 平台动作必须通过 Platform Runtime 和 Adapter。
- 如果某个平台不支持 REPLY，任务会被拒绝，而不是强行执行。

---

## 10. Worker Center

Worker Center 用于查看 Automation Runtime。

重点指标：

- Online Workers
- Offline Workers
- Queue
- Running
- Failed
- Retry Pending
- Worker Lost
- Failure Rate

运营动作：

- 查看 Worker Pool。
- 查看 Execution Queue。
- 查看 Alerts。
- 查看 Runtime Metrics。
- 必要时点击 Claim Next 进行演示性 Claim。

注意：

- Worker 掉线后，任务会进入恢复流程。
- 当前 Sprint 使用 Database Lock。
- Redis Lock 是后续生产升级项。

---

## 11. Execution

Execution Center 显示执行任务。

当前执行模式：

```text
SEMI_AUTO
```

半自动回复流程：

```text
Open Post
↓
Find Reply Box
↓
Fill Reply
↓
WAITING_MANUAL
↓
人工在平台点击提交
↓
回到 ATOS 点击 Confirm
↓
SUCCESS
```

重要原则：

- ATOS 当前不自动点击 Comment / Submit。
- 人工必须检查回复内容。
- 人工必须在平台页面手动提交。
- 提交后再回 ATOS 确认。

---

## 12. Engagement

Engagement Center 管理互动策略。

支持：

- Silent Browse
- Like Only
- Profile Visit
- Mixed Engagement
- Reply Warm-up

用途：

- 增加自然行为轨迹。
- 在回复前做预热。
- 降低单一回复行为带来的风险。

注意：

- Engagement 不绕过 Scheduler。
- 所有 Engagement Task 也必须进入 Scheduler。

---

## 13. Intelligence

Intelligence Runtime 用于分析历史表现。

查看：

- Funnel
- Top Strategies
- Top Replies
- Best Accounts
- Best Time
- Platform Ranking
- Recommendations
- Duplicate Reply Detection

运营动作：

1. 查看 Recommendations。
2. 查看 Reply Score。
3. 查看 Best Time。
4. 根据建议调整平台、账号、时间和回复策略。

当前版本：

- 使用本地启发式评分。
- 使用 Mock Embedding。
- 不依赖外部向量库。

---

## 14. System Settings

System Settings 用于配置：

- LLM Providers
- Provider Routing
- Prompt Templates
- Scheduler Settings
- Platform Weights
- TGE Settings
- Playwright Settings

安全规则：

- API Key 不应明文展示。
- 更新 API Key 时，留空表示不修改。
- 生产环境不要提交 `.env`。

---

## 15. 常见问题

### 15.1 前端打不开

检查：

```bash
cd /Users/zhangkaikai/Documents/INDEX/ATOS/frontend
pnpm dev
```

确认访问：

```text
http://127.0.0.1:5173
```

### 15.2 后端打不开

检查：

```bash
cd /Users/zhangkaikai/Documents/INDEX/ATOS/backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

确认访问：

```text
http://127.0.0.1:8000/health
```

### 15.3 页面没有数据

执行：

```bash
cd /Users/zhangkaikai/Documents/INDEX/ATOS
.venv/bin/python scripts/seed.py
```

### 15.4 AI 没有真实回复

检查：

- `OPENAI_API_KEY`
- System Settings / LLM Providers
- Provider 是否 Enabled
- Provider Routing 是否启用

没有真实 Key 时系统会使用 Mock Provider。

### 15.5 Worker 离线

检查：

- Worker 是否启动。
- `WORKER_API_TOKEN` 是否一致。
- Heartbeat 是否正常。
- Worker Center 是否有 Alert。

### 15.6 任务卡在 WAITING_MANUAL

这通常是正常状态。

含义：

- 回复已准备。
- 等待人工在平台提交。

处理：

1. 到浏览器确认内容。
2. 人工点击提交。
3. 回 ATOS 点击 Confirm / Mark Submitted。

---

## 16. 操作红线

当前版本不要做：

- 自动点击 Comment。
- 自动提交评论。
- 自动私信。
- 自动关注。
- 绕过 Scheduler 创建执行任务。
- 绕过 Account Center 修改账号状态。
- 绕过 Platform Adapter 写平台特殊逻辑。

---

## 17. 推荐每日检查清单

- Dashboard 无大量红色异常。
- Data Center 最近采集成功。
- Post Pool 有新帖子。
- AI Workspace 无大量失败任务。
- Scheduler 无大量 WAITING_ACCOUNT。
- Worker Center 至少一个 Worker Online。
- Execution 无异常堆积。
- Account Center 无 Critical 账号继续执行。
- Intelligence 有最新 Recommendations。

---

## 18. 版本边界

当前 ATOS 已具备：

- 本地可运行系统骨架。
- 数据采集链路。
- AI 分析与回复草稿链路。
- Scheduler 队列。
- Account / TGE Profile 管理。
- Execution / Browser / Platform Runtime Scaffold。
- Semi-auto reply preparation。
- Automation Runtime。
- Intelligence Runtime。

当前 ATOS 尚未实现：

- 全自动提交。
- 真实大规模向量库。
- 生产 Redis Lock。
- 完整远程 Worker 执行 loop。
- 每个平台完整真实 Selector 验证。
