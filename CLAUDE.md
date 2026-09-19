# CLAUDE.md — BabyOverHattrick

This file is the primary context document for Claude Code agents working on this repository. Read it fully before touching any code.

---

## Project Overview

**BabyOverHattrick** is a cricket trivia game platform. Players test their cricket knowledge through a growing set of mini-games — image-based identification, name unscrambling, and more in later phases. The platform supports both guest play (no account required) and registered accounts (via Clerk), with a unified leaderboard merging both.

The target audience is cricket fans who want bite-sized, social trivia. The Instagram presence is at https://www.instagram.com/babyoverhattrick.

**Live URLs**

| | URL |
|---|---|
| Frontend (Vercel) | https://babyoverhatrick-pink.vercel.app |
| Backend (Render) | https://babyoverhatrick.onrender.com |
| Admin panel | https://babyoverhatrick-pink.vercel.app/admin |

---

## Current State

### Built and functional (Phase 1)

- **Guess the Cricketer** — player is shown a cricketer image, types the name using an autocomplete dropdown, 15-second timer. Server-side fuzzy match determines correctness.
- **Unscramble the Name** — player sees scrambled letter tiles, types the name within 30 seconds. A three-tier hint system (country → role → DB hints) is available. Per-word scrambling with a space sentinel preserves name structure.
- **Session management** — full session lifecycle: create, submit answers one by one, optional hints, complete. Answers are never sent to the client before submission.
- **No-repeat logic** — frontend stores played question IDs in `sessionStorage` and passes `exclude_ids` on next session creation. Backend filters them out and falls back to the full pool when exhausted.
- **Leaderboard** — real data. Registered users (max score per day) and guests (individual scores) are merged and sorted by score descending.
- **Daily challenge** — dedicated endpoint; question set rotates daily.
- **Admin CMS** — HTTP Basic Auth-protected `/admin` route in the frontend and SQLAdmin at the backend `/admin` endpoint. Admins can manage question sets, cricketers, and questions (add, edit, delete).
- **Auth** — Clerk (JWT RS256) for players. HTTP Basic Auth (timing-safe comparison) for the admin content API.
- **Object storage** — Cloudinary (production). MinIO (local dev, S3-compatible). The `storage_provider` env var switches between them — no code changes needed.
- **Deployment** — fully live. Backend on Render, frontend on Vercel. See the Deployment section below.

### Stubs / not yet implemented

- `backend/app/share_cards/` — share card image generation using Pillow. The module exists but produces no output.
- Streaks — the concept exists but there is no API endpoint yet.
- Phase 2 — multiplayer (not started).
- Phase 3 — broader platform features (not started).
- CI/CD pipeline — GitHub Actions not yet configured. See the Forward Direction section.

---

## Branching Strategy

| Branch | Purpose | Triggers deploy? |
|---|---|---|
| `main` | Production — always deployable | ✅ Vercel (production URL) + Render auto-deploy |
| `dev` | Integration — work branches merge here first | Vercel preview deployment only |
| `feat/*`, `fix/*`, `chore/*` | Individual tasks — branch off `dev` | Vercel preview only |

**Workflow:**
1. Branch off `dev`: `git checkout -b feat/my-thing dev`
2. PR → `dev` for review
3. Release PR: `dev` → `main` triggers production deploy on both platforms

**What happens on each push:**
- Push to `main` → Vercel production URL updates + Render redeploys backend
- Push to `dev` or any other branch → Vercel creates a throwaway preview URL (does NOT update production); Render ignores it (only watches `main`)

---

## Rules for Claude Code Agents

> These rules apply to every Claude Code agent working in this repository, including the primary session.

### ⚠️ NEVER push directly to `main`

`main` is the production branch. Direct pushes to `main` bypass review and trigger an immediate production deployment. **Do not push to `main` under any circumstances.**

### Always work on `dev` (or a feature branch off `dev`)

Before making any changes:
```bash
git checkout dev
git pull origin dev
```

If the work is a distinct feature or fix, create a feature branch:
```bash
git checkout -b feat/short-description dev
```

Push all changes to `dev` or the feature branch:
```bash
git push origin dev          # or: git push origin feat/short-description
```

