# Build Plan & Evaluation

Evaluates the spec in [README.md](./README.md) and tracks the phased build against its build order.

## Evaluation of the Spec

- **Strengths**
  - Broad coverage: Next.js/TypeScript frontend, Python backend, Postgres, RAG/LLM agent — full-stack + applied-AI, not a single-layer demo.
  - Concrete architecture: ingestion → agent (CoT + tools + memory) → API → frontend → eval → guardrails → benchmark.
  - Synthetic applicant/underwriting data avoids privacy/compliance issues.
    - Policy corpus later switched to real specimen PDFs for realism — repo stays **private** as a deliberate trade-off (see README § Data).
  - Outcome-driven: every phase has a measurable target (faithfulness score, latency reduction).
- **Gaps found (addressed in README and this plan)**
  - No golden dataset — an "80%+ faithfulness" claim needs manually verified ground truth to be defensible.
  - Latency benchmark needed an explicit methodology, or the number reads as fabricated.
  - `risk_calculator` data flow was unspecified — resolved by reading criteria/formula from Excel at runtime.
  - No unit tests originally — pytest coverage now demonstrates correctness beyond manual click-through.
  - Session isolation was claimed but unverified — needs a concurrent-session test with recorded evidence.
  - Guardrails needed before/after proof, not just a system prompt.
  - Postgres schema kept minimal by design: `sessions`, `chat_messages`, `applicants` only.
  - No git repo existed — initialized as the first build step.
- **Verdict**: solid design document, not originally execution-ready (missing verification details above, now folded into README). Build status: **all 4 phases complete**.

## Phased Build Plan

No fixed calendar — each phase starts once the previous phase's verification checklist passes.

### Phase 1 — Foundation (README steps 1–3)

- [x] `git init`, `backend/` + `frontend/` skeletons, Python venv, `.env.example`, `.gitignore`
- [x] Mock data
  - [x] Excel underwriting criteria (age, BMI, health history, occupation risk, risk formula)
  - [x] 8 real RBC specimen policy PDFs — gitignored, fetched via `scripts/download_real_policies.py`; synthetic HTML fallback in `data/policies_mock_backup/` (see `backend/data/README.md`)
  - [x] 20–30 synthetic applicant cases, including edge cases
- [x] Ingestion pipeline (`ingest.py`) — Excel/PDF → chunk → embed into ChromaDB
- [x] Manual spot-check script (5 sample queries) for retrieval quality

### Phase 2 — Agent + API (README steps 4–5)

- [x] Agent (`agent.py`) — `langchain.agents.create_agent` + CoT system prompt
- [x] `risk_calculator` tool — reads criteria/formula from Excel at runtime
- [x] `policy_lookup` tool — RAG query against ChromaDB
- [x] Session-isolated memory via LangGraph checkpointer keyed by `thread_id`
- [x] Concurrent-session isolation test (`tests/test_agent_session_isolation.py`, fake model, no LLM cost)
- [x] FastAPI `POST /assess` — smoke-tested, fails gracefully (502) without an API key
- [x] pytest coverage (28/28 passing)
- [x] Live smoke test, real `gpt-4o-mini`, 3 applicant cases:
  - Low risk (Chloe Bennett) — both tools called, scored 5/Preferred, real RBC pages cited.
  - High-risk composite (Marcus Webb) — both tools called, scored 220/Decline, breakdown matched `calculate_risk` exactly.
  - Missing BMI (Grace Owusu) — **found a real bug**: model guessed `bmi=0` instead of asking a clarifying question, since `_applicant_to_message()` silently dropped `None` fields. Fixed by flagging missing required fields as `"MISSING (not provided by the applicant)"`; regression tests added.

### Phase 3 — Frontend + Evaluation (README steps 6–7)

- [x] Applicant data form (`frontend/app/components/ApplicantForm.tsx`)
- [x] Result display — risk-tier badge, reasoning, cited sources, tool-call trace (`AssessmentResult.tsx`)
- [x] Frontend ↔ backend wiring (`lib/api.ts` → `POST /assess`, CORS added) — verified end-to-end via a scripted Playwright run, zero console errors
- [x] Golden dataset (`backend/data/golden_dataset.json`) — 11 cases: 5 policy/underwriting Q&A grounded in real retrieved text, 6 applicant assessments with deterministic expected scores, including one missing-field edge case
- [x] DeepEval run, scores recorded in README
  - First run: relevancy avg 0.846 (64% pass) — the agent applied its full 5-heading format even to plain policy questions.
  - Fixed by branching the system prompt on request type (`agent.py`); re-ran.
  - Final: **faithfulness 0.985 (11/11 pass)**, **relevancy 0.875 (9/11 pass)** — both clear the 80% target on average (see README § Evaluation for the 2 accepted relevancy misses).

