# Build Plan & Evaluation

This document evaluates the project spec in [README.md](./README.md) and lays out a phased build plan starting from zero, following the README's build order.

## Evaluation of the Spec

### Strengths
- **Broad technical coverage**: Next.js/TypeScript frontend, Python backend, SQL persistence (Postgres), and a RAG/LLM agent layer — a genuine full-stack + applied-AI system, not a single-layer demo.
- **Concrete architecture**: Clear separation of ingestion → agent (CoT + tool calling + memory) → API → frontend → eval → guardrails → benchmark. This is a full production-style agent pipeline, not a toy chatbot.
- **Synthetic applicant/underwriting data**: Avoids privacy/compliance issues around personal and health data. Note: the policy document corpus was later switched to real specimen PDFs for realism (see Data section in `README.md`), which means this repository must stay **private** rather than be published — this is a deliberate tradeoff, not an oversight.
- **Outcome-driven**: Every phase has a measurable target (e.g., faithfulness score, latency reduction), which keeps the project focused instead of open-ended.

### Gaps found (addressed in the README and in this plan)
1. **No golden dataset for evaluation** — DeepEval needs ground truth to compare against. Without a manually verified Q&A set, an "80%+ faithfulness" number is not defensible or reproducible.
2. **Latency benchmark risk of looking fabricated** — "manual vs AI-assisted" needs an explicit, stated methodology (where the manual-time assumption comes from, how AI time is measured), or the number reads as made up.
3. **`risk_calculator` data flow was unspecified** — resolved by having it read criteria/formula from the mock Excel file at runtime, which also exercises real pandas usage rather than hardcoded logic.
4. **No unit tests** — pytest coverage for `risk_calculator` and the ingestion pipeline shows engineering maturity beyond "it works when I click through it."
5. **Session isolation is claimed but not verified** — needs an explicit test with two concurrent sessions proving no context leakage, with the result recorded as evidence.
6. **Guardrails need before/after proof** — a system prompt alone isn't evidence; documented test cases (e.g., a legal-advice request, a prompt-injection attempt) with observed blocked/redirected output are.
7. **Postgres schema should stay simple** — kept in scope for chat history and session metadata, but scoped to just `sessions`, `chat_messages`, `applicants` — no over-engineering.
8. **No git repo existed** — this project is standing up in its own folder; initialize git as the very first build step so there's a clean commit history.

### Verdict
The spec is a strong **design document** (architecture and scope are solid) but was **not yet execution-ready** because it lacked the verification details above (golden dataset, benchmark methodology, test cases). Those additions are now folded into `README.md`. Current implementation status: **0% built** — this plan starts entirely from scratch.

## Phased Build Plan

Project root: `/Users/athens/Downloads/Coding/rag-powered-decision-assistant/`

No fixed calendar — each phase starts once the previous phase's verification checklist passes.

### Phase 1 — Foundation (README steps 1–3)
- [x] `git init`, create `backend/` + `frontend/` (Next.js + TS + Tailwind) skeletons, Python venv, `.env.example`, `.gitignore`
- [x] Generate mock data:
  - [x] Excel: underwriting criteria (age, BMI, health history, occupation risk, risk score formula) — this is what `risk_calculator` will read from
  - [x] Policy documents: 8 real specimen policy PDFs from RBC Insurance (term life, term 100, universal life x2, riders x2, critical illness, disability income) — gitignored (`backend/data/policies/*.pdf`), fetched locally via `scripts/download_real_policies.py`, never enter git history; repo still kept private regardless. Synthetic HTML fallback kept in `data/policies_mock_backup/`. See `backend/data/README.md`.
  - [x] 20–30 synthetic applicant cases, covering edge cases (high risk, borderline, missing fields)
- [x] Ingestion pipeline (`ingest.py`) — parse Excel/PDF → chunk → embed into ChromaDB
- [x] Manual spot-check script (5 sample queries) to confirm retrieval quality

