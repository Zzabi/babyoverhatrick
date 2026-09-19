"""
Object storage abstraction.

storage_provider = "s3"        → boto3 S3-compatible client (MinIO, Cloudflare R2,
                                  Backblaze B2, AWS S3 — same code, different env vars).
storage_provider = "cloudinary" → Cloudinary SDK (free tier, no S3 keys needed).

The public interface is identical for both providers:
  upload_bytes(key, data, content_type) → public URL (str)
  public_url(key)                       → public URL (str)
  ensure_bucket_exists()                → None

All callers use only those three functions — switching providers requires only
env var changes, no code changes outside this module.
"""
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from app.core.config import settings


# ── S3-compatible (default) ───────────────────────────────────────────────────

def _s3_client():
    """Returns a boto3 S3-compatible client."""
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint,
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
        region_name=settings.storage_region,
        config=Config(signature_version="s3v4"),
    )


def _s3_upload(object_key: str, data: bytes, content_type: str) -> str:
    """Upload bytes to an S3-compatible bucket. Returns the public URL."""
    _s3_client().put_object(
        Bucket=settings.storage_bucket,
        Key=object_key,
        Body=data,
        ContentType=content_type,
    )
    return f"{settings.storage_public_url}/{object_key}"


def _s3_ensure_bucket() -> None:
    """Creates the S3 bucket if it doesn't already exist (MinIO local dev only)."""
    client = _s3_client()
    try:
        client.head_bucket(Bucket=settings.storage_bucket)
    except ClientError:
        client.create_bucket(Bucket=settings.storage_bucket)


# ── Cloudinary ────────────────────────────────────────────────────────────────

def _cloudinary_upload(object_key: str, data: bytes, content_type: str) -> str:
    """
    Upload bytes to Cloudinary. Returns the secure CDN URL.

    object_key (e.g. 'questions/abc123.jpg') is used as the Cloudinary public_id
    so UUID-based naming is preserved and answer inference from URLs is prevented.
    """
    import cloudinary
    import cloudinary.uploader

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )

    # Strip extension — Cloudinary appends its own
    public_id = object_key.rsplit(".", 1)[0]  # 'questions/abc123'
    fmt = content_type.split("/")[-1]          # 'jpeg' or 'png'

    result = cloudinary.uploader.upload(
        data,
        public_id=public_id,
        resource_type="image",
        format=fmt,
        overwrite=False,
    )
    return result["secure_url"]


# ── Public interface (provider-agnostic) ──────────────────────────────────────

def upload_bytes(object_key: str, data: bytes, content_type: str = "image/jpeg") -> str:
    """Upload bytes to the configured storage provider. Returns the public URL."""
    if settings.storage_provider == "cloudinary":
        return _cloudinary_upload(object_key, data, content_type)
    return _s3_upload(object_key, data, content_type)


def public_url(object_key: str) -> str:
    """
    Returns the publicly accessible URL for a stored object.

    For S3-compatible storage: constructs URL from base + key.
    For Cloudinary: the object_key IS already the full URL (returned by upload_bytes
    and stored as-is in the database), so return it unchanged.
    """
    if settings.storage_provider == "cloudinary":
        return object_key  # already a full URL from upload time
    return f"{settings.storage_public_url}/{object_key}"


def ensure_bucket_exists() -> None:
    """Creates local MinIO bucket if needed. No-op for Cloudinary and managed S3."""
    if settings.storage_provider == "cloudinary":
        return
    _s3_ensure_bucket()
