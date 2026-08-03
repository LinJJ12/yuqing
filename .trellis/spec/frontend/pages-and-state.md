# Pages & Client State

---

## Routing

- History mode via `createWebHistory`
- `meta.title` / `meta.subtitle` drive chrome headers
- `meta.layout`: `public` (no sidebar) vs `app` (shell); `meta.requiresAuth` for workbench routes
- Public: `/` home · `/login`; workbench overview at `/overview` (not `/`)
- Guard (`router.beforeEach`): unauthenticated app routes → `/login?redirect=…`; authenticated `/login` → `/overview` (or safe relative redirect)
- Redirect safety: `lib/auth.js` `safeInternalPath` — only `/…`, reject `//…`
- Session change: `AUTH_CHANGED_EVENT` after `setSession` / `clearSession` (shell username + home CTA)
- API 401 (non-login): `clearSession` + navigate to `/login` when on app layout (`setUnauthorizedHandler` from `main.js`)
- Shareable scope: `?bvid=` on insights / alerts / reports / agent
- Insights tabs: `?tab=sentiment|topics|tools` (default sentiment)

When writing links, preserve existing query keys you do not own (spread `route.query`).

---

## Page responsibilities

| Route | State notes |
|-------|-------------|
| `/` · `/login` | Public layout; session in `lib/auth.js` (`zhiwei.auth.*`); login uses `client.login` + `setSession` |
| `/inbox` | Server pagination + `q`; selection `Set` replaced immutably for Vue reactivity |
| `/insights` | Charts need `nextTick` after tab show; poll analysis-jobs while busy |
| `/alerts` | `tab=review` for hard cases; override updates list |
| `/agent` | **Do not** keep chat only in the page — use `lib/agentSession.js` |

---

## agentSession rules

- Multi-conversation; `localStorage` key `zhiwei.agent.sessions.v3`
- Persist messages / digest / bvid; **do not** persist `loading*` / `*ReqId`
- Bump `chatReqId` / `briefReqId` on send, clear, or delete so late responses cannot write the wrong thread
- Global `state.error` / `notice` only update when `activeId` still matches the request’s conversation

Regression script: `cd frontend && npm run test:agent-session` (`scripts/agent-session-check.mjs`).
Auth guard script: `cd frontend && npm run test:auth-guard` (`scripts/auth-guard-check.mjs`).

---

## UI consistency

- Reuse `VideoScopePicker` for BV scope instead of one-off inputs
- Prefer existing shell buttons / tabs in `style.css` over new purple/glow themes
- Empty states should point to the next step (monitor → insights → reports)
