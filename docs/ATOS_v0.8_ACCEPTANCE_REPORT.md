# ATOS v0.8 验收报告

Version: v0.8

Status: Accepted for local MVP

---

## 本轮目标

在 v0.7 OPEN_PAGE / Screenshot / Close Tab 基础链路上，实现半自动回复准备流程。

系统只负责：

- 打开目标帖子
- 定位评论框
- 填入回复内容
- 进入 `WAITING_MANUAL`
- 等待人工在平台页面点击提交
- 人工回到 ATOS 点击 `Mark Submitted`
- 关闭当前 Tab
- 回写 Execution / Scheduler / Account Usage

系统不做：

- 自动点击 Submit
- 自动私信
- 自动关注
- 自动发帖
- 批量自动提交

---

## 已完成内容

- 新增 `PREPARE_REPLY` action type。
- 新增 `platform_selectors` selector registry。
- 新增 `PlatformAdapter`。
- 新增 reply box 方法：
  - `find_reply_box`
  - `focus_reply_box`
  - `fill_reply_box`
  - `detect_submitted`
  - `detect_comment_disabled`
  - `detect_login_required`
  - `detect_rate_limited`
- 新增 Execution API：
  - `POST /execution/tasks/{id}/prepare-reply`
  - `POST /execution/tasks/{id}/mark-submitted`
  - `POST /execution/tasks/{id}/retry-fill`
- 新增 Platform Selector API：
  - `GET /platform-selectors`
  - `POST /platform-selectors`
  - `PUT /platform-selectors/{id}`
- Execution 页面新增：
  - Reply Content 预览
  - Fill Status
  - Prepare Reply
  - Mark Submitted
  - Retry Fill
  - Close Tab
- System Settings 页面新增 Platform Selector Registry。
- Replay 增加：
  - before fill screenshot
  - after fill screenshot
  - HTML snapshot
  - execution timeline
- Scheduler 成功回写为 `EXECUTED`。
- Account Usage 成功后更新：
  - `current_reply_count + 1`
  - `last_active_at`
  - `health_score + 1`

---

## PREPARE_REPLY 流程测试

Mock Mode 下已通过自动化测试：

```text
backend/tests/test_semi_auto_reply.py
```

覆盖流程：

```text
Scheduler DISPATCHED
Execution RECEIVED
Precheck
Attach
Open Post URL
Find Reply Box
Fill Reply Content
WAITING_MANUAL
Mark Submitted
Close Current Tab
SUCCESS
Scheduler EXECUTED
Account Usage Updated
```

---

## Reply Box 定位测试

Seed 默认包含 Reddit 示例 selector：

```text
platform = reddit
selector_key = reply_box
selector_value = div[contenteditable="true"]
selector_type = css
```

Execution 不直接写 Reddit selector。

所有 selector 通过 `PlatformAdapter` 从 `platform_selectors` 读取。

---

## Fill Reply 测试

Mock Mode：

- 模拟找到 reply box。
- 模拟 focus。
- 模拟填入回复。
- 状态进入 `REPLY_FILLED`。

真实模式：

- 使用 selector locator。
- 通过 `document.execCommand('insertText')` 填入。
- 不点击提交按钮。

---

## WAITING_MANUAL 测试

填入后任务进入：

```text
WAITING_MANUAL
```

前端显示提示：

```text
回复内容已填入浏览器，请在平台页面人工确认并点击提交。提交后回到 ATOS 点击 Mark Submitted。
```

---

## Mark Submitted 测试

`POST /execution/tasks/{id}/mark-submitted`：

- `WAITING_MANUAL -> MANUAL_SUBMITTED`
- 尝试 detect submitted
- 允许人工确认成功
- 写入 `manual_confirmed=true`
- 关闭当前 Tab
- 最终 `SUCCESS`

---

## Close Tab 测试

当前实现只关闭当前 Tab。

不会关闭：

- TGE Environment
- Browser
- Profile

---

## Mock Mode 测试

`PLAYWRIGHT_MOCK_MODE=true` 时：

- 不连接真实 TGE。
- 不打开真实浏览器。
- 仍然生成状态流转。
- 仍然生成 replay placeholder。
- 仍然更新 Scheduler / Account Usage。

---

## 已知问题

- 真实 Reddit selector 可能随页面版本变化，需要后续持续维护。
- 当前 detect submitted 以人工确认为主。
- 当前 Replay UI 仍是基础列表，未做完整截图预览。
- 当前没有后台 Worker，执行动作仍通过 API 同步触发。

---

## 下一步建议

- v0.9 增加 Engagement Strategy 与 Warm-up Workflow。
- 后续增加 Execution Worker，避免长任务阻塞 API 请求。
- 后续增加 Platform Selector 测试器。
- 后续增强 Replay UI，直接预览 before/after screenshot。