### After pushing, ask the user to merge

After every push, end with a message like:

> Changes are on `dev`. When you're ready to deploy to production, open a Pull Request from `dev` → `main` on GitHub and merge it there.

Do not merge `dev` → `main` yourself. The human reviews and merges.

### Checking which branch you're on

```bash
git branch --show-current
```

If the output is `main`, switch to `dev` before touching any files:
```bash
git checkout dev
```

---

## Stack Deep-Dive

### Backend

| Concern | Technology |
|---|---|
| Framework | FastAPI (Python 3.12) |
| Database | PostgreSQL 16 (Neon in production, Docker locally) |
| ORM | SQLAlchemy (sync) |
| Migrations | Alembic |
| Cache / sessions | Redis 7 (Upstash in production, Docker locally) |
| Object storage | Cloudinary (production) / MinIO (local dev) |
| Auth | Clerk JWT RS256 dependency + HTTP Basic Auth for admin |
| Config | pydantic-settings (reads from `.env`) |
| Tests | pytest + pytest-cov |

**Why sync SQLAlchemy, not async?**
Connection pool management with async SQLAlchemy adds significant complexity (particularly around session scoping in FastAPI dependencies) for a project at this scale. The sync driver is simpler to reason about and sufficient for current load. This is a deliberate choice — do not migrate to async unless there is a measured performance bottleneck that justifies it.

**Why Clerk for auth instead of custom JWT?**
Clerk handles token rotation, JWKS endpoint, device sessions, and social login out of the box. Rolling a custom JWT system would add maintenance burden with no benefit at this stage. The backend validates Clerk-issued RS256 JWTs via the JWKS URL. `DEV_BYPASS_AUTH=true` skips Clerk validation locally.

**Why Neon for the database (not Render Postgres)?**
Render's free Postgres expires after 90 days. Neon's free tier is permanent (0.5 GB, PostgreSQL 16). Neon is also serverless — it scales to zero and back up instantly.

**Why Upstash for Redis (not Render Redis)?**
Same reason: Render's free Redis expires after 90 days. Upstash's free tier is permanent (10,000 commands/day, 256 MB). Upstash requires TLS — use `rediss://` (double-s) in `REDIS_URL`.

**Why Cloudinary for image storage (not S3/MinIO in production)?**
Cloudflare R2 (original plan) moved to a paid model. Cloudinary has a generous permanent free tier (25 GB storage, 25 GB bandwidth/month) and a simple upload API that requires no bucket configuration. The storage module abstracts both providers behind the same interface — switching to S3-compatible storage only requires changing `STORAGE_PROVIDER` and the relevant env vars; no code changes needed.

**Storage provider abstraction**
`backend/app/core/storage.py` exposes three functions: `upload_bytes()`, `public_url()`, `ensure_bucket_exists()`. Both providers implement the same interface:
- `STORAGE_PROVIDER=s3` → uses boto3; works with MinIO, AWS S3, Cloudflare R2, Backblaze B2
- `STORAGE_PROVIDER=cloudinary` → uses Cloudinary SDK; `upload_bytes()` returns the full CDN URL, which is stored in the DB as `image_url`; `public_url(key)` returns `key` unchanged (it is already the URL)

**Anti-cheat design**
- Answers are stored only in the database. They are never included in any API response that the client receives before submission.
- Question IDs are stored in the server-side session; the client cannot fabricate or replay a question.
- One attempt per question is enforced server-side.
- Image filenames are UUIDs — there is no relationship between filename and cricketer name.
- Fuzzy matching (Levenshtein distance) runs server-side only. The threshold is configurable via `FUZZY_MATCH_THRESHOLD`.

**Per-word scrambling**
Multi-word names are scrambled word-by-word, with a space sentinel character marking word boundaries. This preserves the structure of the name (first name / last name separation) while still scrambling the letters within each word.

### Frontend

| Concern | Technology |
|---|---|
| Build tool | Vite 8 |
| Framework | React 19 + TypeScript 5.8 |
| Routing | TanStack Router v1 (file-based) |
| Data fetching | TanStack Query v5 |
| Auth | Clerk v5 (`@clerk/react`) |
| Styling | Tailwind v4 |
| Components | shadcn/ui + lucide-react |

