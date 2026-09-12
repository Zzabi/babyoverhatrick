# Setup Guide

Complete instructions for bringing up the BabyOverHattrick platform on a fresh machine. Follow every step in order — do not skip any.

---

## Prerequisites

Install these before starting:

| Tool | Version | Install |
|---|---|---|
| Docker Desktop | Latest | https://docker.com/products/docker-desktop |
| Node.js | 20+ | https://nodejs.org (or via `nvm`) |
| pnpm | 9+ | `npm install -g pnpm` |
| Python | 3.12 | https://python.org or `pyenv install 3.12` |
| Git | Any | https://git-scm.com |

Verify:
```bash
docker --version       # Docker version 24+
node --version         # v20+
pnpm --version         # 9+
python3.12 --version   # Python 3.12.x
```

---

## 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/babyoverhatrick.git
cd babyoverhatrick
```

---

## 2. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and set the following. The defaults work for local development without changes — only the ones marked **required** need real values:

```bash
# ── Required: generate a random secret key ────────────────────────────────────
SECRET_KEY=$(openssl rand -hex 32)
# Paste the output into .env: SECRET_KEY=<output>

# ── Required: Clerk authentication ───────────────────────────────────────────
# Sign up free at https://clerk.com → create an application
# Copy the keys from your Clerk dashboard:
CLERK_SECRET_KEY=sk_test_...
CLERK_JWKS_URL=https://<your-instance>.clerk.accounts.dev/.well-known/jwks.json

# ── Optional: skip Clerk auth entirely during local development ───────────────
DEV_BYPASS_AUTH=true   # set to true to skip JWT validation locally
DEV_USER_ID=local-dev
DEV_USER_EMAIL=dev@local.test

# ── Admin panel credentials ───────────────────────────────────────────────────
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme    # change this before any real deployment
```

All other values (database URL, Redis URL, MinIO credentials) are pre-configured for the Docker Compose setup and do not need to change for local development.

### Frontend environment

```bash
cp frontend/.env.local frontend/.env.local.bak  # if one already exists
```

Create `frontend/.env.local`:
```bash
VITE_API_URL=http://localhost:8000
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...   # from your Clerk dashboard
```

> **Without Clerk keys**: set `DEV_BYPASS_AUTH=true` in `.env` — the backend skips JWT validation. The frontend will show a console warning but still work.

---

## 3. Start Infrastructure (Docker)

```bash
docker compose up -d
```

This starts:
- **PostgreSQL 16** on port 5432 — primary database
- **Redis 7** on port 6379 — caching
- **MinIO** on port 9000 (S3 API) and 9001 (web UI) — local image storage
- **pgAdmin** on port 5050 — optional database GUI

Wait for all services to be healthy (~30 seconds):

```bash
docker compose ps
# All containers should show "healthy" or "running"
```

---

## 4. Set Up the Backend

### 4a. Create a Python virtual environment

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows PowerShell
```

### 4b. Install dependencies

```bash
pip install -r requirements.txt
```

### 4c. Run database migrations

```bash
python -m alembic upgrade head
```

This creates all 13 tables in the `gameplatform_dev` database. You should see output like:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 3506816003f2, initial schema
INFO  [alembic.runtime.migration] Running upgrade 3506816003f2 -> e425cd27d2a8, add cricketer table
```

### 4d. Seed the database

```bash
python -m app.scripts.seed
```

This creates:
- 2 games: `guess-the-cricketer` and `unscramble-the-name`
- Default question sets for each game
- 27 sample cricketers in the autocomplete list

Safe to run multiple times — skips existing records.

### 4e. Start the backend server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify it's running:
```bash
curl http://localhost:8000/health
# {"status":"ok","services":{"postgres":"ok","redis":"ok"}}
```

The API docs are available at: http://localhost:8000/docs

---

## 5. Set Up MinIO (Image Storage)

### 5a. Create the storage bucket

Open the MinIO web UI: http://localhost:9001

- Log in with `minioadmin` / `minioadmin` (or whatever you set in `.env`)
- Click **Buckets** → **Create Bucket**
- Name: `gameplatform-assets`
- Click **Create Bucket**

### 5b. Make the bucket public (for image serving)

In the MinIO UI, click the bucket → **Access Policy** → set to **public**. This allows the frontend to display uploaded images without authentication.

> Alternatively, run this with the MinIO CLI (`mc`):
> ```bash
> mc alias set local http://localhost:9000 minioadmin minioadmin
> mc mb local/gameplatform-assets
> mc anonymous set download local/gameplatform-assets
> ```

---

## 6. Set Up the Frontend

```bash
cd ../frontend    # from the backend directory, or cd frontend from the repo root
pnpm install
pnpm dev
```

The frontend runs at http://localhost:5173

---

## 7. Verify Everything Works

Open http://localhost:5173 in your browser. You should see the BabyOverHattrick homepage.

Run through this checklist:

- [ ] Homepage loads with two game cards
- [ ] "Play now" navigates to the guess game setup screen
- [ ] Backend health check passes: `curl http://localhost:8000/health`
- [ ] Admin panel accessible: http://localhost:5173/admin (use ADMIN_USERNAME / ADMIN_PASSWORD from `.env`)
- [ ] API docs visible: http://localhost:8000/docs

