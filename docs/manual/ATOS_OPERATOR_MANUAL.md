# ATOS Operator Manual

Version: 1.0.0-rc.1

Status: v1.0 Release Candidate

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

## 17. X 平台操作

X 当前支持标准半自动回复链路。

默认模式：

- `SEMI_AUTO`

系统会：

1. 打开 X 帖子。
2. 定位 Reply 按钮。
3. 打开回复编辑器。
4. 填入 AI 回复内容。
5. 进入 `WAITING_MANUAL`。

系统不会：

- 自动点击 Reply / Post 提交按钮。
- 自动提交评论。
- 自动关注。
- 自动私信。

### 17.1 支持的 X 链接

支持：

- `https://x.com/{username}/status/{tweet_id}`
- `https://twitter.com/{username}/status/{tweet_id}`

系统内部统一为：

- `https://x.com/{username}/status/{tweet_id}`

### 17.2 如何处理 X 帖子

1. 在 Post Pool 找到平台为 `x` 的帖子。
2. 进入 AI Workspace 生成回复。
3. 审核并 Approve Reply。
4. 加入 Scheduler。
5. 由 Execution 执行 `PREPARE_REPLY`。
6. 等待状态变为 `WAITING_MANUAL`。

### 17.3 如何审核 X 回复

重点检查：

- 是否像真实用户。
- 是否过度营销。
- 是否提到敏感内容。
- 是否适合 X 的短文本语境。
- 是否需要删掉链接或 CTA。

建议：

- X 回复尽量短。
- 第一目标是自然互动。
- 不要每条都引流。

### 17.4 如何执行 X 半自动任务

在 Execution 页面：

1. 找到平台为 `x` 的任务。
2. 点击 `Prepare Reply`。
3. 系统打开页面并填入回复。
4. 浏览器中检查内容。
5. 人工在 X 页面点击提交。
6. 回到 ATOS 点击 `Mark Submitted`。

在 Submission 页面：

1. 找到对应 Submission Task。
2. 状态应从 `WAITING_MANUAL` 进入 `VERIFIED`。
3. 查看 Result URL / Timeline。

### 17.5 常见失败原因

`X_LOGIN_REQUIRED`

- X 页面要求登录。
- 处理：检查 TGE Profile 是否仍登录。

`X_RATE_LIMITED`

- X 限流。
- 处理：暂停该账号回复，只保留浏览或冷却。

`X_REPLY_BOX_NOT_FOUND`

- 找不到 Reply 按钮或回复框。
- 处理：检查 selector 是否失效。

`X_EDITOR_NOT_READY`

- 回复编辑器未加载或无法输入。
- 处理：重试一次；仍失败则人工处理。

`X_PAGE_LOAD_FAILED`

- 页面打开失败。
- 处理：检查网络、代理、帖子是否存在。

### 17.6 X 操作红线

不要：

- 开启自动提交。
- 批量连续回复。
- 登录状态异常时继续执行。
- 限流后继续派发 Reply。

---

## 18. Reddit / X 提交确认与恢复

Reddit 和 X 现在共用同一套提交确认流程。

核心状态：

- `WAITING_MANUAL`
- `MANUAL_CONFIRMED`
- `VERIFIED`
- `MANUAL_REQUIRED`
- `FAILED`
- `CANCELLED`

### 18.1 如何处理 WAITING_MANUAL

含义：

- ATOS 已打开帖子。
- ATOS 已填入回复内容。
- 等待你在平台页面人工点击提交。

操作：

1. 打开对应浏览器 Tab。
2. 检查平台、账号、帖子 URL。
3. 检查回复内容。
4. 在 Reddit 或 X 页面人工点击提交。
5. 回到 ATOS Submission 页面。
6. 点击 `Confirm Submitted`。

确认后系统会记录：

- platform
- account_id
- post_id
- reply_task_id
- execution_task_id
- submission_task_id
- operator_id
- confirmed_at
- result_url
- external_reply_id
- verification_status

### 18.2 如何 Mark Failed

当你确认任务不能继续时使用。

操作：

1. 在 Submission 页面找到任务。
2. 点击 `Mark Failed`。
3. 输入失败原因。

常用失败原因：

- `LOGIN_REQUIRED`
- `REPLY_BOX_NOT_FOUND`
- `EDITOR_NOT_READY`
- `RATE_LIMITED`
- `PAGE_LOAD_FAILED`
- `BROWSER_DISCONNECTED`
- `WORKER_OFFLINE`
- `CONTENT_REJECTED`
- `UNKNOWN_ERROR`

系统会同步更新：

- submission task
- execution task
- reply task
- scheduler task
- audit log

### 18.3 如何 Retry

只有可重试任务才允许 Retry。

