# ATOS v1.1 验收报告

Version: v1.1

Status: Accepted for local MVP

---

## 本轮目标

把 Data Center 的 Apify 接入从通用 raw_json 入库升级为可配置 Actor Mapping。

本轮不做：

- TGE 自动执行
- 自动提交评论

---

## 已完成内容

- 新增 `actor_mappings`。
- Post 增加：
  - author_id
  - score
  - comment_count
  - media
  - mapping_id
- Crawl Log 增加：
  - mapping_id
  - mapping_missing
  - incomplete_count
  - validation_failed_count
  - normalization_warning_count
- Apify Normalizer 支持 Mapping。
- 支持 fallback generic normalizer。
- 支持 raw_json_hash 去重。
- 新增 Mapping Test API：
  - `POST /actor-mappings/test`
- Data Center 页面增加 Actor Mapping 配置和 Preview。
- Post Pool 增加 Raw JSON Viewer。

---

## Actor Mapping 创建测试

Seed 默认创建：

```text
Default Reddit Mapping
actor_id = demo/reddit-discovery
platform = reddit
```

---

## Mapping Test API 测试

输入：

- mapping
- raw_item_json

输出：

- normalized_post_preview
- missing_fields
- warnings

---

## Apify 数据解析测试

ApifyService 会按以下顺序处理：

```text
raw item
mapping normalize
validator
deduplicator
posts
```

---

## Fallback Normalizer 测试

如果没有找到 mapping：

- 使用 generic normalizer。
- `crawl_logs.mapping_missing = true`
- `normalization_warning_count + 1`

---

## Incomplete Post 测试

如果缺少 url 或 title：

- 允许入库。
- `posts.status = INCOMPLETE`
- `crawl_logs.incomplete_count + 1`

---

## Raw JSON Viewer 测试

Post Pool 可打开 Raw JSON Viewer 查看原始数据。

---

## 已知问题

- Mapping UI 目前是 MVP 表单。
- 真实 Actor 的字段结构需要逐个配置。
- Post Pool Raw JSON 暂未实现复制按钮。

---

## 下一步建议

- 增加 Mapping Template Library。
- 增加 Actor Mapping 自动推荐。
- 增加字段类型校验。
