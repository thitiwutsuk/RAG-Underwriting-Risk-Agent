9hv'dki# Deployment Guide (Phase 4)

Covers deploying the backend (FastAPI) to Render and the frontend (Next.js) to Vercel. Documents steps and config only — deploying requires your own Render, Vercel, and OpenAI accounts.

## (a) Prerequisites

- GitHub account with this repo pushed (public or private — both work; Render/Vercel deploy from either).
  - `backend/data/policies/*.pdf` are real RBC Insurance specimen documents, credited in `backend/data/README.md`; gitignored and never in git history either way.
- [Render](https://render.com) account (backend, free tier used here).
- [Vercel](https://vercel.com) account (frontend, free/Hobby tier used here).
- OpenAI API key with billing enabled — the agent calls the OpenAI API on every `/assess` request.
- Local sanity check before deploying: `cd backend && source venv/bin/activate && python -m pytest -q` (30/30 as of this writing).
- Free-tier specifics (spin-down, RAM/CPU limits, build minutes) change often — check current pricing pages if a limit matters. One stable fact worth planning around: Render's free web services spin down after inactivity and take a noticeable cold start (tens of seconds) on the next request — hit `/health` before a demo.
- **RAM matters here.** Render's free web service has 512MB RAM. `policy_lookup`'s embeddings use `fastembed` (ONNX runtime), not `sentence-transformers`/`torch` — this took two failed attempts to land on:
  1. `BAAI/bge-m3` via sentence-transformers (~2GB) OOM'd outright.
  2. Swapping to a smaller model but keeping sentence-transformers (`all-MiniLM-L6-v2`) *still* OOM'd — loading `torch` itself uses ~600MB regardless of which model is loaded, already over the 512MB limit before the app does anything else.
  3. `fastembed` has no torch dependency. Measured peak RSS for a full real `/assess` call (model load + ChromaDB query + LLM round trip) is **~420MB** — fits, with modest headroom (~90MB).
  - If you ever change `EMBEDDING_MODEL_NAME` or the embedding library in `backend/ingest.py`/`backend/tools.py`, re-measure peak RSS before deploying to the free tier — `/usr/bin/time -l python -c "from agent import run_assessment; run_assessment(...)"` on macOS (or `/usr/bin/time -v` on Linux) reports `maximum resident set size`.

## (b) Backend deploy — Render

Config checked in at the repo root: `render.yaml` (Render Blueprint) and `backend/Procfile` (fallback/reference for a manual setup or another platform like Railway).

- **Steps**
  1. Render dashboard → **New → Blueprint** → connect GitHub → select this repo.
  2. Render reads `render.yaml`, proposes one service: `rag-underwriting-backend`, `rootDir: backend`.
  3. Fill in env vars marked `sync: false` (dashboard-only, not in the file):
     - `OPENAI_API_KEY` — required, real API costs start here (see § e).
     - `FRONTEND_ORIGIN` — leave blank until the frontend is deployed (part c), then set to its Vercel URL. Comma-separate multiple origins. Until set, CORS only allows `http://localhost:3000` — a deployed frontend will hit a CORS error until this is set.
     - `HF_TOKEN` — optional; only needed if `fastembed` hits HuggingFace Hub's anonymous rate limit while downloading the embedding model during the build's `ingest.py` step.
  4. Deploy, watch build logs — the `ingest.py` step downloads an embedding model and 8 PDFs, so the first build is slower than a typical Python service.
  5. Note the service's public URL (e.g. `https://rag-underwriting-backend-<hash>.onrender.com`) — the frontend needs it.
- **Why the build command has three steps**, not one:
  ```
  pip install -r requirements.txt &&
  python scripts/download_real_policies.py &&
  python ingest.py
  ```
  - `backend/data/policies/*.pdf` are gitignored — a fresh deploy has no policy documents and no ChromaDB collection without this step.
  - Skipping either step: the app still boots, `/health` still returns 200, but `policy_lookup` has nothing to search — every assessment loses its RAG grounding (no cited sources). This is the single most important thing to get right.
- **Start command**: `uvicorn main:app --host 0.0.0.0 --port $PORT` (`$PORT` injected by Render — don't hardcode).
- **Env vars actually consumed right now**: `OPENAI_API_KEY`, `AGENT_MODEL` (defaults `gpt-4o-mini`), `FRONTEND_ORIGIN`.
  - `.env.example` also lists `CHROMA_PERSIST_DIR`, `UNDERWRITING_EXCEL_PATH`, `POLICY_HTML_DIR` — not currently read by any code path (`ingest.py`/`tools.py` use hardcoded relative paths against the working directory). Since `rootDir: backend` makes `backend/` the working directory, this works without setting those vars — they're aspirational, not load-bearing.
  - `DATABASE_URL` (Postgres) is similarly unwired — not needed for this deploy.

### CORS change made in this phase

`backend/main.py` previously hardcoded `allow_origins=["http://localhost:3000"]`. Now reads `FRONTEND_ORIGIN` (comma-separated, defaults to `http://localhost:3000`) — local dev needs zero config, a deployed frontend origin is a dashboard setting:

```python
_frontend_origins = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
ALLOWED_ORIGINS = [origin.strip() for origin in _frontend_origins.split(",") if origin.strip()]
```

## (c) Frontend deploy — Vercel

The Next.js app needs no special config beyond one env var.

1. Vercel dashboard → **Add New → Project** → import this repo → root directory `frontend/`.
2. Vercel auto-detects Next.js 16 — no build command override needed.
3. Set one env var: `NEXT_PUBLIC_API_BASE_URL` = the Render backend's public URL from (b)5, e.g. `https://rag-underwriting-backend-xxxx.onrender.com` (no trailing slash — `lib/api.ts` appends `/assess`).
   - This is a build-time var (`NEXT_PUBLIC_*`, baked into the client bundle) — set it before the first deploy, or redeploy after changing it.
4. Deploy. Note the resulting Vercel URL.
5. Back in Render: set `FRONTEND_ORIGIN` to that exact URL, then redeploy/restart the backend so CORS picks it up.

## (d) Post-deploy smoke test

1. `curl https://<render-url>/health` → expect `{"status":"ok"}`. Hangs or 502s → check the `ingest` step in Render's build logs first.
2. Open the Vercel URL — form renders, no console errors.
3. Submit one test applicant end-to-end. Confirm:
   - No CORS error (a mismatch means `FRONTEND_ORIGIN` doesn't exactly match the Vercel URL, including `https://` and no trailing slash).
   - A real risk tier, reasoning, and ≥1 cited policy source come back — confirms `ingest.py` actually ran and the collection isn't empty.
   - No 502 — a 502 usually means a missing/bad `OPENAI_API_KEY` on Render.
4. Check Render logs for the request to confirm nothing silently failed server-side.

## (e) Cost note

- Kept on free/hobby tiers where possible (Render free web service, Vercel Hobby) — this is a portfolio/demo project, not a production service.
- The one real, unavoidable cost: **OpenAI API usage is billed per call**, at whatever the current per-token rate is for `AGENT_MODEL` (`gpt-4o-mini` by default). Every `/assess` request makes at least one real OpenAI call (often two, given `risk_calculator`/`policy_lookup` tool calls plus the final response).
- If the URL is shared publicly, budget for that or add a safeguard (shared secret header, OpenAI usage cap) — neither is set up here; out of scope for this pass.