允许自动重试：

- `BROWSER_DISCONNECTED`
- `WORKER_OFFLINE`

禁止自动重试：

- `LOGIN_REQUIRED`
- `RATE_LIMITED`
- `CONTENT_REJECTED`
- `MANUAL_REQUIRED`

默认：

- Reply Task 最多 1 次重试。
- Submission Task 最多 1 次重试。

如果按钮不可用，查看 `retry_blocked_reason`。

### 18.4 如何查看截图

Submission Detail / contract 中包含标准截图路径：

- before_open
- after_open
- before_reply_box
- after_reply_box
- before_fill
- after_fill
- waiting_manual
- manual_confirmed
- failure

这些路径对应 Replay 文件。

如果还没有真实截图，说明当前任务运行在 Mock/Test Mode。

### 18.5 常见失败原因

`LOGIN_REQUIRED`

- 账号未登录。
- 处理：进入 TGE Profile 重新登录。

`RATE_LIMITED`

- 平台限流。
- 处理：暂停回复，进入冷却。

`REPLY_BOX_NOT_FOUND`

- selector 失效或页面结构变化。
- 处理：检查 Platform Selector Registry。

`EDITOR_NOT_READY`

- 回复框打开但编辑器不可输入。
- 处理：重试一次，仍失败则人工处理。

`BROWSER_DISCONNECTED`

- 浏览器连接中断。
- 处理：允许重试。

`WORKER_OFFLINE`

- Worker 离线。
- 处理：等待 Worker 恢复后重试。

---

## 19. AUTO_ASSISTED 使用说明

### 19.1 模式定义

`AUTO_ASSISTED` 是审核通过后的辅助提交模式。

当前版本只支持 Test Mode 模拟提交。

真实 Reddit / X 提交点击仍然禁用。

默认模式仍然是 `SEMI_AUTO`。

### 19.2 如何开启 AUTO_ASSISTED

进入：

System Settings

↓

Submission Policy

开启：

- Auto Assisted Enabled
- Auto Assisted Test Mode

然后进入：

AUTO_ASSISTED Platform Controls

分别开启：

- reddit
- x

最后到 Account Center 中确认账号：

- `allow_auto_assisted = true`

三层都满足后，任务才可能通过 Policy Check。

### 19.3 如何关闭 AUTO_ASSISTED

进入 System Settings：

- 关闭 Auto Assisted Enabled
- 关闭平台级 AUTO_ASSISTED

或者点击：

Emergency Stop

Emergency Stop 会：

- 关闭全局 AUTO_ASSISTED
- 关闭平台 AUTO_ASSISTED
- 把待执行 AUTO_ASSISTED 任务回退到 `WAITING_MANUAL`
- 写入 Audit Log

### 19.4 如何查看 Policy Blocked

进入 Submission 页面。

查看任务列表的：

- Policy
- Failure
- Retry

Policy 显示阻断原因，例如：

- Global AUTO_ASSISTED is disabled
- Platform AUTO_ASSISTED is disabled
- Account AUTO_ASSISTED permission is disabled
- Outside platform AUTO_ASSISTED time window
- No browser session bound

### 19.5 如何处理 Manual Fallback

常见回退：

`LOGIN_REQUIRED`

- 回到 TGE 环境重新登录。
- 完成后重试或切回人工。

`RATE_LIMITED`

- 停止回复。
- 等待冷却。

`VERIFICATION_FAILED`

- 进入 `MANUAL_REVIEW`。
- 人工确认平台页面是否真的提交成功。

`BROWSER_DISCONNECTED`

- 等待 Browser Runtime 恢复。
- 使用 Retry。

### 19.6 如何运行 AUTO_ASSISTED Now

进入 Submission 页面。

点击：

Run AUTO_ASSISTED Now

系统会：

1. 执行 Policy Check。
2. 如果未通过，回退人工。
3. 如果 Test Mode 通过，模拟提交。
4. 执行 verify。
5. 记录结果和统计。

当前版本不会点击真实 Reddit / X 提交按钮。

---

## 20. 回复模板与漏斗策略

ATOS 当前内置五类中文回复模板：

1. `纯帮助，不引流`
2. `软引导主页`
3. `引导到大号`
4. `直接外链`
5. `不引导，信任建设`

### 20.1 五类模板含义

`纯帮助，不引流`

- 只回答问题。
- 不提主页。
- 不提链接。
- 不提产品。
- 不引导私信。

`软引导主页`

- 先完整回答。
- 结尾只允许轻提示主页或置顶内容。
- 不直接放外链。

`引导到大号`

- 更适合 X。
- 可以自然提到主账号或 thread。
- 不要过度营销。

`直接外链`

