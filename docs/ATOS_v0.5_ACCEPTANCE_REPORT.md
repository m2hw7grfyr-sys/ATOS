# ATOS v0.5 验收报告

## 版本

ATOS v0.5

## 本轮目标

完善 Account Center，让账号、平台、TGE Environment、每日限额、工作时间、风险状态真正可配置，为后续 Execution 接入 TGE/Playwright 做准备。

本轮不包含：

- 真实 TGE API 调用
- Playwright
- 自动打开浏览器
- 自动粘贴
- 自动评论

## 已完成内容

- `accounts` 扩展账号资料、风险、冷却字段。
- 新增 `account_limits`。
- 新增 `account_working_windows`。
- 扩展 `tge_profiles`，支持 profile name、environment id、platform、proxy、绑定账号。
- Account Center 页面支持添加、编辑、暂停/恢复、详情、Health 重算。
- Account Center 支持查看 Daily Limits、Working Windows、Risk / Cooling、Usage Today。
- Account Center 支持绑定/解绑 TGE Profile。
- TGE Profile 提供列表、新建、更新 API。
- Scheduler 账号选择读取 Account Center 正式数据。
- Dashboard 增加 Active Accounts、Cooling Accounts、High Risk Accounts、TGE Profiles Active、Accounts Without TGE Binding。
- Seed 增加 4 个账号、4 个 TGE Profile、4 组每日限额、28 个工作时间窗口。

## 账号增删改测试

状态：通过基础验证。

已实现 API：

- `GET /accounts`
- `POST /accounts`
- `GET /accounts/{id}`
- `PUT /accounts/{id}`
- `POST /accounts/{id}/pause`
- `POST /accounts/{id}/resume`
- `POST /accounts/{id}/recalculate-health`

说明：

- 本轮未提供删除账号接口，避免误删账号资产。
- 账号状态支持 `ACTIVE / PAUSED / DISABLED`。

## TGE Profile 绑定测试

状态：通过。

已实现：

- `GET /tge-profiles`
- `POST /tge-profiles`
- `PUT /tge-profiles/{id}`
- `POST /accounts/{id}/bind-tge-profile`
- `DELETE /accounts/{id}/unbind-tge-profile`

Seed 中 4 个账号均绑定 1 个 TGE Profile。

## 唯一绑定约束测试

状态：通过 schema 与 API 双层保护。

规则：

- 一个账号最多绑定一个 TGE Profile。
- 一个 TGE Profile 最多绑定一个账号。
- 后端重复绑定返回 `409`。
- 数据库对 `bound_account_id` 建立唯一索引。

## 每日限额测试

状态：通过。

已实现：

- `GET /accounts/{id}/limits`
- `PUT /accounts/{id}/limits`

Scheduler 选择账号时读取 `account_limits.reply_daily_limit` 与 `current_reply_count`。

## 工作时间测试

状态：通过。

已实现：

- `GET /accounts/{id}/working-windows`
- `PUT /accounts/{id}/working-windows`

支持同一天多个时间段。

Seed 为每个账号创建 7 天全天窗口，便于本地验收。

## Scheduler 账号选择测试

状态：通过。

Scheduler 选择账号时检查：

- `account.status = ACTIVE`
- `risk_status` 不为 `HIGH / CRITICAL`
- `cooling_down_until` 为空或已过期
- 当前时间在 working windows 内
- 今日 reply limit 未超
- platform 匹配
- 已绑定 TGE Profile

如果不满足，会写入 `scheduler_logs`。

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

- Account Center 的 TGE Profile 创建入口当前主要通过 API，页面侧重点是账号绑定和查看。
- Health Score 当前是手动重算的 MVP 规则。
- 工作时间 timezone 字段已保存，调度判断仍使用本地运行时间。
- Scheduler 仍为本地数据库队列。

## 下一步建议

- 增加 TGE Profile 独立管理页面。
- 增加账号操作历史与风险日志。
- 增加每日限额自动 reset job。
- v0.6 再考虑 Execution Runtime 的 TGE attach 占位验证。
