# Logging Guidelines

> How the backend records runtime signals today.

---

## Overview

There is **no** project-wide structured logging framework (no mandatory `structlog` / JSON logger). Operators rely on:

- `print` / uvicorn access logs for process lifecycle (`backend/main.py` prints listen URL)
- Occasional module-level messages around device/CUDA and model load
- Smoke script `[PASS]/` / `[FAIL]` / `[WARN]` lines

When adding logs, keep them lightweight and never print secrets.

---

## Log Levels

| Level (conceptual) | Use |
|--------------------|-----|
| info | Startup host/port, “using cuda/cpu”, job finished counts |
| warn | Optional dependency missing (Ollama embed skipped), CPU fallback |
| error | Failed import job, unhandled path before 500 handler |

Prefer clear English or Chinese prefixes like `[main]`, `[sentiment]` consistent with nearby code.

---

## Structured Logging

Not required. If you add logging, include: component name, action, and non-sensitive ids (`job_id`, `bvid`, counts). Avoid dumping full comment bodies at info level in hot loops.

---

## What to Log

- Process start / chosen device
- Import / collect job completion stats (inserted, rejected, noise reasons counts)
- Model cache miss / load failure summary
- Agent provider fallback (cloud → Ollama) without printing keys

---

## What NOT to Log

- `OPENAI_API_KEY`, full Cookie / `SESSDATA`, `.env` contents
- Entire request bodies with user PII when not needed for debugging
- Huge tensor / embedding arrays

Debug probes during incidents should use a unique prefix (e.g. `[DEBUG-xxxx]`) and be removed before merge.
