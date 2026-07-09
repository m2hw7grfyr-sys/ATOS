# ATOS v0.7 验收报告

Version: v0.7

Status: Accepted for local MVP

---

## 本轮目标

让 Execution Center 具备 Playwright Attach 到 TGE 环境的基础能力，并完成：

- 打开目标页面
- 页面加载检测
- 截图保存
- HTML Snapshot 保存
- 关闭当前 Tab
- Execution 状态回写

本轮不做：

- 自动粘贴评论
- 自动提交评论
- 自动点赞
- 自动关注
- 自动私信

---

## 已完成内容

- 新增 Playwright 配置：
  - `playwright_enabled`
  - `playwright_mock_mode`
  - `playwright_timeout_seconds`
  - `playwright_headless`
  - `playwright_default_wait_ms`
  - `enable_screenshot`
  - `enable_html_snapshot`
  - `enable_auto_close_tab`
  - `enable_replay_capture`
- 新增 `PlaywrightService`。
- 新增 OPEN_PAGE 执行链：
  - `ATTACHING`
  - `ATTACHED`
  - `PAGE_OPENING`
  - `PAGE_LOADED`
  - `SCREENSHOT_SAVED`
  - `HTML_SAVED`
  - `TAB_CLOSED`
  - `SUCCESS`
- 支持 `PLAYWRIGHT_MOCK_MODE=true`。
- Mock Mode 下不需要真实 TGE / Playwright 浏览器即可完成状态流转。
- Replay 文件保存到：
  - `storage/replay/{execution_task_uuid}/screenshot.png`
  - `storage/replay/{execution_task_uuid}/page.html`
- Execution 页面增加：
  - `Run OPEN_PAGE`
  - `Attach`
  - `Close Tab`
- System Settings 增加 Playwright 配置。
- Scheduler 派发 payload 增加 `action_type=OPEN_PAGE` 和 URL。

---

## Playwright 安装测试

`backend/requirements.txt` 已加入：

```text
playwright==1.49.1
```

本地安装命令：

```bash
pip install -r backend/requirements.txt
python -m playwright install chromium
```

Mock Mode 下测试不依赖真实浏览器安装。

---

## Mock Mode 测试

已新增自动化测试：

```text
backend/tests/test_playwright_runner.py
```

测试覆盖：

- Execution Precheck
- Mock Attach
- Mock Open Page
- Mock Screenshot
- Mock HTML Snapshot
- ReplayFile 入库
- Execution Task 标记 `SUCCESS`

---

## Attach 结构测试

当前实现优先读取：

1. `tge_profile.websocket_url`
2. `tge_profile.debug_port`

如果非 Mock Mode 且二者均不存在：

- `execution_tasks.status = ATTACH_FAILED`
- `error_code = ATTACH_INFO_MISSING`

---

## OPEN_PAGE 流程测试

OPEN_PAGE API：

```text
POST /execution/tasks/{id}/run-open-page
```

执行前如任务尚未完成 Precheck，会先运行 Precheck。

成功后：

- `execution_tasks.status = SUCCESS`
- `replay_files.screenshot_path` 写入
- `replay_files.html_path` 写入
- `execution_logs` 记录关键步骤

---

## Screenshot / HTML 保存测试

Mock Mode 会生成：

- 1x1 PNG 占位截图
- 包含目标 URL 的 HTML Snapshot

真实模式会调用 Playwright：

- `page.screenshot(full_page=True)`
- `page.content()`

---

## Tab Close 测试

如果 `enable_auto_close_tab=true`：

- OPEN_PAGE 完成后关闭当前 Tab。
- Execution Logs 写入 `TAB_CLOSED`。

---

## 已知问题

- 真实 TGE attach 仍依赖 TGE 返回可用 `websocket_url` 或 `debug_port`。
- 当前未实现 DOM 平台 Adapter。
- 当前未实现评论框定位。
- 当前未实现评论粘贴或提交。
- Replay UI 仍是基础展示，后续可增加截图预览和 HTML 下载。

---

## 下一步建议

- v0.8 增加 Platform Adapter 接口。
- v0.8 增加 Reddit OPEN_PAGE 页面状态检测。
- v0.9 再讨论人工确认型草稿填充，但仍需保持 human-in-the-loop。
- 后续再引入 Redis/Celery，将 Execution 从 API 同步执行升级为后台 Worker。
