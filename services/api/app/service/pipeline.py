"""Archive run orchestration: probe -> ingest -> metadata -> clip -> index.

Runs in a daemon thread because yt-dlp downloads block. The manifest entry's
``status`` / ``progress`` / ``current_step`` are updated at each stage so a page
reload (the UI polls while running) reflects live state. A module-level set of
running ids plus a lock prevents double-runs.
"""

import logging
import os
import re
import tempfile
from datetime import UTC, datetime
from threading import Lock, Thread

from app.repo import ffmpeg_client, manifest, upload_json, upload_path, ytdlp_client
from app.service.clipping import build_clip_plan
from app.types import Archive, ArchivedVideo, Clip, RunStatus

logger = logging.getLogger(__name__)

# Cap videos processed per run so a channel/playlist source stays bounded.
MAX_VIDEOS_PER_RUN = 3

_running: set[str] = set()
_running_lock = Lock()

_UNSAFE_ID_RE = re.compile(r"[^A-Za-z0-9_-]")


def _safe_id(value: str) -> str:
    cleaned = _UNSAFE_ID_RE.sub("_", (value or "video").strip())
    return cleaned[:100] or "video"


def is_running(archive_id: str) -> bool:
    with _running_lock:
        return archive_id in _running


def start_run(archive_id: str) -> bool:
    """Mark an archive running and spawn its background thread.

    Returns False if a run is already in progress for this id.
    """
    with _running_lock:
        if archive_id in _running:
            return False
        _running.add(archive_id)
    # Reflect running state synchronously so the immediate poll sees it.
    manifest.update_archive(
        archive_id,
        status=RunStatus.running,
        progress=1,
        current_step="queued",
        last_error=None,
    )
    Thread(target=_run_safe, args=(archive_id,), daemon=True).start()
    return True


def _run_safe(archive_id: str) -> None:
    try:
        _run(archive_id)
    except Exception as e:
        logger.exception("Archive run failed: %s", archive_id)
        manifest.update_archive(
            archive_id,
            status=RunStatus.failed,
            current_step="failed",
            last_error=str(e)[:500],
        )
    finally:
        with _running_lock:
            _running.discard(archive_id)


def _make_clips(
    archive: Archive, workdir: str, src_path: str, vid: str, summary: dict
) -> list[Clip]:
    plan = build_clip_plan(
        summary["duration_seconds"],
        archive.clip_mode,
        archive.clip_length_seconds,
        archive.max_clips,
        summary["chapters"],
    )
    clips: list[Clip] = []
    for i, (start, end, label) in enumerate(plan, start=1):
        clip_name = f"clip_{i:02d}.mp4"
        local_clip = os.path.join(workdir, f"{vid}_{clip_name}")
        try:
            ffmpeg_client.cut_clip(src_path, start, end, local_clip)
        except RuntimeError:
            logger.warning("Skipping clip %d (%s-%s) for %s", i, start, end, vid)
            continue
        clip_key = f"archive/clips/{archive.id}/{vid}/{clip_name}"
        upload_path(local_clip, clip_key, "video/mp4")
        clips.append(Clip(key=clip_key, start=start, end=end, label=label))
    return clips


def _run(archive_id: str) -> None:
    archive = manifest.get_archive(archive_id)
    if not archive:
        logger.warning("Run requested for unknown archive: %s", archive_id)
        return

    manifest.update_archive(
        archive_id, progress=5, current_step="probing source", videos=[]
    )
    info = ytdlp_client.probe(archive.url)
    urls = [u for u in ytdlp_client.entry_urls(info) if u][:MAX_VIDEOS_PER_RUN]
    if not urls:
        raise RuntimeError("No downloadable video found at the source URL")

    videos: list[ArchivedVideo] = []
    with tempfile.TemporaryDirectory(prefix="vod-archive-") as workdir:
        for idx, url in enumerate(urls):
            label = f"{idx + 1}/{len(urls)}"
            manifest.update_archive(
                archive_id,
                progress=10 + int(80 * idx / len(urls)),
                current_step=f"downloading {label}",
            )
            local_path, vinfo = ytdlp_client.download(url, workdir)
            summary = ytdlp_client.summarize(vinfo)
            # Direct-media URLs come back without a duration; probe the file so
            # the clip planner has a real length to work with.
            if summary["duration_seconds"] <= 0:
                summary["duration_seconds"] = ffmpeg_client.probe_duration(local_path)
            vid = _safe_id(summary["video_id"])

            vod_key = f"archive/vods/{archive_id}/{vid}.mp4"
            size = upload_path(local_path, vod_key, "video/mp4")
            meta_key = f"archive/meta/{archive_id}/{vid}.json"
            upload_json(meta_key, vinfo)

            manifest.update_archive(
                archive_id, current_step=f"cutting clips {label}"
            )
            clips = _make_clips(archive, workdir, local_path, vid, summary)

            videos.append(
                ArchivedVideo(
                    video_id=vid,
                    title=summary["title"],
                    duration_seconds=summary["duration_seconds"],
                    vod_key=vod_key,
                    meta_key=meta_key,
                    size_bytes=size,
                    thumbnail_url=summary["thumbnail_url"],
                    archived_at=datetime.now(UTC),
                    clips=clips,
                )
            )
            # Persist incrementally so a mid-run reload shows partial results.
            manifest.update_archive(archive_id, videos=list(videos))

    manifest.update_archive(
        archive_id,
        status=RunStatus.completed,
        progress=100,
        current_step="done",
        last_run_at=datetime.now(UTC),
        videos=videos,
    )