### Phase 2 — Agent + API (README steps 4–5)
- [x] Agent (`agent.py`) — built with `langchain.agents.create_agent` (LangChain 1.x) + CoT system prompt
- [x] `risk_calculator` tool (`tools.py`, reads criteria/formula from the mock Excel file at runtime, not hardcoded)
- [x] `policy_lookup` tool (`tools.py`, RAG query against the ChromaDB vector store from Phase 1)
- [x] Session-isolated memory (per session_id, via a LangGraph checkpointer keyed by `thread_id`)
- [x] Two-concurrent-sessions isolation test (`tests/test_agent_session_isolation.py`, uses a fake chat model so it costs no real LLM calls)
- [x] FastAPI (`main.py`) — `POST /assess` endpoint, smoke-tested to boot and fail gracefully (502) without an API key
- [x] pytest coverage for the endpoint and tools (28/28 tests passing across the whole backend)
- [x] **Live smoke test with a real `gpt-4o-mini` API key** — ran 3 real applicant cases end-to-end:
  - Low risk (Chloe Bennett): correctly called both tools, scored 5/Preferred, cited real RBC policy pages, followed the 5-heading format.
  - High-risk composite (Marcus Webb): correctly called both tools, scored 220/Decline, breakdown matched `calculate_risk` exactly (age 30 + bmi 45 + health max(30,45)=45 + occupation 60 + smoker 40).
  - Missing BMI (Grace Owusu): **found a real bug** — the model initially guessed `bmi=0` instead of asking a clarifying question, because `_applicant_to_message()` silently dropped `None` fields instead of flagging them. Fixed by marking required-but-missing fields as `"MISSING (not provided by the applicant)"` in the message (`main.py`); after the fix, the agent correctly asked for the missing BMI and called no tools. Regression tests added in `tests/test_main.py`.

