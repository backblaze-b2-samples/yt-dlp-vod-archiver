"""yt-dlp adapter — the only place the ``yt_dlp`` library is imported.

Wraps probing and downloading a source URL. yt-dlp is pointed at the bundled
static ffmpeg (via ``ffmpeg_location``) so muxing/merging never depends on a
system ffmpeg. Everything here is CPU-only network + disk I/O; no GPU, no key.
"""

import logging
import os

import yt_dlp

from app.repo.ffmpeg_client import get_ffmpeg_exe

logger = logging.getLogger(__name__)


def _base_opts() -> dict:
    return {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "ffmpeg_location": get_ffmpeg_exe(),
        "logger": logger,
    }


def probe(url: str) -> dict:
    """Return yt-dlp's metadata dict for a URL without downloading.

    For a playlist/channel the dict carries an ``entries`` list. Raises
    RuntimeError if the URL can't be resolved.
    """
    opts = {**_base_opts(), "skip_download": True, "extract_flat": "in_playlist"}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.sanitize_info(ydl.extract_info(url, download=False))
    except yt_dlp.utils.DownloadError as e:
        raise RuntimeError(f"yt-dlp could not read '{url}': {e}") from e


def entry_urls(info: dict) -> list[str]:
    """Flatten a probed info dict into a list of individual video URLs.

    A single video returns ``[its own url]``; a playlist/channel returns each
    entry's URL. Entries missing a resolvable URL are skipped.
    """
    entries = info.get("entries")
    if not entries:
        return [info.get("webpage_url") or info.get("original_url") or ""]
    urls: list[str] = []
    for entry in entries:
        if not entry:
            continue
        url = entry.get("url") or entry.get("webpage_url")
        if url:
            urls.append(url)
    return urls


def download(url: str, dest_dir: str) -> tuple[str, dict]:
    """Download a single video into ``dest_dir``.

    Returns ``(local_file_path, info_dict)``. ``noplaylist=True`` guards against
    accidentally pulling an entire playlist when a member URL is passed. Raises
    RuntimeError on failure.
    """
    opts = {
        **_base_opts(),
        "noplaylist": True,
        "outtmpl": os.path.join(dest_dir, "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "format": "bestvideo*+bestaudio/best",
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)
            # merge_output_format rewrites the container to .mp4 when merging.
            if not os.path.exists(path):
                base, _ = os.path.splitext(path)
                mp4 = base + ".mp4"
                if os.path.exists(mp4):
                    path = mp4
            return path, ydl.sanitize_info(info)
    except yt_dlp.utils.DownloadError as e:
        raise RuntimeError(f"yt-dlp failed to download '{url}': {e}") from e


def summarize(info: dict) -> dict:
    """Pull the fields the pipeline needs from a yt-dlp info dict."""
    return {
        "video_id": info.get("id") or "video",
        "title": info.get("title") or "Untitled",
        "duration_seconds": float(info.get("duration") or 0.0),
        "thumbnail_url": info.get("thumbnail"),
        "chapters": info.get("chapters") or [],
    }
