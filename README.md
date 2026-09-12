# BabyOverHattrick

### The cricket trivia game platform.

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3120/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS v4](https://img.shields.io/badge/Tailwind_CSS-v4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)

---

BabyOverHattrick is a cricket trivia game platform where fans compete across a set of bite-sized mini-games — identifying cricketers from images, unscrambling names, and more to come. Play instantly as a guest or create an account to track your score on the global leaderboard.

Follow us on Instagram: [@babyoverhattrick](https://www.instagram.com/babyoverhattrick?stkn=YTNvaThzODZ4OWI5)

---

## Features

- **Two game modes** (Phase 1): Guess the Cricketer and Unscramble the Name
- **No account required** — guests can play immediately without signing up
- **Guest score continuity** — guest scores appear on the leaderboard alongside registered users
- **Daily challenges** — a fresh question set every day
- **Unified leaderboard** — registered users (best score per day) and guests (individual scores) merged and ranked
- **Admin content CMS** — add, edit, and delete cricketers and question sets through a protected admin panel
- **Anti-cheat by design** — answers never leave the server before submission; one attempt per question enforced server-side; image filenames are UUIDs
- **Clerk authentication** — secure, session-managed login for registered players (RS256 JWT)
- **Fuzzy answer matching** — server-side Levenshtein distance matching so minor typos are forgiven

---

## Screenshots

_Screenshots coming soon._

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy (sync), Alembic, PostgreSQL 16, Redis 7, pydantic-settings |
| **Frontend** | Vite 8, React 19, TypeScript 5.8, TanStack Router v1, TanStack Query v5, Clerk v5, Tailwind v4, shadcn/ui |
| **Infrastructure** | Docker Compose (local), Render (backend), Vercel (frontend), Cloudflare R2 (images), MinIO (local object storage) |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for local backing services)
- [Node.js 20+](https://nodejs.org/) and [pnpm](https://pnpm.io/)
- [Python 3.12+](https://www.python.org/)

---

## Quick Start

> For a full walkthrough including environment variable descriptions, Clerk setup, and MinIO bucket configuration, see [SETUP.md](./SETUP.md).

**1. Clone the repository**

```bash
git clone https://github.com/zzabi/babyoverhatrick.git
cd babyoverhatrick
```

**2. Copy the environment template**

```bash
cp .env.example .env
# Edit .env and fill in the required values.
# Set DEV_BYPASS_AUTH=true to skip Clerk during local development.
```

**3. Start backing services**

```bash
docker compose up -d
# Starts PostgreSQL, Redis, MinIO, and pgAdmin.
```

**4. Set up and run the backend**

```bash
cd backend
pip install -r requirements.txt
python -m alembic upgrade head
python -m app.scripts.seed
uvicorn app.main:app --reload
# API available at http://localhost:8000
# Interactive API docs at http://localhost:8000/docs
```

**5. Set up and run the frontend** _(new terminal)_

```bash
cd frontend
pnpm install
pnpm dev
# App available at http://localhost:5173
```

---

## Game Flows

### Guess the Cricketer

A photo of a cricketer is displayed. The player has 15 seconds to type the correct name using an autocomplete dropdown. Answers are submitted to the server, which applies fuzzy matching server-side to allow for minor spelling variations. The answer is never exposed to the client before submission.

### Unscramble the Name

The player is shown scrambled letter tiles representing a cricketer's name. Each word in the name is scrambled independently. The player has 30 seconds to type the correct name. If stuck, three progressively specific hints are available: country, playing role, and a database-defined hint. As with all games, fuzzy matching is applied server-side on submission.

---

## Admin Panel

The admin panel is accessible at `/admin`. It is protected by HTTP Basic Auth (credentials set via `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env`).

Through the admin panel you can:

- Add, edit, and delete cricketers (including uploading images to object storage)
- Create and manage question sets for each game type
- Add, edit, and delete individual questions

A SQLAdmin interface is also served by the backend at `/admin` (same credentials), providing a direct database-level view of all models.

---

## API Documentation

FastAPI generates interactive API documentation automatically. In development, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

All player-facing endpoints are prefixed with `/api/`. The main API domains are:

| Prefix | Purpose |
|---|---|
| `/api/games` | List available games |
| `/api/sessions` | Session lifecycle (create, submit answers, hints, complete) |
| `/api/leaderboard` | Leaderboard data |
| `/api/daily` | Daily challenge question set |
| `/api/cricketers` | Cricketer lookup and autocomplete |
| `/api/users` | Clerk user sync |
| `/api/admin` | Content management (Basic Auth required) |

---

## Running Tests

```bash
cd backend
pytest --cov=app --cov-report=term-missing
```

Test files live in `backend/tests/`. Coverage must remain above 90%.

---

## Deployment

| Layer | Platform | Notes |
|---|---|---|
| Backend | Render (web service) | Python 3.12 runtime; start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Frontend | Vercel | Root directory `frontend`; Vite preset |
| Database | Render Postgres | Managed PostgreSQL 16 |
| Cache | Render Redis | Used for session storage |
| Images | Cloudflare R2 | S3-compatible; same client code as local MinIO |

Configure environment variables from `.env.example` on each platform. Run `python -m alembic upgrade head` on first backend deploy to create the schema. See [SETUP.md](./SETUP.md) for the full environment variable reference.

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on branching, code standards, testing requirements, and the pull request process.

---

## License

This project is licensed under the [MIT License](./LICENSE).
