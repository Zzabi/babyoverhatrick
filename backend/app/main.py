import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqladmin import Admin
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
import secrets
from app.core.config import settings
from app.core.db import engine
from app.routers import health, games, sessions, users, leaderboards, daily
from app.routers import cricketers, admin_content
from app.admin.views import register_admin_views

# ── Sentry ────────────────────────────────────────────────────────────────────
if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment, traces_sample_rate=0.1)


# ── SQLAdmin authentication ───────────────────────────────────────────────────
class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username", "")
        password = form.get("password", "")
        ok_user = secrets.compare_digest(str(username), settings.admin_username)
        ok_pass = secrets.compare_digest(str(password), settings.admin_password)
        if ok_user and ok_pass:
            request.session.update({"admin_authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("admin_authenticated"))


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="babyoverhattrick API",
    version="0.1.0",
    description="Cricket trivia game platform API",
    docs_url="/docs",
    redoc_url=None,
)

# Session middleware required for SQLAdmin auth
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── SQLAdmin panel (/admin) ───────────────────────────────────────────────────
authentication_backend = AdminAuth(secret_key=settings.secret_key)
admin = Admin(app, engine, title="babyoverhattrick CMS", authentication_backend=authentication_backend)
register_admin_views(admin)

# ── API Routers ───────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(games.router,          prefix="/api/games",        tags=["games"])
app.include_router(sessions.router,       prefix="/api/sessions",     tags=["sessions"])
app.include_router(users.router,          prefix="/api/users",        tags=["users"])
app.include_router(leaderboards.router,   prefix="/api/leaderboards", tags=["leaderboards"])
app.include_router(daily.router,          prefix="/api/daily",        tags=["daily"])
app.include_router(cricketers.router,     prefix="/api/cricketers",   tags=["cricketers"])
app.include_router(admin_content.router)  # prefix already set in router


@app.on_event("startup")
async def on_startup():
    try:
        from app.core.storage import ensure_bucket_exists
        ensure_bucket_exists()
    except Exception as exc:
        print(f"[startup] storage check skipped: {exc}")
