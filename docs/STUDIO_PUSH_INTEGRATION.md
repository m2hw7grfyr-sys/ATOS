# ATOS Studio Push Integration

## Service Address

ATOS calls Studio from the backend only.

```env
STUDIO_BASE_URL=http://127.0.0.1:8502
STUDIO_PUSH_API_TOKEN=replace-with-a-strong-token
STUDIO_REQUEST_TIMEOUT_SECONDS=10
```

The browser frontend never receives the Studio token and never calls Studio directly.

## Single Push

ATOS frontend:

```text
POST /api/studio/push
```

Request:

```json
{
  "atos_post_id": "1",
  "requested_content_type": "video",
  "target_platforms": ["tiktok"],
  "operator_note": ""
}
```

ATOS backend reads the post from its own database and builds the Studio payload. Frontend-supplied title, body, author, score, or URL are not trusted.

## Batch Push

```text
POST /api/studio/push-batch
```

Request:

```json
{
  "atos_post_ids": ["1", "2", "3"],
  "requested_content_type": "video",
  "target_platforms": ["tiktok"],
  "operator_note": ""
}
```

Rules:

- Maximum 50 posts.
- Empty arrays are rejected.
- Duplicate IDs in one request are de-duplicated.
- One failed post does not roll back the whole batch.

## Status Feedback

ATOS uses:

```text
GET  /api/studio/status/{post_id}
POST /api/studio/status-batch
```

The Post Pool loads Studio status in one batch request for the current page to avoid N+1 calls.

Displayed statuses:

- 未送入
- 待审核
- 已批准
- 已拒绝
- 已归档
- 状态未知
- Studio不可达

## Error Handling

User-facing messages are sanitized:

- Studio不可达: `Studio服务不可达，请检查Studio是否启动`
- Auth failure: `Studio鉴权失败，请检查内部Token配置`
- Post missing: `ATOS中未找到该帖子`
- Validation failure: `Studio请求校验失败`

Tracebacks, tokens, database URLs, proxy settings, browser profile data, worker keys, and account secrets must not be exposed.

## Frontend Operation

Single post:

1. Open Post Pool.
2. Click `送入Studio` on one row.
3. Select content type.
4. Select target platforms.
5. Add optional note.
6. Confirm.

Batch:

1. Select rows or use `当前页全选`.
2. Click `批量送入 Studio`.
3. Fill the same fields.
4. Confirm.
5. Review created / duplicate / failed summary.

## Troubleshooting

`Studio服务不可达`

Studio is not running or `STUDIO_BASE_URL` points to the wrong port.

`Studio鉴权失败`

ATOS `STUDIO_PUSH_API_TOKEN` does not match Studio `STUDIO_PUSH_API_TOKEN`.

`状态未知`

The status query failed but the Post Pool itself remains usable.