**SPA routing on Vercel**
`frontend/vercel.json` rewrites all routes to `index.html` so that direct navigation to `/admin`, `/games`, etc. works. Without this, Vercel returns 404 for any route that doesn't correspond to a real file.

### Infrastructure (local dev)

All services run via Docker Compose:

| Service | Image | Port |
|---|---|---|
| PostgreSQL | postgres:16-alpine | 5432 |
| Redis | redis:7-alpine | 6379 |
| MinIO | minio/minio | 9000 (API), 9001 (console) |
| pgAdmin | dpage/pgadmin4 | 5050 |

---

## Directory Structure

```
babyoverhatrick/
├── backend/
│   ├── .python-version         # Pins Python 3.12 for Render (prevents default to 3.14+).
│   ├── alembic/                # DB migration scripts and env.py. Run via `python -m alembic`.
│   ├── app/
│   │   ├── main.py             # FastAPI app factory, middleware, router registration.
│   │   ├── admin/              # SQLAdmin view registrations (cricketer, question, session models).
│   │   ├── auth/               # Clerk JWT FastAPI dependency. DEV_BYPASS_AUTH short-circuits this.
│   │   ├── core/
│   │   │   ├── config.py       # pydantic-settings Settings class. All env vars land here.
│   │   │   ├── db.py           # SQLAlchemy engine + session factory + get_db dependency.
│   │   │   ├── redis.py        # Redis client factory.
│   │   │   └── storage.py      # Storage abstraction: Cloudinary or S3-compatible (MinIO/R2/B2/S3).
│   │   ├── daily_challenge/    # Daily challenge selection logic.
│   │   ├── models/             # SQLAlchemy ORM models (Cricketer, Question, Session, Answer, …).
│   │   ├── routers/            # One file per API domain:
│   │   │   ├── games.py        # GET /api/games — list available games.
│   │   │   ├── sessions.py     # Session lifecycle (create, submit, hint, complete).
│   │   │   ├── leaderboards.py # GET /api/leaderboard.
│   │   │   ├── daily.py        # GET /api/daily.
│   │   │   ├── cricketers.py   # Cricketer lookup / autocomplete.
│   │   │   ├── users.py        # Clerk user sync.
│   │   │   └── admin.py        # Admin content API (Basic Auth, CRUD).
│   │   ├── scripts/
│   │   │   └── seed.py         # Seed the database with initial cricketer/question data.
│   │   └── share_cards/        # STUB — Pillow-based share card image generation (not implemented).
│   └── requirements.txt
├── .claude/agents/             # Claude Code skill definitions (e.g. add-game.md).
├── frontend/
│   ├── vercel.json             # Rewrites all routes to index.html for SPA routing on Vercel.
│   └── src/
│       ├── components/         # Shared UI components:
│       │   ├── BrandHeader     # Page-level logo header (mobile only — hidden on desktop).
│       │   ├── BottomNav       # Bottom tab bar (mobile) / unified top nav (desktop: logo + nav + auth).
│       │   ├── ResultScreen    # End-of-game result display.
│       │   └── SignInSheet     # Clerk sign-in drawer/sheet.
│       ├── lib/
│       │   ├── api.ts          # All API call functions + TypeScript types. Add new calls here.
│       │   ├── auth.ts         # Clerk auth header helper (buildAuthHeaders).
│       │   ├── config.ts       # Frontend config constants (game settings, endpoints).
│       │   ├── game-data.ts    # Static game metadata (display names, descriptions, icons).
│       │   └── utils.ts        # shadcn/ui cn() helper.
│       └── routes/             # File-based routes (TanStack Router). One file = one route.
│           ├── index.tsx       # /
│           ├── games.tsx       # /games
│           ├── play/
│           │   ├── guess.tsx   # /play/guess — Guess the Cricketer game.
│           │   └── unscramble.tsx  # /play/unscramble — Unscramble the Name game.
│           ├── leaderboard.tsx # /leaderboard
│           ├── signin.tsx      # /signin
│           └── admin.tsx       # /admin
├── .env.example                # Template for required environment variables.
├── docker-compose.yml          # Local dev services.
├── CLAUDE.md                   # This file.
├── README.md                   # Project overview for contributors and users.
├── CONTRIBUTING.md             # Contribution guidelines.
└── SETUP.md                    # Full local development setup walkthrough.
```

