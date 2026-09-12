import redis
from app.core.config import settings

# Single shared client — thread-safe, connection-pooled
redis_client = redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=5,
)


def get_redis() -> redis.Redis:
    """FastAPI dependency — returns the shared Redis client."""
    return redis_client


# ── Convenience helpers ───────────────────────────────────────────────────────

def cache_set(key: str, value: str, ttl_seconds: int = 300) -> None:
    redis_client.setex(key, ttl_seconds, value)


def cache_get(key: str) -> str | None:
    return redis_client.get(key)


def cache_delete(key: str) -> None:
    redis_client.delete(key)
