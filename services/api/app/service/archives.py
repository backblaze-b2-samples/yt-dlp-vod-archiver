"""Archive registry business logic over the running manifest.

CRUD for Archive entries, slug derivation, SSRF-guarded URL validation, the
dashboard stats/activity aggregations, and presigned asset URLs. All B2 access
goes through the repo layer; this module holds no boto3/yt-dlp imports.
"""

import ipaddress
import logging
import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from app.repo import delete_prefix, get_presigned_url, manifest
from app.service import pipeline
from app.types import (
    Archive,
    ArchiveConfig,
    ArchiveStats,
    DailyArchiveCount,
    RunStatus,
)
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

_ARCHIVE_PREFIX = "archive/"
_DANGEROUS_KEY_RE = re.compile(r"(\.\./|/\.\.|\\|%2e%2e|%00|\x00)")
_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")
_BLOCKED_HOSTS = {"localhost", "localhost.localdomain", "metadata.google.internal"}


class ArchiveNotFoundError(Exception):
    def __init__(self, detail: str = "Archive not found"):
        self.detail = detail
        super().__init__(detail)


class ArchiveValidationError(Exception):
    def __init__(self, detail: str = "Invalid archive"):
        self.detail = detail
        super().__init__(detail)


class ArchiveConflictError(Exception):
    def __init__(self, detail: str = "Archive run already in progress"):
        self.detail = detail
        super().__init__(detail)


def _slugify(value: str) -> str:
    slug = _SLUG_STRIP_RE.sub("-", value.lower()).strip("-")
    return slug[:60] or "archive"


def _unique_slug(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    n = 2
    while f"{base}-{n}" in existing:
        n += 1
    return f"{base}-{n}"


def _title_from_url(url: str) -> str:
    path = urlparse(url).path.rsplit("/", 1)[-1]
    name = re.sub(r"\.[a-z0-9]{1,5}$", "", path, flags=re.IGNORECASE)
    return name.replace("-", " ").replace("_", " ").strip() or "Untitled archive"


def validate_source_url(url: str) -> str:
    """Reject non-http(s) schemes and loopback/private/link-local hosts (SSRF)."""
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in ("http", "https"):
        raise ArchiveValidationError("URL must start with http:// or https://")
    host = parsed.hostname
    if not host:
        raise ArchiveValidationError("URL is missing a host")
    if host.lower() in _BLOCKED_HOSTS:
        raise ArchiveValidationError("Refusing to fetch from a loopback host")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    ):
        raise ArchiveValidationError("Refusing to fetch from a private address")
    return parsed.geturl()


def list_archives() -> list[Archive]:
    return manifest.list_archives()


def get_archive(archive_id: str) -> Archive:
    archive = manifest.get_archive(archive_id)
    if not archive:
        raise ArchiveNotFoundError()
    return archive


def create_archive(config: ArchiveConfig) -> Archive:
    url = validate_source_url(config.url)
    title = config.title.strip() or _title_from_url(url)
    existing_ids = {a.id for a in manifest.list_archives()}
    archive_id = _unique_slug(_slugify(title), existing_ids)
    archive = Archive(
        id=archive_id,
        title=title,
        url=url,
        clip_mode=config.clip_mode,
        clip_length_seconds=config.clip_length_seconds,
        max_clips=config.max_clips,
        status=RunStatus.idle,
        progress=0,
        current_step="idle",
        created_at=datetime.now(UTC),
    )
    return manifest.add_archive(archive)


def update_archive(archive_id: str, config: ArchiveConfig) -> Archive:
    existing = get_archive(archive_id)
    url = validate_source_url(config.url)
    updated = existing.model_copy(
        update={
            "title": config.title.strip() or existing.title,
            "url": url,
            "clip_mode": config.clip_mode,
            "clip_length_seconds": config.clip_length_seconds,
            "max_clips": config.max_clips,
        }
    )
    result = manifest.replace_archive(updated)
    if result is None:
        raise ArchiveNotFoundError()
    return result


def delete_archive(archive_id: str) -> None:
    get_archive(archive_id)  # 404 if missing
    # Prefix-scoped deletes only — never bucket-wide.
    for prefix in (
        f"archive/vods/{archive_id}/",
        f"archive/meta/{archive_id}/",
        f"archive/clips/{archive_id}/",
    ):
        delete_prefix(prefix)
    manifest.remove_archive(archive_id)


def run_archive(archive_id: str) -> Archive:
    get_archive(archive_id)  # 404 if missing
    if not pipeline.start_run(archive_id):
        raise ArchiveConflictError()
    return get_archive(archive_id)


def get_asset_url(key: str, download: bool = False) -> str:
    """Presigned URL for an archived asset. Scoped to the ``archive/`` prefix."""
    if not key or _DANGEROUS_KEY_RE.search(key.lower()):
        raise ArchiveValidationError("Invalid asset key")
    if not key.startswith(_ARCHIVE_PREFIX):
        raise ArchiveValidationError("Asset key must be under archive/")
    return get_presigned_url(key, inline=not download)


def get_stats() -> ArchiveStats:
    archives = manifest.list_archives()
    total_videos = sum(len(a.videos) for a in archives)
    total_clips = sum(len(v.clips) for a in archives for v in a.videos)
    total_size = sum(v.size_bytes for a in archives for v in a.videos)
    return ArchiveStats(
        total_archives=len(archives),
        total_videos=total_videos,
        total_clips=total_clips,
        total_size_bytes=total_size,
        total_size_human=humanize_bytes(total_size),
    )


def get_activity(days: int = 7) -> list[DailyArchiveCount]:
    archives = manifest.list_archives()
    today = datetime.now(UTC).date()
    cutoff = today - timedelta(days=days - 1)
    counts: dict[str, int] = defaultdict(int)
    for archive in archives:
        for video in archive.videos:
            d = video.archived_at.date()
            if d >= cutoff:
                counts[d.isoformat()] += 1
    return [
        DailyArchiveCount(
            date=(cutoff + timedelta(days=i)).isoformat(),
            videos=counts.get((cutoff + timedelta(days=i)).isoformat(), 0),
        )
        for i in range(days)
    ]
