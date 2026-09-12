# CLAUDE.md — BabyOverHattrick

This file is the primary context document for Claude Code agents working on this repository. Read it fully before touching any code.

---

## Project Overview

**BabyOverHattrick** is a cricket trivia game platform. Players test their cricket knowledge through a growing set of mini-games — image-based identification, name unscrambling, and more in later phases. The platform supports both guest play (no account required) and registered accounts (via Clerk), with a unified leaderboard merging both.

The target audience is cricket fans who want bite-sized, social trivia. The Instagram presence is at https://www.instagram.com/babyoverhattrick.

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
- **Object storage** — MinIO locally, Cloudflare R2 in production (same S3-compatible API). UUID filenames for images prevent answer inference from URLs.

### Stubs / not yet implemented

- `backend/app/share_cards/` — share card image generation using Pillow. The module exists but produces no output.
- Streaks — the concept exists but there is no API endpoint yet.
- Phase 2 — multiplayer (not started).
- Phase 3 — broader platform features (not started).

---

## Stack Deep-Dive

### Backend

| Concern | Technology |
|---|---|
| Framework | FastAPI (Python 3.12) |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy (sync) |
| Migrations | Alembic |
| Cache / sessions | Redis 7 |
| Object storage | MinIO (local) / Cloudflare R2 (prod) |
| Auth | Clerk JWT RS256 dependency + HTTP Basic Auth for admin |
| Config | pydantic-settings (reads from `.env`) |
| Tests | pytest + pytest-cov |

**Why sync SQLAlchemy, not async?**
Connection pool management with async SQLAlchemy adds significant complexity (particularly around session scoping in FastAPI dependencies) for a project at this scale. The sync driver is simpler to reason about and sufficient for current load. This is a deliberate choice — do not migrate to async unless there is a measured performance bottleneck that justifies it.

**Why Clerk for auth instead of custom JWT?**
Clerk handles token rotation, JWKS endpoint, device sessions, and social login out of the box. Rolling a custom JWT system would add maintenance burden with no benefit at this stage. The backend validates Clerk-issued RS256 JWTs via the JWKS URL. `DEV_BYPASS_AUTH=true` skips Clerk validation locally.

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

**Why MinIO locally / R2 in production?**
Both expose an S3-compatible API. The backend uses the same boto3/httpx storage client in both environments — only the endpoint URL, access key, and bucket name change. This eliminates any environment-specific code paths in the application layer.

### Infrastructure (local dev)

All services run via Docker Compose:

| Service | Image | Port |
|---|---|---|
| PostgreSQL | postgres:16-alpine | 5432 |
| Redis | redis:7-alpine | 6379 |
| MinIO | minio/minio | 9000 (API), 9001 (console) |
| pgAdmin | dpage/pgadmin4 | 5050 |

In production: backend on Render, frontend on Vercel, images on Cloudflare R2.

---

## Directory Structure

```
babyoverhatrick/
├── backend/
│   ├── alembic/                # DB migration scripts and env.py. Run via `python -m alembic`.
│   ├── app/
│   │   ├── main.py             # FastAPI app factory, middleware, router registration.
│   │   ├── admin/              # SQLAdmin view registrations (cricketer, question, session models).
│   │   ├── auth/               # Clerk JWT FastAPI dependency. DEV_BYPASS_AUTH short-circuits this.
│   │   ├── core/
│   │   │   ├── config.py       # pydantic-settings Settings class. All env vars land here.
│   │   │   ├── db.py           # SQLAlchemy engine + session factory + get_db dependency.
│   │   │   ├── redis.py        # Redis client factory.
│   │   │   └── storage.py      # S3-compatible storage client (MinIO / R2).
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
├── docs/                       # Developer reference docs. Not committed to the repo.
├── frontend/
│   └── src/
│       ├── components/         # Shared UI components:
│       │   ├── BrandHeader     # Top navigation / logo.
│       │   ├── BottomNav       # Mobile bottom navigation bar.
│       │   ├── ResultScreen    # End-of-game result display.
│       │   └── SignInSheet     # Clerk sign-in drawer/sheet.
│       ├── lib/
│       │   ├── api.ts          # All API call functions + TypeScript types. Add new calls here.
│       │   ├── config.ts       # Frontend config constants (game settings, endpoints).
│       │   └── game-data.ts    # Static game metadata (display names, descriptions, icons).
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
| `DATABASE_URL` | Backend | PostgreSQL connection string (`postgresql://...`) |
| `REDIS_URL` | Backend | Redis connection string (`redis://...`) |
| `STORAGE_ENDPOINT` | Backend | MinIO / R2 endpoint URL |
| `STORAGE_ACCESS_KEY` | Backend | S3 access key |
| `STORAGE_SECRET_KEY` | Backend | S3 secret key |
| `STORAGE_BUCKET` | Backend | S3 bucket name for cricketer images |
| `CLERK_SECRET_KEY` | Backend | Clerk server-side secret for token verification |
| `CLERK_JWKS_URL` | Backend | URL to Clerk JWKS endpoint for RS256 validation |
| `VITE_CLERK_PUBLISHABLE_KEY` | Frontend | Clerk publishable key (embedded in client bundle) |
| `ADMIN_USERNAME` | Backend | HTTP Basic Auth username for admin endpoints |
| `ADMIN_PASSWORD` | Backend | HTTP Basic Auth password for admin endpoints |
| `DEV_BYPASS_AUTH` | Backend | Set `true` to skip Clerk JWT validation in local dev |
| `FUZZY_MATCH_THRESHOLD` | Backend | Levenshtein distance threshold for answer fuzzy matching |
| `QUESTIONS_PER_SESSION` | Backend | Number of questions served per game session |

**Never commit `.env` to the repository. It is in `.gitignore`.**

---

## Files NOT to Edit Directly

| File | Reason |
|---|---|
| `frontend/src/routeTree.gen.ts` | Auto-generated by TanStack Router from files in `src/routes/`. Re-generated on every `pnpm dev` / `pnpm build` run. Manual edits will be overwritten. |
| `.venv/` | Python virtual environment. Managed by pip, never edited manually. |
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

| Layer | Host |
|---|---|
| Backend | Render (web service, Python runtime) |
| Frontend | Vercel |
| Images | Cloudflare R2 (S3-compatible, same client code as MinIO) |
| Database | Render PostgreSQL or managed Postgres |
| Redis | Render Redis |

See `INFRA.md` (in `docs/`, not committed) for the full deployment procedure, environment variable setup on each platform, and free-tier constraints.

---

## Future Work / Open TODOs

| Item | Location | Status |
|---|---|---|
| Share card image generation | `backend/app/share_cards/` | Stub exists, Pillow logic not implemented |
| Streaks | `backend/app/routers/` | No endpoint yet; model design TBD |
| Phase 2 — Multiplayer | — | Not started |
| Phase 3 — Platform features | — | Not started |
| CI/CD pipeline | `.github/workflows/` | Not set up |

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
