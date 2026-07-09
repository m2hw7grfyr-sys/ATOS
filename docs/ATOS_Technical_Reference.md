# ATOS Technical Reference

**Version:** 0.1

**Status:** Draft

本文档用于记录 ATOS 的数据库、API、DTO、事件、队列、Redis、错误码、部署与开发规范。

后续所有技术细节统一维护在此文件。

---

## 1. 技术栈初始建议

Backend:

- Python FastAPI

Frontend:

- React
- TailwindCSS

Database:

- PostgreSQL
- SQLite only for local MVP

Cache:

- Redis

Queue:

- Redis Queue / Celery / RQ

Browser Automation:

- Playwright

Fingerprint Browser:

- TGE Browser

Data Source:

- Apify

LLM:

- OpenAI
- Anthropic
- Gemini
- Ollama
- Custom API

---

## 2. 核心数据库分组

- platform
- data_center
- post_pool
- ai_workspace
- scheduler
- execution
- engagement
- account_center
- statistics
- system_settings
- audit_log

---

## 3. 核心事件

- POST_IMPORTED
- POST_NORMALIZED
- AI_ANALYSIS_COMPLETED
- REPLY_GENERATED
- REPLY_APPROVED
- TASK_QUEUED
- TASK_DISPATCHED
- EXECUTION_STARTED
- EXECUTION_COMPLETED
- EXECUTION_FAILED
- ACCOUNT_COOLDOWN
- ACCOUNT_RECOVERED

---

## 4. 核心队列

- data_import_queue
- ai_analysis_queue
- reply_generation_queue
- scheduler_queue
- execution_queue
- engagement_queue
- statistics_queue

---

## 5. 错误码前缀

- DC: Data Center
- AI: AI Workspace
- SCH: Scheduler
- EXE: Execution
- ENG: Engagement
- ACC: Account Center
- STA: Statistics
- SET: System Settings
- PLA: Platform Adapter
- SYS: System

---

## 6. API 统一返回结构

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {},
  "trace_id": "string"
}
```
