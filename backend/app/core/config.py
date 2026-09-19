from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    environment: str = "development"
    secret_key: str = "dev-secret-key-change-in-production"
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql://gameplatform:localpassword@localhost:5432/gameplatform_dev"
    database_url_direct: str = ""

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://:localpassword@localhost:6379"

    # ── Object storage ────────────────────────────────────────────────────────
    # storage_provider: "s3" (default — works with MinIO, R2, B2, AWS S3, etc.)
    #                   "cloudinary" (set cloudinary_* vars below)
    storage_provider: str = "s3"

    # S3-compatible settings (used when storage_provider = "s3")
    storage_endpoint: str = "http://localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket: str = "gameplatform-assets"
    storage_public_url: str = "http://localhost:9000/gameplatform-assets"
    storage_region: str = "us-east-1"

    # Cloudinary settings (used when storage_provider = "cloudinary")
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # ── Auth — Clerk ──────────────────────────────────────────────────────────
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""

    # ── Dev auth bypass (local only — NEVER set true in production) ────────────
    dev_bypass_auth: bool = False
    dev_user_id: str = "dev-user-001"
    dev_user_email: str = "dev@local.dev"
    dev_user_role: str = "admin"

    # ── Admin content management (separate from Clerk auth) ───────────────────
    # Used for the content admin API and SQLAdmin panel
    admin_username: str = "admin"
    admin_password: str = "changeme"

    # ── Game settings ─────────────────────────────────────────────────────────
    questions_per_session: int = 10    # random questions picked per session
    max_answer_attempts: int = 1       # attempts allowed per question (1 = one-shot, no retries)
    fuzzy_match_threshold: float = 0.75

    # ── Error tracking ────────────────────────────────────────────────────────
    sentry_dsn: str = ""


settings = Settings()
