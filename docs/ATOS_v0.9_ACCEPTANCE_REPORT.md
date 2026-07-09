# ATOS v0.9 验收报告

Version: v0.9

Status: Accepted for local MVP

---

## 本轮目标

把 Engagement Center 从页面占位升级为可运行的互动任务系统，并与 Scheduler / Execution 结构打通。

本轮仍然不自动提交评论。

---

## 已完成内容

- 新增 `engagement_strategies`。
- 新增 `engagement_tasks`。
- 新增 Engagement API：
  - `GET /engagement/strategies`
  - `POST /engagement/strategies`
  - `PUT /engagement/strategies/{id}`
  - `GET /engagement/tasks`
  - `POST /engagement/tasks`
  - `POST /engagement/tasks/{id}/cancel`
  - `POST /engagement/tasks/{id}/retry`
  - `POST /engagement/tasks/{id}/run-mock`
  - `GET /engagement/statistics`
- Engagement 页面支持：
  - 创建 Strategy
  - 创建 Task
  - 查看 Queue
  - Run Mock
  - 查看 Statistics
- Scheduler 支持 `ENGAGEMENT` task type。
- Scheduler 列表显示：
  - `strategy_type`
  - `action_type`
  - `parent_task_id`
- Platform Adapter 增加互动方法结构。
- Dashboard 增加 Engagement 指标。

---

## Engagement Strategy 测试

Seed 默认包含：

- Reddit Silent Browse
- Reddit Reply Warm-up

支持类型：

- SILENT_BROWSE
- LIKE_ONLY
- PROFILE_VISIT
- MIXED_ENGAGEMENT
- REPLY_WARMUP
- CUSTOM

---

## 独立浏览任务测试

Engagement 页面可创建独立任务：

- source_type = POST_POOL
- browse_target_count > 0
- like_target_count = 0
- visit_profile_target_count 可选

创建后进入 Scheduler。

---

## 独立点赞任务测试

Engagement 页面可创建：

- like_target_count > 0

Mock 执行后更新：

- `current_like_count`
- `like_count` statistics

---

## Reply Warm-up 测试

当 Reply Warm-up Strategy 启用时：

- Scheduler 派发 PREPARE_REPLY 前可生成 warm-up engagement task。
- 任务仍进入 Scheduler。
- Engagement 不绕过 Scheduler。

---

## Scheduler 集成测试

Engagement Task 创建后：

- 生成 SchedulerTask。
- `task_type = ENGAGEMENT`
- `payload.action_type = MIXED_ENGAGEMENT`

---

## Execution Mock 测试

v0.9 默认通过 `POST /engagement/tasks/{id}/run-mock` 测试执行闭环。

Mock Mode 会：

- 模拟浏览。
- 模拟点赞。
- 模拟主页访问。
- 更新任务完成数量。
- 标记 `SUCCESS`。

---

## Statistics 更新测试

Run Mock 后会更新：

- browse_count
- like_count
- visit_profile_count
- engagement_success_rate

---

## 已知问题

- 真实平台 Browse / Like / Visit Profile 尚未执行。
- 真实 selector 需要后续按平台维护。
- Reply Warm-up 当前为 MVP 队列插入，后续需要严格阻塞 Reply 直到 Warm-up 完成。

---

## 下一步建议

- v1.0 冻结 Runnable MVP。
- 后续把 Engagement Execution 合并到后台 Worker。
- 后续增加更细的账号冷却和行为间隔。
