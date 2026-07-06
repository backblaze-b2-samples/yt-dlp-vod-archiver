"""Deterministic, local, keyless highlight-clip planning.

Given a VOD's duration and the archive's clip config, produce a list of
``(start, end, label)`` cut instructions. No transcript/chat API, no ML — just
chapter markers or evenly-spaced intervals.
"""

import logging

from app.types import ClipMode, ClipStrategy

logger = logging.getLogger(__name__)

ClipPlan = list[tuple[float, float, str]]


def _interval_plan(
    duration: float, clip_length_seconds: int, max_clips: int
) -> ClipPlan:
    """Evenly-spaced clips of ``clip_length_seconds``, up to ``max_clips``.

    Works on any video, including chapterless ones — the safe default.
    """
    if duration <= clip_length_seconds:
        return [(0.0, round(duration, 3), "Segment 1")]
    step = duration / max_clips
    plan: ClipPlan = []
    for i in range(max_clips):
        start = i * step
        end = min(start + clip_length_seconds, duration)
        if end - start < 0.5:
            continue
        plan.append((round(start, 3), round(end, 3), f"Segment {i + 1}"))
    return plan


def _chapter_plan(chapters: list[dict], max_clips: int, duration: float) -> ClipPlan:
    """One clip per usable chapter marker, capped at ``max_clips``."""
    plan: ClipPlan = []
    for i, chapter in enumerate(chapters[:max_clips]):
        start = float(chapter.get("start_time") or 0.0)
        end = float(chapter.get("end_time") or 0.0)
        if end <= start:
            continue
        label = chapter.get("title") or f"Chapter {i + 1}"
        plan.append((round(start, 3), round(min(end, duration), 3), label))
    return plan


def build_clip_plan(
    duration: float,
    clip_mode: ClipMode,
    clip_length_seconds: int,
    max_clips: int,
    chapters: list[dict],
) -> tuple[ClipPlan, ClipStrategy]:
    """Return the clip cut plan *and the strategy actually used* for a VOD.

    - ``none``: no clips.
    - ``chapters``: one clip per chapter marker (up to ``max_clips``); when the
      source has no usable chapter markers this falls back to interval mode and
      reports ``chapters_fallback_interval`` so the UI can say so.
    - ``interval``: evenly-spaced fixed-length clips.
    """
    if clip_mode == "none" or duration <= 0:
        return [], "none"

    if clip_mode == "chapters":
        plan = _chapter_plan(chapters, max_clips, duration)
        if plan:
            return plan, "chapters"
        logger.info("chapters mode requested but no usable markers; using interval")
        return (
            _interval_plan(duration, clip_length_seconds, max_clips),
            "chapters_fallback_interval",
        )

    return _interval_plan(duration, clip_length_seconds, max_clips), "interval"