- 属于高风险模板。
- 只在平台规则允许时使用。
- 默认不适合 Reddit。

`不引导，信任建设`

- 只做真实互动。
- 重点是共情、经验和补充信息。

### 20.2 Reddit 推荐模板

Reddit 默认推荐：

- `纯帮助，不引流`
- `不引导，信任建设`
- 少量 `软引导主页`

Reddit 默认阻止：

- `直接外链`

### 20.3 X 推荐模板

X 默认允许：

- `纯帮助，不引流`
- `软引导主页`
- `引导到大号`
- 限量 `直接外链`

直接外链仍然是高风险模板，不默认进入 AUTO_ASSISTED。

### 20.4 如何切换模板

进入 AI Workspace。

在顶部选择：

Reply Template

可以选择：

- 系统推荐模板
- 指定某个中文模板

生成或重新生成回复时，系统会把模板指令传给 AI Runtime。

### 20.5 审核时看什么

审核 Reply Task 时重点检查：

- 模板类型
- Funnel Intent
- CTA Strength
- 平台是否允许
- 风险等级
- 推荐理由

如果模板被平台规则禁止，Approve 会失败。

### 20.6 高风险模板提示

高风险模板包括：

- `直接外链`

遇到高风险模板：

- 优先保留 SEMI_AUTO。
- 不要默认开启 AUTO_ASSISTED。
- 检查平台规则和账号状态。

### 20.7 模板效果统计

进入 System Settings。

查看：

Reply Templates

Platform Template Rules

Template Performance

Dashboard 也会显示：

- 今日模板生成数
- 今日模板验证数
- 模板成功率
- 高风险模板使用次数
- 涉及平台数量

详细架构见：

`docs/REPLY_TEMPLATE_STRATEGY.md`

---

## 21. 生产环境使用注意事项

生产环境必须通过 HTTPS 访问。

不要把本地开发地址暴露到公网。

### 21.1 Worker Online / Offline

Dashboard 显示 Worker 状态。

如果 Worker Offline：

1. 检查 Windows Worker 服务是否运行。
2. 检查 `WORKER_API_TOKEN` 是否正确。
3. 检查网络和 Cloudflare Tunnel。
4. 等待 Heartbeat 恢复。

### 21.2 AUTO_ASSISTED 注意事项

生产环境 AUTO_ASSISTED 必须满足：

- Global switch
- Platform switch
- Account switch
- Daily limit
- Time window
- Worker healthy
- Audit enabled
- Screenshot enabled
- Verification enabled

如果任何条件不满足，系统会阻止 AUTO_ASSISTED。

### 21.3 Emergency Stop

进入 System Settings。

点击：

Emergency Stop

系统会：

- 关闭所有 AUTO_ASSISTED。
- 将待执行 AUTO_ASSISTED 任务回退到人工。
- 写入 Audit Log。
- Dashboard 显示 Emergency Stop 状态。

### 21.4 Backup 状态查看

备份文件默认在：

`storage/backups/`

数据库备份：

`storage/backups/postgres/`

Storage 备份：

`storage/backups/storage/`

恢复前必须停止 backend、worker、scheduler。

### 21.5 常见告警处理

`Worker Offline`

- 检查 Worker 服务和 Token。

`Queue Too Long`

- 暂停新增任务，检查 Worker 容量。

`AI Provider Error`

- 切换 Mock Provider 或备用 Provider。

`Submission Failure Rate High`

- 暂停 AUTO_ASSISTED，检查登录态和 Selector。

`Redis Down`

- 检查 Redis 容器和持久化配置。

`Database Backup Failed`

- 检查磁盘空间和 PostgreSQL 凭据。

---

## 22. 推荐每日检查清单

- Dashboard 无大量红色异常。
- Data Center 最近采集成功。
- Post Pool 有新帖子。
- AI Workspace 无大量失败任务。
- Scheduler 无大量 WAITING_ACCOUNT。
- Worker Center 至少一个 Worker Online。
- Execution 无异常堆积。
- Account Center 无 Critical 账号继续执行。
- Intelligence 有最新 Recommendations。
- `/health` 和 `/ready` 正常。
- 最近一次数据库备份存在。

---

## 23. 版本边界

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
- Submission Runtime。
- X Adapter v1 semi-auto flow。
- Cross-platform Submission Hardening。
- AUTO_ASSISTED Test Mode scaffold。
- Reply Template & Funnel Strategy Layer。
- Production Release Foundation。

当前 ATOS 尚未实现：

- 全自动提交。
- 真实 Reddit / X 自动提交点击。
- 真实大规模向量库。
- 生产 Redis Lock。
- 完整远程 Worker 执行 loop。
- 每个平台完整真实 Selector 验证。
