# Directory Structure

> How backend code is organized in 知微.

---

## Overview

Runnable backend root is `backend/` (not `app/`). Entry: `backend/main.py` adds `backend/` to `sys.path` and runs `src.api.app:app`.

Call chain:

```text
frontend → src/api/* → src/services/* → src/storage | src/config
```

Keys, model ids, Cookie, Ollama URLs come **only** from `src/config/`. Never import from `vendor/`.

---

## Directory Layout

```text
backend/
├── main.py                 # uvicorn entry
├── scripts/                # smoke_test, sample data, prefetch (ops, not API)
├── tests/                  # pytest (configured via root pyproject.toml)
├── data/                   # runtime SQLite + samples (mostly gitignored)
└── src/
    ├── api/                # FastAPI routers + app assembly
    │   ├── app.py
    │   ├── health.py
    │   ├── data.py         # imports, posts CRUD, dashboard
    │   ├── collect.py
    │   ├── analysis.py
    │   ├── alerts.py
    │   ├── reports.py
    │   └── agent.py
    ├── services/           # single-capability modules (sentiment, topics, …)
    ├── storage/            # SQLite Store only
    ├── config/             # settings, device/CUDA, cookie helpers
    └── lib/                # no-domain helpers (http ok/err)
```

---

## Module Organization

| Layer | Put here | Do not put here |
|-------|----------|-----------------|
| `api/` | Pydantic bodies, Query params, status codes, call services/store | BERT/Ollama calls, SQL strings |
| `services/` | ingest, bilibili collect/quality, sentiment, topics, forecast, report, agent | FastAPI `Request`, reading `.env` ad hoc |
| `storage/` | `Store` CRUD, schema, filters (`bvid`, `q`) | LLM, HTTP clients |
| `config/` | pydantic-settings, CUDA probe | business alert rules |
| `lib/` | `ok` / `err` JSON helpers | domain types |

New HTTP capability: add or extend a router file under `api/`, register in `app.py` with prefix `/api/v1`, then mirror the client in `frontend/src/api/client.js`.

---

## Naming Conventions

- Modules: `snake_case.py`
- Routers: domain noun (`data.py`, `alerts.py`)
- Store methods: verb_noun (`list_posts`, `create_post`, `delete_posts`)
- Source ids for Bilibili comments stay stable for `UNIQUE(platform, source_id)` dedupe

---

## Examples

- Layer map: `backend/src/README.md`
- HTTP ownership: `backend/src/api/README.md`
- Posts + search + CRUD: `backend/src/api/data.py` + `backend/src/storage/db.py`
- Response helpers: `backend/src/lib/http.py`
