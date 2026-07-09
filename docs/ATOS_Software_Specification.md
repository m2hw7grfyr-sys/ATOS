# ATOS Software Specification

**Project Name:** AI Traffic Operating System

**Short Name:** ATOS

**Version:** 0.3

**Status:** Draft

**Primary Language:** Chinese

**Source of Truth:** This document is the primary product and system specification for ATOS.

---

## 1. 项目定位

ATOS 是一套 AI Traffic Operating System，不是单一 Reddit 自动回复工具，也不是单一社媒机器人。

ATOS 的目标是统一管理：

- 多平台数据采集
- 多账号运营
- AI 内容分析
- AI 回复生成
- 策略调度
- 浏览器执行
- 账号养成
- 风控
- 统计分析
- 系统配置

回复只是 ATOS 的一个执行动作，不是系统本身。

ATOS 的核心是：

> 数据 → AI 分析 → Strategy → Scheduler → Execution → Statistics → Optimization

---

## 2. 设计原则

### 2.1 Strategy First

ATOS 不直接执行“回复”“点赞”“浏览”等动作。

系统必须先选择 Strategy，再由 Strategy 决定具体动作组合。

Strategy 可以包括：

- Warm-up
- Silent Browse
- Like Only
- Reply
- Brand Exposure
- Education
- Story
- Mixed Engagement

### 2.2 Scheduler First

任何任务进入执行前，必须经过 Scheduler。

禁止任何模块绕过 Scheduler 直接进入 Execution。

Scheduler 负责：

- 平台轮询
- 平台权重
- 账号权重
- 工作时间
- 随机延迟
- 冷却机制
- 风控检查
- 执行顺序
- 任务分发

### 2.3 Platform Agnostic

平台只是 Adapter。

业务代码不得写死 Reddit、Facebook、X、Instagram、TikTok 等平台逻辑。

所有平台差异必须通过 Platform Adapter 处理。

### 2.4 AI Replaceable

所有 AI 模型必须可替换。

系统不得绑定单一 AI Provider。

支持：

- OpenAI
- Anthropic
- Gemini
- Ollama
- Local Model
- Custom API

### 2.5 Configuration First

所有核心行为必须可配置。

包括：

- 平台权重
- 账号权重
- 工作时间
- 每日限额
- 随机延迟
- Prompt
- Model
- Strategy
- 风控规则
- TGE 环境
- Playwright 参数

禁止硬编码业务规则。

---

## 3. 系统一级模块

ATOS 包含以下一级模块：

1. Dashboard
2. Data Center
3. AI Workspace
4. Scheduler
5. Execution
6. Engagement
7. Account Center
8. Statistics
9. System Settings
10. System Architecture
11. Platform Adapters
12. Shared Components

---

## 4. Dashboard

Dashboard 是 ATOS Console 的首页。

Dashboard 的目标是让运营人员在进入系统后，立即看到：

- 今日任务情况
- 今日采集数量
- AI 生成状态
- 待审核数量
- 待执行数量
- 执行成功率
- 账号健康状态
- Scheduler 状态
- TGE 状态
- Playwright 状态
- Apify 状态
- 系统异常
- 转化漏斗

Dashboard 不允许直接访问业务数据库。

Dashboard 必须通过 Statistics Service 和 Health Service 获取数据。

---

## 5. Data Center

Data Center 是所有外部数据进入 ATOS 的统一入口。

第一阶段正式支持 Apify。

Data Center 必须支持：

- 多个 Apify API Token
- 多个 Actor ID
- Actor 备注
- 平台映射
- Input JSON 配置
- 手动采集
- 定时采集
- 采集日志
- 失败重试
- 数据去重
- Parser
- Normalizer
- Post Pool 入库

所有采集内容必须先进入 Post Pool。

禁止 Data Center 直接把内容发送到 AI Workspace 或 Scheduler。

---

## 6. Post Pool

Post Pool 是帖子进入系统后的统一池子。

Post Pool 必须支持：

- 全部平台查看
- 单平台筛选
- 多平台筛选
- 平台轮询排序
- 权重轮询排序
- 按 AI 状态筛选
- 按商业价值筛选
- 按风险等级筛选
- 按是否历史回复筛选
- 按是否重复筛选
- 按是否进入 Scheduler 筛选

当多个平台被选中时，队列排序必须支持平台轮询。

示例：

Reddit、Facebook、X 被同时选中时，排序不应是：

Reddit, Reddit, Reddit, Facebook, Facebook, X

而应支持：

Reddit, Facebook, X, Reddit, Facebook, X

如果某个平台任务耗尽，则跳过该平台继续轮询。

---

## 7. AI Workspace

AI Workspace 负责：

