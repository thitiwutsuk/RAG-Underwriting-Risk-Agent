# Deployment Guide (Phase 4)

This covers deploying the backend (FastAPI) to Render and the frontend (Next.js)
to Vercel. It documents the steps and config; it does not deploy anything for
you — you'll need your own Render, Vercel, and OpenAI accounts to actually run
this.

## (a) Prerequisites

- A GitHub account with this repo pushed to a **private** GitHub repository.
  This is non-negotiable: `backend/data/policies/*.pdf` are real copyrighted
  RBC Insurance specimen documents (see `backend/data/README.md`). They're
  gitignored so they never enter git history, but the repo containing the
  scripts and setup to fetch/use them must still stay private per README.md.
  Render, Railway, and Vercel can all deploy directly from a private repo, so
  this doesn't block deployment — just don't flip the GitHub repo to public.
- A [Render](https://render.com) account (backend) — free tier used here.
- A [Vercel](https://vercel.com) account (frontend) — free/Hobby tier used here.
- An OpenAI API key with billing enabled. The agent calls the OpenAI API on
  every `/assess` request; there is no way around a real API key for a real
  deployment.
- Local sanity check before deploying: `cd backend && source venv/bin/activate
  && python -m pytest -q` should pass (30/30 as of this writing).

Free-tier specifics (spin-down behavior, RAM/CPU limits, exact build minutes)
change fairly often on all three platforms and aren't reproduced here with
confident numbers — check the current Render/Vercel pricing pages if a limit
matters to you. What's stable and worth planning around: Render's free web
services spin down after a period of inactivity and take a noticeable cold
start on the next request (tens of seconds), which matters for a demo — hitting
`/health` right before showing someone the app is a reasonable workaround.

## (b) Backend deploy — Render

Config is checked in at the repo root: `render.yaml` (Render Blueprint) and
`backend/Procfile` (a fallback/reference if you set the service up manually
instead of via Blueprint — Render's Python runtime uses the build/start
commands from the Blueprint or dashboard, not the Procfile, but Procfile is
included since it's the convention other platforms like Railway also read).

Steps:

1. In the Render dashboard: **New → Blueprint**, connect your GitHub account,
   and select this repository (must be authorized as private — Render
   supports this same as public repos).
2. Render reads `render.yaml` from the repo root and proposes one service,
   `rag-underwriting-backend`, with `rootDir: backend`.
3. Before the first deploy, fill in the env vars `render.yaml` leaves blank
   (`sync: false` means "set this in the dashboard, don't put it in the
   file"):
   - `OPENAI_API_KEY` — required, real API costs start here (see section e).
   - `FRONTEND_ORIGIN` — leave blank for now if you haven't deployed the
     frontend yet; you'll come back and set it to the Vercel URL once you
     have it (see part c). Comma-separate multiple origins if needed. Until
     it's set, CORS defaults to `http://localhost:3000` only, so a deployed
     frontend calling this backend will fail with a CORS error — that's
     expected and just means this var still needs setting.
   - `HF_TOKEN` — optional. `sentence-transformers` downloads the
     `BAAI/bge-m3` embedding model from the HuggingFace Hub during the build
     step (`ingest.py`). This needs outbound internet access from Render's
     build environment (present by default) and normally works anonymously;
     `HF_TOKEN` only helps if you hit HuggingFace's anonymous rate limit.
4. **Why the build command has three steps, not one.** `render.yaml`'s
   `buildCommand` is:
   ```
   pip install -r requirements.txt &&
   python scripts/download_real_policies.py &&
   python ingest.py
   ```
   `backend/data/policies/*.pdf` are gitignored and never committed (see
   `backend/data/README.md`), so a fresh clone/deploy has no policy documents
   and no ChromaDB collection at all. `download_real_policies.py` re-fetches
   the 8 real specimen PDFs from rbcinsurance.com, then `ingest.py` parses
   them (plus the underwriting Excel) and rebuilds the ChromaDB collection at
   `backend/chroma_db/`. If either step is skipped, the app still boots and
   `/health` still returns 200, but the agent's `policy_lookup` tool has
   nothing to search — every assessment will be missing its RAG grounding
   (no cited sources, and DeepEval faithfulness would tank if run against
   it). This is the single most important thing to get right in this
   deployment.
5. Start command (from `render.yaml`): `uvicorn main:app --host 0.0.0.0
   --port $PORT`. `$PORT` is injected by Render at runtime — don't hardcode a
   port.
6. Deploy. Watch the build logs — the `ingest.py` step downloads an
   embedding model and 8 PDFs, so the first build takes noticeably longer
   than a typical Python service build.
7. Once live, note the service's public URL (`https://rag-underwriting-backend-<hash>.onrender.com` or
   similar — Render assigns this) — the frontend needs it.

Env vars actually consumed by the running app right now: `OPENAI_API_KEY`,
`AGENT_MODEL` (defaults to `gpt-4o-mini` if unset), `FRONTEND_ORIGIN` (new —
added in this phase, see below). Worth flagging: `.env.example` at the repo
root also lists `CHROMA_PERSIST_DIR`, `UNDERWRITING_EXCEL_PATH`, and
`POLICY_HTML_DIR`, but as of this writing `ingest.py`/`tools.py` don't
actually read those env vars — they use hardcoded relative paths
(`chroma_db`, `data/underwriting_criteria.xlsx`, `data/policies`) resolved
against the working directory. Since Render's `rootDir: backend` makes
`backend/` the working directory for both the build and start commands, this
works correctly without setting those three vars — they're aspirational at
the moment, not load-bearing. `DATABASE_URL` (Postgres) is similarly present
in `.env.example` for the planned chat-history/session-metadata persistence
but isn't wired into any code path yet, so it isn't needed for this deploy.

### CORS change made in this phase

`backend/main.py` previously hardcoded
`allow_origins=["http://localhost:3000"]` in its `CORSMiddleware` setup. It
now reads a `FRONTEND_ORIGIN` env var (comma-separated for multiple origins),
defaulting to `http://localhost:3000` when unset — so local dev needs zero
config, and a deployed frontend origin is a dashboard setting, not a code
change:

```python
_frontend_origins = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
ALLOWED_ORIGINS = [origin.strip() for origin in _frontend_origins.split(",") if origin.strip()]
```

## (c) Frontend deploy — Vercel

The Next.js app in `frontend/` needs no special config beyond one env var.

1. In the Vercel dashboard: **Add New → Project**, import this same GitHub
   repo, set the project's root directory to `frontend/`.
2. Vercel auto-detects Next.js 16 and uses `npm run build` / `next start` —
   no build command override needed.
3. Set one environment variable in the Vercel project settings:
   - `NEXT_PUBLIC_API_BASE_URL` = the Render backend's public URL from step
     (b)7 above, e.g. `https://rag-underwriting-backend-xxxx.onrender.com`
     (no trailing slash — `frontend/app/lib/api.ts` appends `/assess`
     directly). This must be set as a build-time env var since it's a
     `NEXT_PUBLIC_*` var baked into the client bundle at build time, not read
     at runtime — set it before the first deploy, or redeploy after changing
     it.
4. Deploy. Note the resulting Vercel URL (e.g.
   `https://your-app.vercel.app`).
5. Go back to the Render dashboard and set `FRONTEND_ORIGIN` to that exact
   Vercel URL (part b, step 3), then redeploy/restart the backend so CORS
   picks it up.

## (d) Post-deploy smoke test

Run through this in order once both sides are live:

1. `curl https://<your-render-url>/health` → expect `{"status":"ok"}`. If
   this hangs or 502s, the backend build likely failed (check the ingest
   step in the Render build logs before anything else).
2. Open the Vercel frontend URL in a browser. Confirm the applicant form
   renders with no console errors.
3. Submit one real test applicant end-to-end (any of the synthetic cases in
   `backend/data/applicants.json` works, or fill the form manually). Confirm:
   - The request reaches the backend (no CORS error in the browser console —
     if you see one, `FRONTEND_ORIGIN` on Render doesn't match the Vercel URL
     exactly, including `https://` and no trailing slash).
   - A real risk tier, reasoning, and at least one cited policy source come
     back — this confirms `ingest.py` actually ran during the build and the
     ChromaDB collection isn't empty.
   - No 502 — a 502 means `run_assessment` raised, most likely a missing/bad
     `OPENAI_API_KEY` on Render.
4. Check the Render logs for the request you just made, to confirm nothing
   silently failed server-side even though the frontend showed a result.

## (e) Cost note

This project is deliberately kept on free/hobby tiers where possible (Render
free web service, Vercel Hobby plan) — it's a portfolio/demo project, not a
production service, and there's no reason to pay for compute here. The one
cost that is real and unavoidable once deployed: **`OPENAI_API_KEY` usage is
billed by OpenAI per API call**, at whatever OpenAI's current per-token rate
is for `AGENT_MODEL` (`gpt-4o-mini` by default). Every `/assess` request from
a publicly reachable frontend makes at least one real OpenAI call (often two,
given `risk_calculator`/`policy_lookup` tool calls plus the final response).
If this URL is shared publicly, budget for that or add a basic safeguard
(e.g. a shared secret header the frontend attaches, or an OpenAI usage cap in
the OpenAI dashboard) — none of that is set up here, since guarding it wasn't
in scope for this pass.