### Phase 3 — Frontend + Evaluation (README steps 6–7)
- [x] Next.js frontend — applicant data form (`frontend/app/components/ApplicantForm.tsx`)
- [x] Assessment result display with reasoning trace and cited sources (`frontend/app/components/AssessmentResult.tsx`, parses the agent's headed response and renders a risk-tier badge, tool-call trace, and cited sources)
- [x] Wire frontend to the backend API (`frontend/app/lib/api.ts` → `POST /assess`; added CORS middleware to `backend/main.py`) — verified end-to-end with a real `gpt-4o-mini` call via a scripted browser run (Playwright): filled the form, submitted, confirmed the risk tier badge, reasoning, cited sources, and tool-call trace all rendered correctly with zero console errors
- [x] Build the golden dataset (`backend/data/golden_dataset.json`, 11 manually verified cases: 5 policy/underwriting Q&A grounded in real retrieved PDF/Excel text, 6 applicant assessments with deterministic expected risk scores/tiers computed directly via `calculate_risk`, including one missing-required-field edge case)
- [x] Run DeepEval (faithfulness, answer relevancy) and record the real scores in `README.md` — first run surfaced a real relevancy problem (the agent applied its full 5-heading applicant-assessment format even to plain policy questions, padding answers with an irrelevant "Risk Tier"/disclaimer boilerplate); fixed by branching the system prompt on request type (`backend/agent.py`), then re-ran. Final: **faithfulness avg 0.985 (11/11 pass)**, **answer relevancy avg 0.875 (9/11 pass)** — both clear the 80% target on average; see README.md § Evaluation for the 2 remaining relevancy misses and why they're an accepted guardrail/metric tension, not a bug

### Phase 4 — Guardrails, Benchmark, Deploy, Docs (README steps 8–11)
- [x] Guardrails — system prompt constraints (already in place from Phase 2) + a deterministic input/output validation layer (`backend/guardrails.py`): input-side prompt-injection detection on free-text applicant fields (422 before any LLM call), output-side `ensure_disclaimer()` backstop. 14 unit/integration tests in `tests/test_guardrails.py`, all mocked (no LLM cost)
- [x] Documented before/after test cases (prompt injection, unqualified-advice request) — real red-team run against the live `gpt-4o-mini` agent (`backend/scripts/guardrail_redteam.py`, transcripts in `backend/guardrail_redteam_results.json`), summarized in README.md § Guardrails. Found the underlying model resisted both injection attempts on its own in this sample (documented honestly rather than oversold) — the guardrail is defense-in-depth, not a fix for an observed jailbreak
- [x] Latency benchmark methodology written down — explicit bottom-up task-time assumption for manual review (couldn't find a citable industry per-application figure, said so), documented in README.md § Latency Benchmark
- [x] Run manual-vs-AI-assisted comparison, record numbers (`backend/scripts/benchmark_latency.py`, 10 real cases + 2 edge cases, real `gpt-4o-mini` calls): **99.6% efficiency gain** (20 min assumed manual vs. 4.29s mean AI-assisted)
- [x] Deploy config prepared — `render.yaml` (backend, Render Blueprint) + `backend/Procfile`; `backend/main.py` CORS origins now env-var-driven (`FRONTEND_ORIGIN`) instead of hardcoded, so a deployed frontend origin is a dashboard setting; full guide in `DEPLOYMENT.md`. **Actual deployment intentionally not performed** — requires the user's own Render/Vercel/OpenAI accounts (their choice, see conversation)
- [x] Verify env vars/secrets aren't committed — `.env`/`.env.local` gitignored, `render.yaml`'s `OPENAI_API_KEY`/`FRONTEND_ORIGIN`/`HF_TOKEN` all marked `sync: false` (dashboard-only, never in the file)
- [x] Finalize `README.md` with architecture, design decisions, and real evaluation numbers — added § Architecture & Design Decisions and § Deployment
- [x] Fix bugs found during end-to-end testing — the latency benchmark surfaced a real crash: a missing `occupation_class` could make the model call `risk_calculator` with a literal `"MISSING"` placeholder, and the tool's uncaught `ValueError` turned the whole request into a 502 instead of a graceful clarifying question (the missing-`bmi` case from Phase 2 didn't generalize). Fixed in `tools.py` (the `@tool` wrapper now catches `ValueError` and returns `{"error": ...}`), regression-tested in `tests/test_risk_calculator.py`

## Verification Checklist (per phase)
- [x] **Ingestion**: 5 sample queries checked against source policy docs for correct chunk retrieval — 4/5 returned an exact-section top match, 1/5 returned a relevant but less specific section (see `scripts/spot_check_retrieval.py` output)
- [x] **Agent**: two concurrent sessions confirmed not to leak memory (`tests/test_agent_session_isolation.py`, fake model, no LLM cost). Tool-calling by a *real* model confirmed via the live smoke test above — `risk_calculator`/`policy_lookup` invoked at the right steps, in the right order, with correct arguments, across 3 real applicant cases.
- [x] **API**: `POST /assess` tested with 3 applicant cases (low/medium/high risk) in `tests/test_main.py` (mocked) and again live against the real agent (see Phase 2 live smoke test notes) — both confirm correct request/response wiring end to end.
- [x] **Frontend**: browser test (Playwright-scripted) — submitted the form, confirmed the risk tier badge, reasoning, recommendation, cited sources, disclaimer, and tool-call trace all render correctly, with zero console errors
- [x] **Eval**: full DeepEval run against the 11-case golden dataset, scores recorded and compared to the 80% threshold (see README.md Evaluation section)
- [x] **Guardrails**: 3 adversarial cases tested against the real live agent (2 prompt-injection, 1 unqualified-legal-advice boundary request), confirming the guardrail behaves as documented (see README.md § Guardrails)
- [ ] **Deploy**: end-to-end check that a deployed Vercel frontend successfully calls a deployed Render backend — pending the user actually running the deploy from `DEPLOYMENT.md` with their own accounts; not performed in this session by design
