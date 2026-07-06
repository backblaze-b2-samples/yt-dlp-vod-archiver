"""Read / modify / write the running archive manifest (`archive/index.json`).

A module-level lock serializes read-modify-write so concurrent requests (or the
background run thread updating progress) can't clobber each other's writes
in-process. The manifest itself lives in B2 and is the sole source of truth for
registered archives and their state.
"""

import logging
from datetime import UTC, datetime
from threading import Lock

from app.repo.b2_client import get_json, upload_json
from app.types import Archive, ArchiveManifest

logger = logging.getLogger(__name__)

MANIFEST_KEY = "archive/index.json"

_lock = Lock()


def load() -> ArchiveManifest:
    """Load the manifest from B2, returning an empty one if it doesn't exist."""
    raw = get_json(MANIFEST_KEY)
    if not raw:
        return ArchiveManifest()
    return ArchiveManifest.model_validate(raw)


def _save(manifest: ArchiveManifest) -> None:
    manifest.updated_at = datetime.now(UTC)
    upload_json(MANIFEST_KEY, manifest.model_dump(mode="json"))


def list_archives() -> list[Archive]:
    return load().archives


def get_archive(archive_id: str) -> Archive | None:
    for archive in load().archives:
        if archive.id == archive_id:
            return archive
    return None


def add_archive(archive: Archive) -> Archive:
    with _lock:
        manifest = load()
        if any(a.id == archive.id for a in manifest.archives):
            raise ValueError(f"Archive '{archive.id}' already exists")
        manifest.archives.append(archive)
        _save(manifest)
    return archive


def replace_archive(archive: Archive) -> Archive | None:
    """Replace an existing archive by id. Returns None if not found."""
    with _lock:
        manifest = load()
        for i, existing in enumerate(manifest.archives):
            if existing.id == archive.id:
                manifest.archives[i] = archive
                _save(manifest)
                return archive
    return None


def update_archive(archive_id: str, **fields) -> Archive | None:
    """Patch fields on a single archive under the lock. Returns the updated one."""
    with _lock:
        manifest = load()
        for i, existing in enumerate(manifest.archives):
            if existing.id == archive_id:
                updated = existing.model_copy(update=fields)
                manifest.archives[i] = updated
                _save(manifest)
                return updated
    logger.warning("update_archive: id not found: %s", archive_id)
    return None


def remove_archive(archive_id: str) -> Archive | None:
    """Remove an archive entry. Returns the removed archive, or None."""
    with _lock:
        manifest = load()
        for i, existing in enumerate(manifest.archives):
            if existing.id == archive_id:
                removed = manifest.archives.pop(i)
                _save(manifest)
                return removed
    return None
