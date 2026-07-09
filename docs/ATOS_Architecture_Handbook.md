# ATOS Architecture Handbook

Version: 0.1

Status: Draft

---

# Chapter 1

Architecture Philosophy

ATOS 是一个 AI Traffic Operating System。

不是 Reddit Bot。

不是 Reply Tool。

不是 Browser Automation。

ATOS 是 Traffic Runtime。

负责：

- Traffic
- AI
- Scheduler
- Execution
- Statistics
- Platform
- Account

形成完整运行时。

---

# Chapter 2

Kernel

ATOS Kernel 是整个系统唯一 Runtime。

Kernel 不负责：

- UI
- AI
- Platform

Kernel 负责：

- Task
- Scheduler
- Execution
- Runtime
- Event
- Health

---

# Chapter 3

Subsystem

整个系统由多个 Subsystem 组成。

Subsystem 彼此独立。

Subsystem 只能通过以下方式通信：

- API
- Event

禁止共享 Repository。

---

# Chapter 4

Runtime

ATOS Runtime 包括：

- Scheduler Runtime
- Execution Runtime
- Worker Runtime
- Event Runtime
- Health Runtime
- Configuration Runtime

所有 Runtime 长期运行。

不得频繁启动。

---

# Chapter 5

Execution Runtime

Execution Runtime 负责：

- Browser
- Environment
- Tab
- Replay

Execution Runtime 不知道：

- Business
- AI
- Strategy

---

# Chapter 6

Scheduler Runtime

Scheduler Runtime 的唯一职责是决定：

- 什么时候
- 哪个账号
- 哪个平台
- 执行什么

Scheduler 永远不执行。

---

# Chapter 7

Event Runtime

所有 Subsystem 通过 Event Runtime 通信。

Event Runtime 负责：

- Publish
- Subscribe
- Retry
- Dead Letter
- Replay
- Trace
- Audit

---

# Chapter 8

Health Runtime

负责：

- Worker
- Redis
- Database
- Playwright
- TGE
- Environment
- Platform
- Health

Dashboard 读取 Health。

---

# Chapter 9

Platform Runtime

Platform 统一使用 Adapter。

Platform 禁止包含业务。

Platform 负责：

- DOM
- Selector
- Locator

---

# Chapter 10

Golden Architecture Rules

## Rule 1

Business 永远不知道 DOM。

## Rule 2

Scheduler 永远不知道 Browser。

## Rule 3

Execution 永远不知道 Business。

## Rule 4

Platform 永远不知道 AI。

## Rule 5

所有 Subsystem 独立。

## Rule 6

所有通信通过 API + Event。

## Rule 7

所有 Runtime 长期运行。

## Rule 8

所有 Task 统一进入 Scheduler。

## Rule 9

所有配置统一进入 Configuration。

## Rule 10

ATOS 永远保持 Platform Agnostic。
