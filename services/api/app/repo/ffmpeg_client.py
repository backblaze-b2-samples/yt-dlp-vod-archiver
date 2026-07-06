"""ffmpeg adapter for cutting highlight clips.

The ffmpeg binary is the static one bundled by ``imageio-ffmpeg`` — this avoids
depending on a system ffmpeg install (and sidesteps slim Homebrew builds that
ship without optional filters). Clips are cut with stream copy (``-c copy``),
so no re-encoding, no libass/drawtext, and near-instant, CPU-only work.
"""

import logging
import re
import subprocess

import imageio_ffmpeg

logger = logging.getLogger(__name__)

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def get_ffmpeg_exe() -> str:
    """Absolute path to the bundled static ffmpeg binary."""
    return imageio_ffmpeg.get_ffmpeg_exe()


def probe_duration(path: str) -> float:
    """Return a media file's duration in seconds by parsing ffmpeg's output.

    yt-dlp's generic extractor doesn't report a duration for direct media URLs,
    so the pipeline falls back to this. Returns 0.0 if it can't be determined.
    (`ffmpeg -i` with no output exits non-zero but still prints Duration.)
    """
    result = subprocess.run(
        [get_ffmpeg_exe(), "-i", path], capture_output=True
    )
    stderr = result.stderr.decode("utf-8", "replace")
    match = _DURATION_RE.search(stderr)
    if not match:
        return 0.0
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def cut_clip(src_path: str, start_s: float, end_s: float, dest_path: str) -> None:
    """Cut [start_s, end_s) from ``src_path`` into ``dest_path`` via stream copy.

    Uses input seeking (`-ss` before `-i`) for speed and `-t` for duration, plus
    `+faststart` so the resulting MP4 plays inline in a browser `<video>`.
    Raises RuntimeError if ffmpeg fails.
    """
    duration = max(0.1, float(end_s) - float(start_s))
    cmd = [
        get_ffmpeg_exe(),
        "-y",
        "-ss",
        f"{float(start_s):.3f}",
        "-i",
        src_path,
        "-t",
        f"{duration:.3f}",
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        dest_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", "replace") if e.stderr else ""
        logger.warning("ffmpeg cut_clip failed: %s", stderr[-500:])
        raise RuntimeError(f"ffmpeg failed to cut clip: {stderr[-200:]}") from e
