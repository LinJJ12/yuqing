# Frontend Quality Guidelines

---

## Forbidden

- Hardcoding backend port in page templates (use `api/client.js`)
- Duplicating chart option blobs across pages without extracting on third copy
- Storing secrets or Cookie in `localStorage`
- Breaking `/sentiment` → `/insights` redirects without updating docs
- Letting in-flight agent answers append after `clear` / `deleteConversation`

---

## Required checks before merge (UI-touching)

```powershell
cd frontend
npm run build
npm run test:agent-session
npm run test:auth-guard
```

If API shapes changed: `uv run pytest` from repo root as well.

---

## Review checklist

- [ ] `client.js` methods match backend routes
- [ ] `bvid` / `q` / pagination edge cases handled
- [ ] No console-only error handling for user-visible failures
- [ ] Sidebar + `pages/README.md` updated for new routes
- [ ] Agent session race covered if chat/brief logic changed
