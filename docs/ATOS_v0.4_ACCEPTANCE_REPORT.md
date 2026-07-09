# ATOS v0.4 验收报告

## 版本

ATOS v0.4

## 本轮目标

把已批准的 AI 回复接入 Scheduler，形成完整的：

AI Approved → Scheduler Queue → READY → mock DISPATCHED

本轮不包含 TGE、Playwright、自动粘贴、自动评论、Redis/Celery。

## 已完成内容

- 已批准 AI 回复可加入 Scheduler。
- AI Workspace 支持 `Add to Scheduler`。
- AI approve 支持按配置自动入 Scheduler。
- Post Pool 支持批量加入 Scheduler。
- Scheduler 页面支持状态分组。
- Scheduler 支持 `Run Once`。
- Scheduler 支持随机延迟。
- Scheduler 支持平台轮询。
- Scheduler 支持权重轮询。
- Scheduler 支持账号选择。
- Scheduler READY 后写入 mock execution placeholder 并标记 `DISPATCHED`。
- 新增 `scheduler_logs`。
- 新增 `platform_weights`。
- Dashboard 增加 Scheduler 指标。
- System Settings 增加 Scheduler 配置和平台权重配置。

## Scheduler Task 创建测试

测试方式：

- 后端单元测试调用 `queue_approved_ai_task`
- 前端 AI Workspace 手动 `Add to Scheduler`

结果：

- Approved AI Task 成功创建 Scheduler Task。
- 状态进入 `QUEUED`。
- 重复入队会复用已有任务。

## 平台轮询测试

状态：通过基础测试。

实现方式：

- Scheduler 按平台分组。
- 读取 `last_dispatched_platform_id`。
- 多平台任务存在时，优先选择不同于上次派发的平台。

## 权重轮询测试

状态：通过配置与服务实现。

实现方式：

- 平台权重来自 `platform_weights`。
- 开启 `enable_weighted_round_robin` 后按权重生成平台顺序。
- 不硬编码业务平台逻辑。

## 随机延迟测试

测试方式：

- 单元测试设置 `enable_random_delay=true`
- 设置 `min_delay_seconds=5`
- 设置 `max_delay_seconds=5`

结果：

- 任务进入 `DELAYED`
- `delay_seconds=5`
- `earliest_execute_at` 已写入

## Account 选择测试

测试方式：

- 单元测试创建 ACTIVE account
- 设置平台匹配
- 设置今日 reply limit
- 设置当前工作窗口

结果：

- Scheduler 成功选择账号。
- 任务写入 `account_id`。
- 不可用账号会进入 `WAITING_ACCOUNT` 并记录日志。

## 工作时间测试

状态：通过 MVP 版本。

支持格式：

```json
[
  {"day": "MON", "start": "09:00", "end": "12:00"}
]
```

也兼容 seed 中的：

```json
{
  "timezone": "Asia/Shanghai",
  "windows": []
}
```

## Execution 占位测试

结果：

- Scheduler READY 后不会调用 TGE。
- 不会打开浏览器。
- 不会粘贴或提交评论。
- 只在 `payload.execution_placeholder` 写入：`已接收任务，等待未来执行引擎`。
- 状态标记为 `DISPATCHED`。

## 已测试命令

```bash
cd backend
../.venv/bin/python -m alembic upgrade head
../.venv/bin/python -m scripts.seed_data
PYTHONPYCACHEPREFIX=/tmp/atos-pycache ../.venv/bin/python -m unittest tests.test_apify_service tests.test_ai_services tests.test_scheduler_service -v
```

```bash
cd frontend
node node_modules/typescript/bin/tsc --noEmit
node node_modules/vite/bin/vite.js build
```

## 已知问题

- Scheduler 仍是本地数据库状态队列。
- 当前 `Run Once` 一次只处理一个任务。
- 工作时间的 timezone 先保留字段，MVP 判断使用当前运行时。
- Execution 仍是占位，不会连接真实执行引擎。

## 下一步建议

- v0.5 完善 Account Center、TGE Profile、每日限额和工作时间实体表。
- v0.5 让 Scheduler 账号选择读取 Account Center 的正式表。
- 后续再引入后台 worker 或 Redis/Celery。