---

## 8. Add Your First Question (Admin Panel)

1. Go to http://localhost:5173/admin
2. Enter your admin credentials
3. Click **"Guess the Cricketer"** tab
4. Select a question set (or create one)
5. Upload a cricketer photo, fill in the answer, click **Add Question**
6. Play the game to verify the question appears

---

## Running Tests

```bash
cd backend

# Create the test database (first time only)
python -c "
import psycopg2, os
conn = psycopg2.connect('postgresql://gameplatform:localpassword@localhost:5432/postgres')
conn.autocommit = True
cur = conn.cursor()
cur.execute(\"SELECT 1 FROM pg_database WHERE datname='gameplatform_test'\")
if not cur.fetchone():
    cur.execute('CREATE DATABASE gameplatform_test')
    print('Created gameplatform_test')
else:
    print('gameplatform_test already exists')
conn.close()
"

# Install test dependencies
pip install -r requirements-test.txt

# Run the test suite
pytest --cov=app --cov-report=term-missing
```

Tests must maintain ≥ 90% coverage. See [CONTRIBUTING.md](CONTRIBUTING.md) for full testing guidelines.

---

## Common Problems

### "connection refused" on port 5432
Docker containers are not running. Run `docker compose up -d` and wait for them to be healthy.

### "database does not exist"
The database name in `.env` must match `POSTGRES_DB` in the Docker environment. Both default to `gameplatform_dev`.

### "UNAUTHORIZED" in the admin panel
Double-check `ADMIN_USERNAME` and `ADMIN_PASSWORD` in your `.env`. Restart the backend after changing them.

### Images not appearing after upload
The MinIO bucket must exist and be public (Step 5). Check `STORAGE_BUCKET` and `STORAGE_PUBLIC_URL` in `.env` match the bucket you created.

### Frontend shows "Failed to fetch"
The `VITE_API_URL` in `frontend/.env.local` must match where the backend is running (default: `http://localhost:8000`). CORS is configured via `ALLOWED_ORIGINS` in `.env`.

### TanStack Router route not found after adding a new file
Run `pnpm dev` or `pnpm build` — the TanStack Router plugin auto-generates `src/routeTree.gen.ts` on build. Never edit this file manually.

### Alembic "Target database is not up to date"
Run `python -m alembic upgrade head` again. If there are conflicts, run `python -m alembic history` to see migration state.

---

## Environment Variable Reference

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://gameplatform:localpassword@localhost:5432/gameplatform_dev` | PostgreSQL connection string |
| `REDIS_URL` | `redis://:localpassword@localhost:6379` | Redis connection string |
| `SECRET_KEY` | _(none)_ | **Required** — session signing key (generate with `openssl rand -hex 32`) |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS allowed origins (comma-separated) |
| `STORAGE_ENDPOINT` | `http://localhost:9000` | S3-compatible storage URL |
| `STORAGE_ACCESS_KEY` | `minioadmin` | Storage access key |
| `STORAGE_SECRET_KEY` | `minioadmin` | Storage secret key |
| `STORAGE_BUCKET` | `gameplatform-assets` | Bucket name |
| `STORAGE_PUBLIC_URL` | `http://localhost:9000/gameplatform-assets` | Public base URL for assets |
| `CLERK_SECRET_KEY` | _(none)_ | Clerk backend secret key |
| `CLERK_JWKS_URL` | _(none)_ | Clerk JWKS endpoint URL |
| `DEV_BYPASS_AUTH` | `false` | Set `true` to skip Clerk JWT validation locally |
| `ADMIN_USERNAME` | `admin` | Admin panel username |
| `ADMIN_PASSWORD` | `changeme` | Admin panel password |
| `FUZZY_MATCH_THRESHOLD` | `0.75` | Answer fuzzy match similarity floor (0.0–1.0) |
| `QUESTIONS_PER_SESSION` | `10` | Questions dealt per game session |
| `SENTRY_DSN` | _(empty)_ | Optional Sentry error-tracking DSN |

| Frontend Variable | Description |
|---|---|
| `VITE_API_URL` | Backend URL (e.g. `http://localhost:8000`) |
| `VITE_CLERK_PUBLISHABLE_KEY` | Clerk publishable key for the frontend |

---

## Production Deployment

The production stack runs on:
- Backend on Render
- Frontend on Vercel
- PostgreSQL on Render managed Postgres
- Redis on Render Redis
- Images on Cloudflare R2

Configure the environment variables from `.env.example` on each platform. All application code is the same — only the connection strings change.

---

## Stopping the Stack

```bash
docker compose down           # stop containers, preserve data
docker compose down -v        # stop containers AND wipe all data (full reset)
```
