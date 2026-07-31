# Quality Guidelines

> What “good” means for this backend.

---

## Overview

Priorities: keep the API vertical (`backend/src/api` ↔ `frontend/src/api`), keep secrets out of the frontend, and prefer small services over god modules. Product name is **知微**; do not rebrand routes or copy to campus-only framing.

---

## Forbidden Patterns

- Importing or depending on `vendor/` at runtime
- Putting `OPENAI_API_KEY` / `BILIBILI_SESSDATA` in frontend or committing `.env`
- Running transformers / Ollama / SQL inside `api/*.py` route bodies
- Auto-labeling ingest with lexicon sentiment as final truth (normalize skips lexicon labels; BERT/manual/llm own labels)
- Treating lexicon-negative alone as high-severity alerts (`alert_from_post` ignores lexicon)
- Skipping frontend client updates when changing request/response shapes
- Letting Trellis `session_auto_commit` commit without an explicit human request (project sets `session_auto_commit: false`)

---

## Required Patterns

- `from __future__ import annotations` in new Python modules (match neighbors)
- Use `ok` / `err` for JSON APIs
- Resolve BVid through existing helpers (`resolve_bvid` / `normalize_bvid`) when accepting user BV input
- Scope analysis by optional `bvid` when the UI sends video scope
- Add or extend tests under `backend/tests/` for new CRUD/filter contracts

---

## Testing Requirements

| Command | Scope |
|---------|-------|
| `uv run pytest` | `backend/tests` only (`pyproject.toml` testpaths; vendor ignored) |
| `uv run python backend/scripts/smoke_test.py` | Broader HTTP + optional Ollama/GPU checks |
| `cd frontend && node scripts/agent-session-check.mjs` | Agent session isolation |

New post list filters / delete semantics need a pytest case. Do not add tests under `vendor/`.

---

## Code Review Checklist

- [ ] Layering respected (api → services → storage/config)
- [ ] Frontend `client.js` (+ callers) updated
- [ ] No secrets in diff
- [ ] Sentiment integer kept in sync when writing labels
- [ ] `bvid` stored under `raw.extra.bvid` when needed for video reports
- [ ] Pytest or smoke covers the regression if the bug was user-visible