---

## Environment Variables Reference

All variables are consumed by `backend/app/core/config.py` (backend) or by Vite at build time (frontend). See `.env.example` for the canonical list.

| Variable | Layer | Purpose |
|---|---|---|
| `DATABASE_URL` | Backend | PostgreSQL connection string |
| `REDIS_URL` | Backend | Redis connection string — use `rediss://` (TLS) for Upstash |
| `STORAGE_PROVIDER` | Backend | `s3` (default, MinIO/R2/B2/AWS) or `cloudinary` |
| `STORAGE_ENDPOINT` | Backend | S3-compatible endpoint URL (used when `STORAGE_PROVIDER=s3`) |
| `STORAGE_ACCESS_KEY` | Backend | S3 access key |
| `STORAGE_SECRET_KEY` | Backend | S3 secret key |
| `STORAGE_BUCKET` | Backend | S3 bucket name |
| `STORAGE_PUBLIC_URL` | Backend | Public base URL for serving stored images (S3 only) |
| `CLOUDINARY_CLOUD_NAME` | Backend | Cloudinary cloud name (used when `STORAGE_PROVIDER=cloudinary`) |
| `CLOUDINARY_API_KEY` | Backend | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Backend | Cloudinary API secret |
| `CLERK_SECRET_KEY` | Backend | Clerk server-side secret for token verification |
| `CLERK_JWKS_URL` | Backend | URL to Clerk JWKS endpoint for RS256 validation |
| `VITE_CLERK_PUBLISHABLE_KEY` | Frontend | Clerk publishable key (embedded in client bundle) |
| `VITE_API_URL` | Frontend | Backend API base URL (e.g. `https://babyoverhatrick.onrender.com`) |
| `ADMIN_USERNAME` | Backend | HTTP Basic Auth username for admin endpoints |
| `ADMIN_PASSWORD` | Backend | HTTP Basic Auth password for admin endpoints |
| `DEV_BYPASS_AUTH` | Backend | Set `true` to skip Clerk JWT validation in local dev — **never `true` in production** |
| `FUZZY_MATCH_THRESHOLD` | Backend | Levenshtein distance threshold for answer fuzzy matching |
| `QUESTIONS_PER_SESSION` | Backend | Number of questions served per game session |
| `ALLOWED_ORIGINS` | Backend | JSON array of allowed CORS origins, e.g. `["https://example.vercel.app"]` |

**Never commit `.env` to the repository. It is in `.gitignore`. Files matching `*.env` are also gitignored (e.g. `render.env`, `vercel.env`).**

---

## Files NOT to Edit Directly

| File | Reason |
|---|---|
| `frontend/src/routeTree.gen.ts` | Auto-generated by TanStack Router. Regenerated on every `pnpm dev` / `pnpm build`. |
| `.venv/` | Python virtual environment. Managed by pip. |
| `alembic/versions/` | Do not edit existing migration files. Add new ones with `alembic revision --autogenerate`. |

---

## Running the Project Locally

Quick reference — see `SETUP.md` for the full walkthrough.

```bash
# 1. Start backing services
docker compose up -d

# 2. Backend
cd backend
pip install -r requirements.txt
python -m alembic upgrade head
python -m app.scripts.seed
uvicorn app.main:app --reload

# 3. Frontend (separate terminal)
cd frontend
pnpm install
pnpm dev
```

The app will be at http://localhost:5173. The FastAPI docs are at http://localhost:8000/docs.

Set `DEV_BYPASS_AUTH=true` in `.env` to skip Clerk auth during local development.

---

## Running Tests

```bash
cd backend
pytest --cov=app --cov-report=term-missing
```

Test files live in `backend/tests/`. Coverage must remain above 90%. Every new backend endpoint must have tests.

---

## Deployment

### Current production setup

