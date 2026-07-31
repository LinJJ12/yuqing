# Error Handling

> HTTP envelope and exception patterns.

---

## Overview

Public JSON contract (success / failure):

```json
{ "ok": true, "data": { } }
{ "ok": false, "error": { "code": "snake_case", "message": "人类可读中文或英文", "details": { } } }
```

Helpers: `src.lib.http.ok` and `src.lib.http.err` return `JSONResponse`.

`app.py` registers a catch-all `Exception` handler that returns `err("internal_error", …, status=500)` so clients never get opaque plain-text 500s.

---

## Error Types

| Mechanism | When |
|-----------|------|
| `err(code, message, status=…)` | Expected business failures (400/404/409/413/503) |
| `ValueError` from Store/services | Mapped in router to `invalid_request` / `invalid_label` |
| `LookupError` | Missing post → 404 `not_found` |
| `AgentUnavailableError` | Agent/LLM not configured → 503 |
| Unhandled `Exception` | 500 `internal_error` |

Do not invent parallel response shapes in new routers.

---

## Error Handling Patterns

```python
# Good: router maps domain errors
try:
    post = get_store().update_post(post_id, **payload)
except ValueError as exc:
    return err("invalid_request", str(exc), status=400)
if not post:
    return err("not_found", "帖子不存在", status=404)
return ok(post)
```

Services may raise; routers translate. Prefer Chinese user-facing `message` strings already used elsewhere.

---

## API Error Responses

- Validation by FastAPI/Pydantic may return **422** (framework default) — smoke tests accept 400 or 422 for missing upload file
- Upload too large: `413` `file_too_large`
- Duplicate insert: `409` `duplicate` when UNIQUE fails on create

Frontend: always check `res.ok` before reading `res.data`; show `res.error.message`.

---

## Common Mistakes

- Returning bare `{"error": "..."}` without `ok: false`
- Swallowing exceptions and returning empty 200
- Leaking stack traces or absolute local paths in `message` for expected errors
- Forgetting to sync new error codes with UI copy
