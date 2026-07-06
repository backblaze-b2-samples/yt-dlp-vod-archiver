import functools
import io
import json
import mimetypes
import os
from datetime import UTC, datetime
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import settings
from app.types import FileMetadata
from app.types.formatting import humanize_bytes


def _guess_content_type(key: str) -> str:
    mime, _ = mimetypes.guess_type(key)
    return mime or "application/octet-stream"


def _split_key(key: str) -> tuple[str, str]:
    """Return (folder, filename) from an object key."""
    parts = key.rsplit("/", 1)
    if len(parts) == 2:
        return parts[0] + "/", parts[1]
    return "", parts[0]


def _public_url(key: str) -> str | None:
    """Build a public URL for an object key, percent-encoding the path."""
    if not settings.b2_public_url_base:
        return None
    return f"{settings.b2_public_url_base}/{quote(key, safe='/')}"


@functools.lru_cache(maxsize=1)
def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.b2_endpoint,
        region_name=settings.b2_region,
        aws_access_key_id=settings.b2_application_key_id,
        aws_secret_access_key=settings.b2_application_key,
        config=Config(
            signature_version="s3v4",
            user_agent_extra="b2ai-yt-dlp-vod-archiver",
        ),
    )


def check_connectivity() -> bool:
    try:
        client = get_s3_client()
        client.head_bucket(Bucket=settings.b2_bucket_name)
        return True
    except Exception:
        return False


def upload_file(
    file_data: bytes, key: str, content_type: str
) -> FileMetadata:
    """Upload file to B2. Raises RuntimeError on S3 failure."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=io.BytesIO(file_data),
            ContentType=content_type,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 upload failed for '{key}': {e}") from e
    folder, filename = _split_key(key)
    size = len(file_data)
    return FileMetadata(
        key=key,
        filename=filename,
        folder=folder,
        size_bytes=size,
        size_human=humanize_bytes(size),
        content_type=content_type,
        uploaded_at=datetime.now(UTC),
        url=_public_url(key),
    )


def list_files(prefix: str = "", max_keys: int = 1000) -> list[FileMetadata]:
    """List files from B2. Raises RuntimeError on S3 failure."""
    client = get_s3_client()
    try:
        response = client.list_objects_v2(
            Bucket=settings.b2_bucket_name,
            Prefix=prefix,
            MaxKeys=max_keys,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 list failed: {e}") from e
    files: list[FileMetadata] = []
    for obj in response.get("Contents", []):
        folder, filename = _split_key(obj["Key"])
        files.append(
            FileMetadata(
                key=obj["Key"],
                filename=filename,
                folder=folder,
                size_bytes=obj["Size"],
                size_human=humanize_bytes(obj["Size"]),
                content_type=_guess_content_type(obj["Key"]),
                uploaded_at=obj["LastModified"],
                url=_public_url(obj["Key"]),
            )
        )
    files.sort(key=lambda f: f.uploaded_at, reverse=True)
    return files


def get_file_metadata(key: str) -> FileMetadata | None:
    client = get_s3_client()
    try:
        response = client.head_object(
            Bucket=settings.b2_bucket_name, Key=key
        )
    except ClientError as e:
        # Only treat 404/NoSuchKey as "not found"; re-raise other errors
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise

    folder, filename = _split_key(key)
    return FileMetadata(
        key=key,
        filename=filename,
        folder=folder,
        size_bytes=response["ContentLength"],
        size_human=humanize_bytes(response["ContentLength"]),
        content_type=response.get("ContentType", _guess_content_type(key)),
        uploaded_at=response["LastModified"],
        url=_public_url(key),
    )


def delete_file(key: str) -> None:
    """Delete an object from B2. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        client.delete_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        raise RuntimeError(f"B2 delete failed for '{key}': {e}") from e


def get_presigned_url(
    key: str,
    filename: str | None = None,
    expires_in: int = 600,
    inline: bool = False,
) -> str:
    """Generate a presigned GET URL. Raises RuntimeError on failure.

    When ``inline`` is True the URL renders in-browser (used for the inline
    ``<video>`` clip player); otherwise it forces a download attachment.
    """
    client = get_s3_client()
    params: dict = {"Bucket": settings.b2_bucket_name, "Key": key}
    if inline:
        params["ResponseContentDisposition"] = "inline"
    elif filename:
        # RFC 5987 encoding for non-ASCII filenames
        encoded = quote(filename, safe="")
        params["ResponseContentDisposition"] = (
            f"attachment; filename=\"{encoded}\"; filename*=UTF-8''{encoded}"
        )
    else:
        params["ResponseContentDisposition"] = "attachment"
    try:
        return client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e


def get_upload_stats() -> dict:
    """Paginate through all objects and return aggregate stats.

    Raises RuntimeError on S3 failure.
    """
    client = get_s3_client()
    contents: list[dict] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "MaxKeys": 1000}
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            contents.extend(response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 stats query failed: {e}") from e

    total_size = sum(obj["Size"] for obj in contents)
    today = datetime.now(UTC).date()
    uploads_today = sum(
        1 for obj in contents if obj["LastModified"].date() == today
    )
    return {
        "total_files": len(contents),
        "total_size_bytes": total_size,
        "total_size_human": humanize_bytes(total_size),
        "uploads_today": uploads_today,
    }


def upload_path(
    local_path: str, key: str, content_type: str | None = None
) -> int:
    """Upload a local file to B2 using boto3's managed multipart transfer.

    `client.upload_file` streams the file from disk in parts, so multi-GB VODs
    never buffer fully in memory. Returns the uploaded size in bytes.
    Raises RuntimeError on S3 failure.
    """
    client = get_s3_client()
    ctype = content_type or _guess_content_type(key)
    try:
        client.upload_file(
            local_path,
            settings.b2_bucket_name,
            key,
            ExtraArgs={"ContentType": ctype},
        )
    except (ClientError, OSError) as e:
        raise RuntimeError(f"B2 upload failed for '{key}': {e}") from e
    return os.path.getsize(local_path)


def upload_json(key: str, obj: dict) -> None:
    """Serialize `obj` to JSON and store it at `key`. Raises on S3 failure."""
    client = get_s3_client()
    body = json.dumps(obj, default=str).encode("utf-8")
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=io.BytesIO(body),
            ContentType="application/json",
        )
    except ClientError as e:
        raise RuntimeError(f"B2 JSON write failed for '{key}': {e}") from e


def get_json(key: str) -> dict | None:
    """Read and parse a JSON object from B2. Returns None if it doesn't exist."""
    client = get_s3_client()
    try:
        response = client.get_object(
            Bucket=settings.b2_bucket_name, Key=key
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise
    return json.loads(response["Body"].read())


def delete_prefix(prefix: str) -> int:
    """Delete every object under a prefix, batched. Returns the count deleted.

    Callers pass a specific archive-scoped prefix (e.g. ``archive/vods/<id>/``);
    this never performs an unscoped, bucket-wide delete. Raises on S3 failure.
    """
    if not prefix:
        raise ValueError("delete_prefix requires a non-empty prefix")
    client = get_s3_client()
    deleted = 0
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix}
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            objects = [{"Key": o["Key"]} for o in response.get("Contents", [])]
            for i in range(0, len(objects), 1000):
                batch = objects[i : i + 1000]
                if batch:
                    client.delete_objects(
                        Bucket=settings.b2_bucket_name,
                        Delete={"Objects": batch},
                    )
                    deleted += len(batch)
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 prefix delete failed for '{prefix}': {e}") from e
    return deleted
