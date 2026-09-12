import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from app.core.config import settings


def get_s3_client():
    """Returns an S3-compatible client. Works with both MinIO and Cloudflare R2."""
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint,
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
        region_name=settings.storage_region,
        config=Config(signature_version="s3v4"),
    )


def public_url(object_key: str) -> str:
    """Returns the publicly accessible CDN/storage URL for an object key."""
    return f"{settings.storage_public_url}/{object_key}"


def upload_bytes(object_key: str, data: bytes, content_type: str = "image/png") -> str:
    """Upload bytes to object storage. Returns the public URL."""
    client = get_s3_client()
    client.put_object(
        Bucket=settings.storage_bucket,
        Key=object_key,
        Body=data,
        ContentType=content_type,
    )
    return public_url(object_key)


def ensure_bucket_exists() -> None:
    """Creates the storage bucket if it doesn't exist. Called on startup."""
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.storage_bucket)
    except ClientError:
        client.create_bucket(Bucket=settings.storage_bucket)
