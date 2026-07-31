# Frontend API Client

---

## Contract

Backend envelope:

```json
{ "ok": true, "data": { } }
{ "ok": false, "error": { "code": "…", "message": "…" } }
```

`client.js` uses Axios with `validateStatus: () => true`. Callers **must** check `res.ok` before using `res.data`.

Base path: Vite proxy `/api/v1`. On proxy 404/502/503/504 (and empty body), retry once against `http://127.0.0.1:8001/api/v1`. Do **not** retry when body already has `ok: false` (avoids double-wait on model 503).

Timeouts: normal `api` 30s; long jobs `slowApi` 600s (sentiment / collect / agent).

---

## Sync rule (required)

Any change to `backend/src/api/*` request/response shape **must** update:

1. `frontend/src/api/client.js`
2. Calling pages / `lib/*`
3. `frontend/src/api/README.md` if the surface area changed

---

## Patterns

```js
const res = await fetchPosts({ q: '食堂', limit: 10 })
if (!res.ok) {
  error.value = res.error?.message || '加载失败'
  return
}
posts.value = res.data.items
```

Prefer named exports (`fetchPosts`, `createPost`) over ad-hoc URLs in pages.

Optional video scope: pass `bvid` when `route.query.bvid` is set (see `VideoScopePicker`).

---

## Forbidden

- Raw `axios.create` / `fetch('http://127.0.0.1:8001/...')` inside pages
- Assuming HTTP 200 means business success
- Putting API keys in frontend env for LLM / Cookie
