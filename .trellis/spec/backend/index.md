# Backend Development Guidelines

> Conventions for the 知微 (Zhiwei) FastAPI backend under `backend/src/`.

---

## Overview

Backend is a BFF: HTTP routers call `services/` (or `storage/` for simple CRUD), never run model inference or raw SQL inside route handlers. Product docs live in `docs/`; layer ownership lives in each directory's README.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | Filled |
| [Database Guidelines](./database-guidelines.md) | SQLite Store patterns, schema, queries | Filled |
| [Error Handling](./error-handling.md) | `ok` / `err` envelope and exceptions | Filled |
| [Quality Guidelines](./quality-guidelines.md) | Forbidden patterns, testing | Filled |
| [Logging Guidelines](./logging-guidelines.md) | Print/logging and secrets | Filled |

---

## Product anchors (read when changing behavior)

- Product PRD: `docs/prd.md`
- Directory rules: `docs/directory-structure.md`
- Backend layer map: `backend/src/README.md`
- API vertical sync: every route change must update `frontend/src/api/client.js` (and page callers)

---

**Language**: Spec files in this folder are written in **English** for Trellis sub-agents. Product-facing docs under `docs/` remain Chinese.
