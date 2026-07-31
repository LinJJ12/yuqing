# Frontend Directory Structure

---

## Layout

```text
frontend/
├── public/                 # favicon, public logo
├── scripts/                # node smoke checks (agent-session-check.mjs)
└── src/
    ├── api/client.js       # sole HTTP client
    ├── pages/              # one file per route view
    ├── router/index.js
    ├── components/         # shared UI (VideoScopePicker, layout, …)
    ├── lib/                # non-UI helpers (agentSession, datetime)
    ├── assets/
    ├── App.vue
    ├── main.js
    └── style.css           # global design tokens / shell
```

---

## Ownership

| Path | Responsibility |
|------|----------------|
| `pages/*Page.vue` | Route UI; call `api/` + shared components |
| `api/client.js` | `/api/v1` methods; parse `{ok,data,error}` |
| `lib/agentSession.js` | Multi-conversation agent state + persistence |
| `components/layout/` | Sidebar / shell only |
| `components/VideoScopePicker.vue` | Shared `?bvid=` scope control |

New screen: add lazy route in `router/index.js`, page file, sidebar entry in `AppSidebar.vue`, and update `pages/README.md`.

Legacy redirects: `/sentiment` and `/topics` → `/insights?tab=…` (keep until bookmarks die).

---

## Naming

- Pages: `PascalCase` + `Page.vue` (`InsightsPage.vue`)
- Lib modules: `camelCase.js`
- CSS: prefer existing utility/classes in `style.css`; page-scoped `<style>` when local

---

## Examples

- Insights merge: `pages/InsightsPage.vue`
- Inbox CRUD: `pages/InboxPage.vue`
- Agent isolation: `lib/agentSession.js`