- 帖子内容分析
- 商业价值评分
- 风险评分
- Strategy 推荐
- Prompt 组装
- 回复生成
- 变量注入
- 重复检测
- Fallback
- 人工审核
- 批量审批

AI Workspace 必须标记每条回复的生成来源：

- LLM Generated
- Fallback Model
- Template Generated
- Manual Edited

AI Workspace 必须支持重新生成回复。

---

## 8. Scheduler

Scheduler 是 ATOS 的调度核心。

Scheduler 必须支持：

- FIFO
- Platform Round Robin
- Weighted Round Robin
- Random
- Priority First
- Hybrid Strategy

Scheduler 必须支持随机延迟开关。

随机延迟必须可配置：

- enable_random_delay
- min_delay_seconds
- max_delay_seconds

每个账号必须支持工作时间配置。

工作时间可按星期、时间段、平台设置。

---

## 9. Execution

Execution 负责通过 TGE + Playwright 执行任务。

Execution 必须支持：

- Attach 已开启的 TGE 环境
- 如果环境未开启，则启动环境
- 环境保持常驻
- 当前任务完成后关闭当前 Tab
- 不关闭整个 TGE 环境
- 执行前检查登录状态
- 检查帖子是否存在
- 检查评论框是否可用
- 检查是否出现验证码或限制
- 保存截图
- 保存 Replay 日志

半自动模式：

- 自动打开页面
- 自动定位评论框
- 自动粘贴内容
- 等待人工点击提交
- 提交后关闭当前 Tab
- 打开下一任务

全自动模式：

- 自动完成全部动作
- 仅在配置开启时使用

---

## 10. Engagement

Engagement 是独立互动中心。

Engagement 支持：

- 浏览帖子
- 点赞
- 收藏
- 浏览主页
- 展开评论
- 随机滚动
- 随机停留
- 关键词浏览
- 指定板块浏览
- 回复前预热

半自动模式下，Engagement 应作为独立任务运行。

全自动模式下，Engagement 可以作为 Reply 前置流程。

---

## 11. Account Center

Account Center 管理所有平台账号。

每个账号必须支持：

- 平台
- 用户名
- Profile URL
- TGE Environment ID
- Proxy
- Karma / Followers
- Account Age
- Health Score
- Daily Browse Limit
- Daily Like Limit
- Daily Reply Limit
- Daily DM Limit
- Work Time
- Risk Status
- Cooling Down
- Auto Downgrade

账号异常时，系统必须自动降级，而不是仅依赖人工处理。

---

## 12. Statistics

Statistics 负责全系统统计。

必须支持：

- 平台统计
- 账号统计
- Strategy 统计
- AI 模型统计
- Prompt 统计
- Token 成本统计
- Execution 成功率
- Engagement 成功率
- CTR
- CVR
- 转化漏斗

---

## 13. System Settings

System Settings 是全局配置中心。

必须支持：

- LLM Provider
- Prompt Template
- Platform Config
- TGE Config
- Playwright Config
- Scheduler Defaults
- Engagement Defaults
- API Key
- RBAC
- Audit Log
- Backup / Restore

所有敏感配置必须加密保存。

---

## 14. Developer Rules

开发必须遵守：

- 禁止硬编码平台
- 禁止硬编码模型
- 禁止硬编码 Prompt
- 禁止 Worker 直接调用其他 Worker
- 禁止绕过 Scheduler 执行任务
- 禁止页面直接访问数据库
- 所有操作必须记录 Audit Log
- 所有任务必须有状态机
- 所有外部调用必须有超时和重试
- 所有模块必须支持配置化

---

## 15. 当前文档版本范围

Version 0.1 定义 ATOS 的产品与系统主干。

后续版本将继续补充：

- UI 详细规范
- 数据库字段
- API DTO
- 状态机图
- 事件定义
- Redis Key
- Queue
- 错误码
- 测试规范

---

# PART II Dashboard

---

# Chapter 1 Dashboard

## 1.1 模块定位

Dashboard 是整个 ATOS Console 的默认首页。

Dashboard 不负责业务处理。

Dashboard 负责：

- 展示
- 聚合
- 导航
- 告警

Dashboard 是整个系统的运行驾驶舱（Operation Cockpit）。

所有业务数据均来自其它 Service。

Dashboard 自身禁止直接访问业务数据库。

---

## 1.2 页面目标

运营人员进入系统后的 3 秒内，应能够知道：

- 今天有没有新帖子
- AI 有没有异常
- Scheduler 是否正常
- Execution 是否正常
- 哪些账号异常
- 哪些平台异常
- 哪些任务等待处理
- 今天的数据是否达到目标

Dashboard 的目标：

让运营人员无需进入任何模块即可了解整个系统状态。

---

## 1.3 页面布局

