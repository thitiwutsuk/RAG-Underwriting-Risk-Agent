# Observability (Phase 5)

LLM tracing (LangFuse), containerized local stack (Docker), and app metrics (Prometheus + Grafana). Everything here runs on free tiers / self-hosted — no new required costs beyond the OpenAI API usage the project already has.

## LangFuse tracing

- Every agent run (chain-of-thought steps, tool calls, latency, token cost) can be traced in [LangFuse](https://cloud.langfuse.com) — free Hobby plan.
- **Fully optional**: with no credentials set, `backend/observability.py` returns `None` and the agent runs exactly as before. Nothing breaks either way.
- Setup:
  1. Create a free account at [cloud.langfuse.com](https://cloud.langfuse.com), create a project, copy its public/secret key.
  2. Set in `.env` (repo root):
     ```
     LANGFUSE_PUBLIC_KEY=pk-...
     LANGFUSE_SECRET_KEY=sk-...
     LANGFUSE_HOST=https://cloud.langfuse.com
     ```
  3. Run the backend and submit an assessment — traces appear in the LangFuse dashboard under the project, grouped by `session_id`.
- Tests: `backend/tests/test_observability.py` (mocked, no real LangFuse account needed).

## Docker

- `backend/Dockerfile` bakes the policy corpus + ChromaDB collection in at **build time** (same approach as the Render deploy — see `DEPLOYMENT.md`), so the container starts ready to serve. This needs network access during build (downloads the RBC specimen PDFs and the local embedding model) but no API keys.
- Build and run just the backend:
  ```bash
  cd backend
  docker build -t rag-underwriting-backend .
  docker run -p 8000:8000 --env-file ../.env rag-underwriting-backend
  ```
- Or run the full stack (backend + Prometheus + Grafana) via `docker-compose.yml` at the repo root — see below.

## Prometheus + Grafana

- `backend/main.py` exposes `GET /metrics` via `prometheus-fastapi-instrumentator`: request count, request latency histograms, plus three app-specific counters:
  - `guardrail_rejections_total{field}` — requests blocked by the input guardrail
  - `agent_tool_calls_total{tool}` — `risk_calculator` vs `policy_lookup` call counts
  - `assessment_errors_total` — `/assess` requests that failed with a 502
- Run the whole stack:
  ```bash
  docker compose up --build
  ```
  - Backend: http://localhost:8000 (`/metrics` for the raw Prometheus output)
  - Prometheus: http://localhost:9090
  - Grafana: http://localhost:3001 — dashboard **"RAG Underwriting Agent - Overview"** is auto-provisioned (datasource + dashboard JSON both load automatically, no manual clicking required); anonymous viewer access is enabled, or log in with `admin` / `admin`.
- Dashboard panels: request rate, p95 latency, tool-call breakdown, guardrail rejections over time, and running totals (errors, rejections, requests, tool calls).
- Config lives in `observability/`: `prometheus.yml` (scrape config) and `grafana/` (datasource + dashboard provisioning, checked into the repo so the dashboard is reproducible on any machine — not something you have to rebuild by hand).

## Why this is separate from the DeepEval/benchmark work

Phase 3/4's `eval.py` and `scripts/benchmark_latency.py` are one-off, offline measurements (answer quality, latency on a fixed sample) run manually and recorded in `README.md`. This phase is the online counterpart — metrics that update continuously while the app is actually being used, for spotting regressions or unusual patterns (e.g. a spike in guardrail rejections, latency creeping up) rather than a point-in-time report.
