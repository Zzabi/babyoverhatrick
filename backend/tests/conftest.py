"""
Test configuration and shared fixtures.

Uses a separate PostgreSQL database (gameplatform_test) so dev data is never touched.
All tables are truncated between tests for isolation.

Environment: set TEST_DATABASE_URL to override the default test DB connection.
Default:     postgresql://gameplatform:localpassword@localhost:5432/gameplatform_test
"""
import os
import sys
import base64

# ── Must be set BEFORE any app.* imports ─────────────────────────────────────
# pydantic-settings reads env at Settings instantiation time.
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://gameplatform:localpassword@localhost:5432/gameplatform_test",
)
os.environ.setdefault("DATABASE_URL", TEST_DB_URL)
os.environ.setdefault("DATABASE_URL_DIRECT", TEST_DB_URL)
os.environ.setdefault("REDIS_URL", "redis://:localpassword@localhost:6379/1")
os.environ.setdefault("DEV_BYPASS_AUTH", "true")
os.environ.setdefault("ADMIN_USERNAME", "testadmin")
os.environ.setdefault("ADMIN_PASSWORD", "testpassword")
os.environ.setdefault("STORAGE_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("STORAGE_ACCESS_KEY", "minioadmin")
os.environ.setdefault("STORAGE_SECRET_KEY", "minioadmin")
os.environ.setdefault("STORAGE_BUCKET", "test-bucket")
os.environ.setdefault("STORAGE_PUBLIC_URL", "http://localhost:9000/test-bucket")
os.environ.setdefault("STORAGE_REGION", "us-east-1")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-do-not-use-in-prod")
os.environ.setdefault("ALLOWED_ORIGINS", '["http://localhost:3000","http://localhost:5173"]')
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SENTRY_DSN", "")

import pytest
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# ── Ensure gameplatform_test database exists ─────────────────────────────────

def _ensure_test_db():
    """Create gameplatform_test database if it doesn't already exist."""
    # Parse host/port/user/pass from connection string
    parts = TEST_DB_URL.replace("postgresql://", "").split("@")
    user_pass = parts[0].split(":")
    host_db = parts[1].split("/")
    host_port = host_db[0].split(":")
    user = user_pass[0]
    password = user_pass[1] if len(user_pass) > 1 else ""
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 5432
    dbname = host_db[1]

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname="postgres",  # connect to default DB to create test DB
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{dbname}"')
        cur.close()
        conn.close()
    except Exception as exc:
        # If we can't create the DB (e.g. already exists or no permissions), continue
        print(f"[conftest] test DB check: {exc}")


_ensure_test_db()

# ── SQLAlchemy engine for tests ───────────────────────────────────────────────

engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── Import app AFTER env vars and test DB are set up ─────────────────────────
# Import all models first so they register with Base.metadata
# (these must be imported before Base.metadata.create_all)
from app.models.base import Base           # noqa: E402
import app.models.game                     # noqa: E402
import app.models.question                 # noqa: E402
import app.models.session                  # noqa: E402
import app.models.user                     # noqa: E402
import app.models.cricketer                # noqa: E402
import app.models.daily                    # noqa: E402
import app.models.leaderboard              # noqa: E402
import app.models.share                    # noqa: E402
import app.models.streak                   # noqa: E402
from app.core.db import get_db             # noqa: E402
# Import as 'fastapi_app' to avoid collision with the 'app' package namespace
from app.main import app as fastapi_app    # noqa: E402


# ── Session-scoped: create / drop tables once per test run ───────────────────

@pytest.fixture(scope="session", autouse=True)
def create_tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ── Function-scoped: truncate all tables before each test ────────────────────

@pytest.fixture(autouse=True)
def truncate_tables():
    """Ensure a clean slate before every test."""
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    yield


# ── Database session fixture ──────────────────────────────────────────────────

@pytest.fixture
def db():
    """Provide a plain test DB session for direct seeding."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── TestClient fixture ────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """
    FastAPI TestClient with get_db overridden to use the test database.
    Each request from TestClient gets its own fresh session (just like production).
    """
    def override_get_db():
        s = TestingSessionLocal()
        try:
            yield s
        finally:
            s.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app, raise_server_exceptions=True) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


# ── Admin auth header ─────────────────────────────────────────────────────────

@pytest.fixture
def admin_headers():
    creds = base64.b64encode(b"testadmin:testpassword").decode()
    return {"Authorization": f"Basic {creds}"}


# ── Seed helpers — used by multiple test files ────────────────────────────────

@pytest.fixture
def guess_game(db):
    """
    Seed a 'guess-the-cricketer' game with one active set and 12 image_guess questions.
    Returns a dict with game, set, and questions.
    """
    from app.models.game import Game
    from app.models.question import QuestionSet, Question, QuestionOption

    g = Game(slug="guess-the-cricketer", name="Guess the Cricketer", status="active", sort_order=1, config={})
    db.add(g)
    db.flush()

    q_set = QuestionSet(
        game_id=g.id, name="Default Set",
        difficulty_default="medium", is_active=True, is_daily_eligible=True,
    )
    db.add(q_set)
    db.flush()

    questions = []
    for i in range(12):
        q = Question(
            set_id=q_set.id,
            question_type="image_guess",
            image_url=f"http://localhost:9000/test-bucket/questions/uuid{i:02d}.jpg",
            difficulty="medium",
            points=100,
            is_active=True,
            accepted_aliases=[],
        )
        db.add(q)
        db.flush()
        opt = QuestionOption(question_id=q.id, option_text=f"Cricketer {i}", is_correct=True)
        db.add(opt)
        questions.append(q)

    db.commit()
    # Refresh to get IDs
    db.refresh(g)
    db.refresh(q_set)
    for q in questions:
        db.refresh(q)

    return {"game": g, "set": q_set, "questions": questions}


@pytest.fixture
def unscramble_game(db):
    """
    Seed an 'unscramble-the-name' game with 12 questions.
    """
    from app.models.game import Game
    from app.models.question import QuestionSet, Question, QuestionOption

    g = Game(slug="unscramble-the-name", name="Unscramble the Name", status="active", sort_order=2, config={})
    db.add(g)
    db.flush()

    q_set = QuestionSet(
        game_id=g.id, name="Default Set",
        difficulty_default="medium", is_active=True, is_daily_eligible=True,
    )
    db.add(q_set)
    db.flush()

    questions = []
    for i in range(12):
        q = Question(
            set_id=q_set.id,
            question_type="unscramble",
            question_text=f"IND|Batter",
            difficulty="medium",
            points=100,
            is_active=True,
            accepted_aliases=[f"Hint {i}"],
        )
        db.add(q)
        db.flush()
        # For unscramble, answer is the cricketer's name (uppercase)
        name = f"KOHLI{i}"
        opt = QuestionOption(question_id=q.id, option_text=name, is_correct=True)
        db.add(opt)
        questions.append(q)

    db.commit()
    db.refresh(g)
    db.refresh(q_set)
    for q in questions:
        db.refresh(q)

    return {"game": g, "set": q_set, "questions": questions}


@pytest.fixture
def seeded_cricketer(db):
    """Seed one cricketer for autocomplete tests."""
    from app.models.cricketer import Cricketer
    c = Cricketer(name="Virat Kohli", country="IND")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c
