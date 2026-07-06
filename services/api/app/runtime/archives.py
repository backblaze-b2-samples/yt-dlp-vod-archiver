"""FastAPI routes for the archive pipeline. Thin handlers — no business logic."""

import logging

from fastapi import APIRouter, HTTPException

from app.service.archives import (
    ArchiveConflictError,
    ArchiveNotFoundError,
    ArchiveValidationError,
    create_archive,
    delete_archive,
    get_activity,
    get_archive,
    get_asset_url,
    get_stats,
    list_archives,
    run_archive,
    update_archive,
)
from app.types import Archive, ArchiveConfig, ArchiveStats, DailyArchiveCount

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/archives", response_model=list[Archive])
async def list_archives_endpoint():
    return list_archives()


@router.post("/archives", response_model=Archive, status_code=201)
async def create_archive_endpoint(config: ArchiveConfig):
    try:
        archive = create_archive(config)
    except ArchiveValidationError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    logger.info("Archive created: id=%s url=%s", archive.id, archive.url)
    return archive


# Literal sub-paths declared BEFORE /archives/{archive_id} so they win the match.
@router.get("/archives/stats", response_model=ArchiveStats)
async def archive_stats_endpoint():
    return get_stats()


@router.get("/archives/stats/activity", response_model=list[DailyArchiveCount])
async def archive_activity_endpoint(days: int = 7):
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 90")
    return get_activity(days=days)


@router.get("/archives/asset")
async def archive_asset_endpoint(key: str, download: bool = False):
    try:
        url = get_asset_url(key, download=download)
    except ArchiveValidationError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to sign asset URL") from None
    return {"url": url}


@router.get("/archives/{archive_id}", response_model=Archive)
async def get_archive_endpoint(archive_id: str):
    try:
        return get_archive(archive_id)
    except ArchiveNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.put("/archives/{archive_id}", response_model=Archive)
async def update_archive_endpoint(archive_id: str, config: ArchiveConfig):
    try:
        return update_archive(archive_id, config)
    except ArchiveNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except ArchiveValidationError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None


@router.delete("/archives/{archive_id}")
async def delete_archive_endpoint(archive_id: str):
    try:
        delete_archive(archive_id)
    except ArchiveNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to delete archive") from None
    logger.info("Archive deleted: id=%s", archive_id)
    return {"deleted": True, "id": archive_id}


@router.post("/archives/{archive_id}/run", status_code=202)
async def run_archive_endpoint(archive_id: str):
    try:
        archive = run_archive(archive_id)
    except ArchiveNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except ArchiveConflictError as e:
        raise HTTPException(status_code=409, detail=e.detail) from None
    logger.info("Archive run started: id=%s", archive_id)
    return {"id": archive.id, "status": archive.status}
