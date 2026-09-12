from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from redis import Redis
from app.core.db import get_db
from app.core.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: Session = Depends(get_db), r: Redis = Depends(get_redis)):
    """
    Health check endpoint. Used by Render keep-alive cron and load balancers.
    Verifies Postgres and Redis connectivity.
    """
    checks = {}

    # Postgres
    try:
        db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"

    # Redis
    try:
        r.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "services": checks,
    }