### Phase 4 — Guardrails, Benchmark, Deploy, Docs (README steps 8–11)

- [x] Guardrails — deterministic input/output validation layer (`backend/guardrails.py`)
  - Input: prompt-injection detection on free-text fields, 422 before any LLM call.
  - Output: `ensure_disclaimer()` backstop.
  - 14 tests in `tests/test_guardrails.py`, all mocked (no LLM cost).
- [x] Documented before/after guardrail cases — real red-team run (`scripts/guardrail_redteam.py`, transcripts in `guardrail_redteam_results.json`, summarized in README § Guardrails).
  - Model resisted both injection attempts unaided in this sample — guardrail is defense-in-depth, not a fix for an observed jailbreak.
- [x] Latency benchmark methodology documented — explicit bottom-up estimate (no citable industry figure found).
- [x] Benchmark run (`scripts/benchmark_latency.py`, 10 cases + 2 edge cases, real `gpt-4o-mini`): **99.6% efficiency gain** (20 min assumed manual vs. 4.29s mean AI-assisted).
- [x] Deploy config prepared — `render.yaml`, `backend/Procfile`, env-var-driven CORS (`FRONTEND_ORIGIN`), full guide in `DEPLOYMENT.md`.
  - Actual deployment intentionally not performed — requires the user's own Render/Vercel/OpenAI accounts.
- [x] Verified no secrets committed — `.env`/`.env.local` gitignored, sensitive `render.yaml` vars marked `sync: false`.
- [x] README finalized — added Architecture & Design Decisions, Deployment sections.
- [x] Bug fix from end-to-end testing — missing `occupation_class` could make the model call `risk_calculator` with a literal `"MISSING"` placeholder, crashing the request into a 502. Fixed in `tools.py` (tool wrapper catches `ValueError`, returns `{"error": ...}`); regression test added.

### Phase 5 — Observability: LangFuse, Docker, Prometheus/Grafana (post-README, not in original build order)

- [x] LangFuse tracing (`backend/observability.py`) — optional, enabled only when `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` are set; wired into `agent.py`'s `run_assessment()` via LangChain callback + `langfuse_session_id` metadata. 3 tests in `tests/test_observability.py`.
- [x] Prometheus metrics (`backend/main.py`, `prometheus-fastapi-instrumentator`) — `GET /metrics` with auto request/latency metrics plus 3 app-specific counters (`guardrail_rejections_total`, `agent_tool_calls_total`, `assessment_errors_total`), verified live via TestClient (guardrail rejection increments the counter correctly).
- [x] Backend Dockerfile — bakes ingestion (PDF download + ChromaDB build) in at build time, same approach as the Render deploy.
- [x] `docker-compose.yml` — backend + Prometheus + Grafana, Grafana dashboard and Prometheus datasource auto-provisioned from `observability/` (no manual UI setup needed).
- [x] Full stack built and run for real via `docker compose up --build`: `/health` returns ok, a real `/assess` call through the container returns a correct risk tier with real RBC policy citations, `/metrics` shows the custom counters incrementing correctly, Prometheus target is `up`, and the Grafana dashboard renders live scraped data (2 total /assess requests, 2 tool calls, 1 guardrail rejection, 0 errors — matching the smoke-test traffic sent).
- [x] Documented in `OBSERVABILITY.md`, linked from `README.md` § Core Features.
- **Zero added cost by design**: LangFuse Cloud free tier, Prometheus/Grafana self-hosted via Docker — only pre-existing cost (OpenAI API usage) applies.

## Verification Checklist (per phase)

- [x] **Ingestion** — 5 sample queries checked against source docs: 4/5 exact-section top match, 1/5 relevant but less specific (`scripts/spot_check_retrieval.py`).
- [x] **Agent** — concurrent-session isolation confirmed (fake model); real-model tool-calling confirmed via live smoke test (3 cases).
- [x] **API** — `POST /assess` tested with 3 risk tiers, mocked and live.
- [x] **Frontend** — Playwright-scripted browser test: risk tier, reasoning, sources, disclaimer, tool trace all render correctly, zero console errors.
- [x] **Eval** — full DeepEval run against the 11-case golden dataset, scored against the 80% threshold (README § Evaluation).
- [x] **Guardrails** — 3 adversarial cases tested against the live agent (2 injection, 1 legal-advice boundary), behaves as documented (README § Guardrails).
- [ ] **Deploy** — end-to-end check of a deployed Vercel frontend calling a deployed Render backend. Pending: requires the user to run the deploy from `DEPLOYMENT.md` with their own accounts.