Dashboard 分为九个区域：

- Header
- Sidebar
- Overview Cards
- Pending Queue
- Platform Health
- System Health
- Statistics
- Quick Actions
- Recent Activity

布局如下：

Header

↓

Sidebar + Main

↓

Overview Cards

↓

Statistics

↓

Recent Activity

---

## 1.4 Header

Header 固定高度：

64px

Header 包含：

- Logo
- Global Search
- Notification
- Current Workspace
- Current User
- Theme Switch
- Language
- System Status

所有页面共享 Header。

---

## 1.5 Sidebar

Sidebar 为整个 Console 的一级导航。

包含：

- Dashboard
- Data Center
- Post Pool
- AI Workspace
- Scheduler
- Execution
- Engagement
- Account Center
- Statistics
- Settings

Sidebar 支持：

- 折叠
- 收藏
- 最近访问
- 快捷键

---

## 1.6 Overview Cards

默认显示：

- Today's Posts
- AI Pending
- Pending Review
- Execution Queue
- Today's Reply
- Success Rate
- CTR
- CVR
- Running Accounts
- Online TGE
- Running Workers
- System Health

所有 Card：

支持点击。

点击后进入对应模块。

Card 不允许编辑业务数据。

---

## 1.7 Pending Queue

显示：

- AI Pending
- Review Pending
- Scheduler Pending
- Execution Pending
- Error Queue

每一项：

点击：

进入对应模块。

---

## 1.8 Platform Health

每个平台：

显示：

- Platform
- Status
- Account Count
- Running
- Cooldown
- Error
- Today's Tasks
- Today's Success

默认：

- Reddit
- Facebook
- X
- Instagram
- TikTok
- YouTube
- Quora

后续新增平台无需修改 Dashboard。

---

## 1.9 System Health

展示：

- AI
- Scheduler
- Execution
- Apify
- Redis
- Database
- Worker
- TGE
- Playwright
- Health Service

全部：

绿色：

Healthy

黄色：

Warning

红色：

Error

支持：

点击：

查看详情。

---

## 1.10 Statistics

Dashboard 默认展示：

- Posts
- Replies
- CTR
- CVR
- Conversions
- AI Cost
- Prompt Usage
- Model Usage
- Execution Time
- Reply Success
- Platform Distribution
- Account Distribution

支持：

- Today
- Yesterday
- 7 Days
- 30 Days
- Custom Range

---

## 1.11 Quick Actions

Dashboard 支持：

- Run Crawler
- Generate AI
- Run Scheduler
- Open Execution
- Open Engagement
- Refresh Statistics
- Restart Worker
- Reload Config

Quick Actions：

必须支持权限控制。

---

## 1.12 Recent Activity

显示：

最近100条：

- AI
- Scheduler
- Execution
- System
- Platform
- Account
- Config

所有日志：

支持：

点击：

查看详情。

---

## 1.13 Dashboard 数据来源

Dashboard 禁止直接查询：

- posts
- accounts
- scheduler
- execution
- 等业务表

Dashboard 仅允许调用：

- Statistics Service
- Health Service
- Configuration Service
- Audit Service

Dashboard API：

负责：

聚合。

---

## 1.14 Dashboard API

Dashboard：

需要：

GET

/dashboard/summary

GET

/dashboard/statistics

GET

/dashboard/health

GET

/dashboard/activity

Dashboard：

不允许：

POST。

---

## 1.15 Dashboard Cache

Dashboard：

默认：

Redis：

30 秒。

Statistics：

60 秒。

Health：

10 秒。

Notification：

实时。

---

## 1.16 Dashboard 权限

Administrator

全部

Operator

全部运营数据

Reviewer

审核相关

Viewer

只读

Dashboard：

所有按钮：

必须：

RBAC。

---

## 1.17 Dashboard 日志

所有：

- 点击
- 刷新
- 搜索
- 筛选
- 跳转

全部：

Audit Log。

---

## 1.18 Dashboard 性能要求

首次打开：

<2 秒

刷新：

<500ms

所有：

统计：

异步。

禁止：

Dashboard：

等待：

AI。

---

## 1.19 Dashboard 开发原则

Dashboard：

禁止：

业务逻辑。

Dashboard：

禁止：

数据库。

Dashboard：

禁止：

平台判断。

Dashboard：

只负责：

展示。

所有：

计算：

必须：

Service。

==============================================================

# PART III Data Center

---

# Chapter 2 Data Center

## 2.1 模块定位

Data Center 是整个 ATOS 唯一的数据入口（Single Entry）。

所有外部数据：

必须先进入 Data Center。

任何模块：

不得直接采集。

例如：

- AI Workspace
- Scheduler
- Execution

均禁止直接调用：

- Apify
- RSS
- API
- Crawler

