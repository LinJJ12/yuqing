# Frontend Development Guidelines

> Conventions for the 知微 Vue 3 workbench under `frontend/src/`.

---

## Overview

The UI is a local BFF client: pages compose charts and forms; all HTTP goes through `frontend/src/api/client.js`. Product copy stays Chinese; this folder is English for Trellis sub-agents.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Pages, api, components, lib | Filled |
| [API Client](./api-client.md) | Axios envelope, fallback, sync rule | Filled |
| [Pages & State](./pages-and-state.md) | Router, scope query, localStorage | Filled |
| [Quality](./quality-guidelines.md) | Forbidden patterns, smoke scripts | Filled |

---

## Product anchors

- Routes: `frontend/src/router/index.js` · `frontend/src/pages/README.md`
- PRD IA: `docs/prd.md` §4–5
- Backend vertical pair: `backend/src/api/`
