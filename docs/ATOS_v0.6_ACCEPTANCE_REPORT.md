# ATOS v0.6 验收报告

## 本轮目标

让 Execution Center 开始具备 TGE 连接与环境管理能力，但不做 Playwright 自动操作，不做真实发帖。

## 已完成内容

- 新增 TGE 全局配置接口：`GET/PUT /settings/tge`
- TGE API Key masked 返回
- 新增 TgeService Adapter：test/status/sync/start/attach/stop
- TGE Profile 支持 connection/runtime/websocket/debug port 状态字段
- 新增 `execution_tasks`
- 新增 `execution_logs`
- 新增 `replay_files`
- Scheduler DISPATCHED 时创建 Execution Task
- Execution 页面显示接收任务与 Precheck
- Execution Precheck 检查 account、TGE profile、environment id、connection status、account risk
- Dashboard 增加 Execution/TGE 指标

## TGE 配置测试

状态：通过。

接口：

- `GET /settings/tge`
- `PUT /settings/tge`

API Key 不明文返回。

## TGE Profile 测试连接

状态：通过 scaffold。

接口：

- `POST /tge-profiles/{id}/test-connection`
- `GET /tge-profiles/{id}/status`
- `POST /tge-profiles/{id}/sync-status`

默认未开启真实连接测试时，返回 scaffold `SUCCESS`。

## Scheduler → Execution 任务接收

状态：通过。

Scheduler `Run Once` 标记任务 `DISPATCHED` 后，会创建 `execution_tasks`，状态为 `RECEIVED`。

## Execution Precheck 测试

状态：通过。

测试覆盖：

- 成功 precheck → `ENVIRONMENT_READY`
- 缺少 TGE profile → `FAILED / NO_TGE_PROFILE`

## Execution 页面展示

状态：通过 build。

页面展示：

- 待执行任务
- 已接收任务
- 环境检测中
- 等待人工
- 成功
- 失败
- Replay 占位

## 已测试命令

```bash
cd backend
../.venv/bin/python -m alembic upgrade head
../.venv/bin/python -m scripts.seed_data
PYTHONPYCACHEPREFIX=/tmp/atos-pycache ../.venv/bin/python -m unittest tests.test_execution_service tests.test_scheduler_service -v
```

```bash
cd frontend
node node_modules/typescript/bin/tsc --noEmit
node node_modules/vite/bin/vite.js build
```

## 已知问题

- TGE 接口路径仍是 Adapter scaffold，后续可替换为真实 TGE API。
- v0.6 不启动环境、不 attach 浏览器、不打开页面。
- Replay 表已创建，但不生成真实文件。

## 下一步建议

- v0.7 增加 PlaywrightService。
- v0.7 增加 OPEN_PAGE mock/真实 attach 流程。
- v0.7 保存 screenshot/html replay 文件。