Data Center 是整个系统唯一的数据接入层。

---

## 2.2 系统职责

Data Center 负责：

- 数据采集
- 数据标准化
- 数据清洗
- 去重
- 标签
- 统一编号
- 平台识别
- 帖子池入库
- 事件通知

Data Center：

绝不负责：

- AI
- Scheduler
- Execution

---

## 2.3 数据来源

V1：

支持：

- Apify

V2：

增加：

- RSS
- JSON
- Webhook
- CSV
- Manual Import
- Official API

所有来源：

统一：

Source Adapter。

---

## 2.4 Source Adapter

所有采集器：

必须实现：

SourceAdapter Interface

统一接口：

- connect()
- test()
- crawl()
- parse()
- normalize()
- validate()
- close()

新增平台：

不得修改：

Data Center。

仅新增：

Adapter。

---

## 2.5 Apify

支持：

- 多个 Token
- 多个 Workspace
- 多个 Actor
- 多个 Input
- 多个 Dataset
- 多个 Schedule

支持：

- 备注
- 状态
- Owner
- 更新时间
- 失败次数
- 成功率
- 平均耗时

---

## 2.6 Actor 管理

Actor：

必须支持：

- 启用
- 停用
- 测试
- 复制
- 版本
- 备注
- 默认 Input
- 最近运行
- 最近错误

每个 Actor：

绑定：

平台。

例如：

- Reddit
- Facebook
- X
- Instagram
- TikTok

---

## 2.7 Platform Mapping

平台：

不是：

Actor。

Actor：

属于：

平台。

例如：

Platform：

Reddit

↓

Actor：

Search ADHD

Actor：

Search Adderall

Actor：

Search Vyvanse

Actor：

Search Concerta

多个：

Actor。

统一：

进入：

Reddit。

---

## 2.8 Crawl Job

每一次采集：

都是：

Job。

Job：

包含：

- Job ID
- Source
- Platform
- Actor
- Status
- Created Time
- Start Time
- End Time
- Duration
- Result Count
- Duplicate Count
- Error Count

---

## 2.9 数据标准化

所有帖子：

统一：

Post Object。

统一字段：

- Platform
- Community
- Author
- Author ID
- Title
- Content
- URL
- Media
- Published Time
- Language
- Source
- Source Post ID
- Hash
- Tags
- Metadata

禁止：

平台：

自定义字段：

直接进入：

Post Pool。

---

## 2.10 Parser

Parser：

负责：

解析：

原始 JSON。

Parser：

不得：

写数据库。

Parser：

只返回：

Post Object。

---

## 2.11 Normalizer

Normalizer：

负责：

统一：

- 时间
- URL
- 媒体
- 编码
- Emoji
- Markdown
- HTML
- Mention
- Link

所有帖子：

统一格式。

---

## 2.12 Validator

Validator：

负责：

检查：

是否：

合法。

例如：

URL

为空。

标题：

为空。

作者：

为空。

时间：

非法。

全部：

Reject。

---

## 2.13 Deduplicator

重复检测：

第一层：

Platform

+

Source Post ID

第二层：

Hash

第三层：

Embedding

第四层：

Semantic

如果：

重复。

写入：

Duplicate Log。

不进入：

Post Pool。

---

## 2.14 Post UUID

进入：

ATOS：

以后。

统一：

生成：

UUID。

之后：

整个系统：

只使用：

UUID。

禁止：

直接使用：

Platform ID。

---

## 2.15 Tag Engine

Data Center：

负责：

基础标签。

例如：

- Platform
- Community
- Language
- Medication
- Intent
- Question
- Experience
- Review
- Emergency

这些标签：

AI：

继续扩展。

---

## 2.16 Event

成功：

POST_IMPORTED

失败：

POST_IMPORT_FAILED

重复：

POST_DUPLICATED

Parser：

POST_PARSED

Normalizer：

POST_NORMALIZED

Validator：

POST_VALIDATED

事件：

统一：

Event Bus。

---

## 2.17 Retry

采集失败：

支持：

Retry。

默认：

3次。

指数退避。

Retry：

记录：

日志。

---

## 2.18 Dashboard

Dashboard：

显示：

- Today's Import
- Today's Duplicate
- Today's Error
- Today's Job
- Average Duration
- Success Rate

---

## 2.19 Data Center API

GET

/data-center/source

GET

/data-center/job

GET

/data-center/platform

POST

/data-center/run

POST

/data-center/retry

POST

/data-center/test

POST

/data-center/import

---

## 2.20 开发原则

Data Center：

禁止：

AI。

禁止：

Execution。

禁止：

Scheduler。

禁止：

Platform Logic。

禁止：

业务判断。

Data Center：

只负责：

Data。