| Concern | Service | Notes |
|---|---|---|
| Frontend | Vercel | Auto-deploys from `main`. Root directory: `frontend`. |
| Backend | Render | Auto-deploys from `main`. Root directory: `backend`. Python 3.12 (pinned via `backend/.python-version`). |
| Database | Neon | PostgreSQL 16. Run `python -m alembic upgrade head` after first deploy and after any migration. |
| Cache | Upstash | Redis. Use `rediss://` URL (TLS required). |
| Images | Cloudinary | Set `STORAGE_PROVIDER=cloudinary` and the three `CLOUDINARY_*` env vars. |

### Render start command

```
python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Migrations run automatically on every deploy. No shell access needed.

### Running a migration

New migrations are created locally and pushed; Render applies them on deploy.

```bash
# 1. Make your model change
# 2. Generate the migration
cd backend
python -m alembic revision --autogenerate -m "describe the change"
# 3. Test it locally
python -m alembic upgrade head
# 4. Commit and push — Render runs it on deploy
```

### Seeding the production database

Since Render's free tier has no shell access, the seed script runs locally against the production database. The `.env` file contains the Neon connection string, so this works out of the box:

```bash
cd backend
python -m app.scripts.seed
```

---

## Forward Direction — CI/CD (not yet implemented)

The goal is a GitHub Actions pipeline that:
1. **On PR to `dev`** — runs the full test suite (`pytest --cov`). Blocks merge if tests fail or coverage drops below 90%.
2. **On merge to `main`** — runs tests again, then triggers a Render deploy via deploy hook. Vercel deploys automatically via its GitHub integration (no action needed).

Planned file: `.github/workflows/ci.yml`

What will need to change when this is set up:
- **Render**: disable "Auto-Deploy" in service settings and generate a Deploy Hook URL instead (used by the GitHub Action).
- **Vercel**: no change needed — it deploys automatically on push to `main`.
- **GitHub**: add `RENDER_DEPLOY_HOOK` as a repository secret.

---

## Future Work / Open TODOs

| Item | Location | Status |
|---|---|---|
| Share card image generation | `backend/app/share_cards/` | Stub exists, Pillow logic not implemented |
| Streaks | `backend/app/routers/` | No endpoint yet; model design TBD |
| CI/CD pipeline | `.github/workflows/` | Design documented above; not yet implemented |
| Phase 2 — Multiplayer | — | Not started |
| Phase 3 — Platform features | — | Not started |

---

## Conventions to Follow When Adding New Code

### Backend

- **Config**: all new configuration values go in `backend/app/core/config.py` as typed `pydantic-settings` fields, and in `.env.example` with a comment.
- **Database**: new columns or tables require an Alembic migration (`alembic revision --autogenerate -m "description"`). Never alter tables manually in production or in the ORM models without a migration.
- **Routers**: one router file per domain. Register it in `app/main.py` with its prefix. Add the prefix to the route list in this document.
- **Anti-cheat**: answers must never appear in any response payload sent to the client before the client submits an answer. Review every new endpoint against this rule.
- **Auth**: use the `get_current_user` dependency from `app/auth/` for player-facing endpoints. Use the `require_admin` dependency for admin endpoints. Do not write ad-hoc auth checks inline.
- **Type hints**: all function signatures, all the way down. No bare `dict` or `Any`.
- **Docstrings**: public functions and classes get a one-line docstring minimum.
- **No hardcoded secrets**: use `settings` from `app/core/config.py`.

### Frontend

- **API calls**: all API calls go through `frontend/src/lib/api.ts`. Do not use `fetch` directly in components.
- **Types**: define TypeScript types in `api.ts` alongside the functions that return them. Use `strict` mode — no `any`.
- **Routes**: new pages are new files in `frontend/src/routes/`. TanStack Router picks them up automatically; `routeTree.gen.ts` is regenerated — do not touch it.
- **Styling**: Tailwind utility classes. Follow existing component patterns. shadcn/ui for new UI primitives.
- **Config constants**: frontend config values (e.g. timer durations, question counts shown to the user) go in `frontend/src/lib/config.ts`.
- **No answer exposure**: components must not store, log, or render answer values received from the server. The server does not send them — keep it that way.
