"""Deterministic, local, keyless highlight-clip planning.

Given a VOD's duration and the archive's clip config, produce a list of
``(start, end, label)`` cut instructions. No transcript/chat API, no ML — just
chapter markers or evenly-spaced intervals.
"""

import logging

from app.types import ClipMode

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


def build_clip_plan(
    duration: float,
    clip_mode: ClipMode,
    clip_length_seconds: int,
    max_clips: int,
    chapters: list[dict],
) -> ClipPlan:
    """Return the clip cut plan for a VOD.

    - ``none``: no clips.
    - ``chapters``: one clip per chapter marker (up to ``max_clips``); falls
      back to interval mode when the video has no usable chapter markers.
    - ``interval``: evenly-spaced fixed-length clips.
    """
    if clip_mode == "none" or duration <= 0:
        return []

    if clip_mode == "chapters" and chapters:
        plan: ClipPlan = []
        for i, chapter in enumerate(chapters[:max_clips]):
            start = float(chapter.get("start_time") or 0.0)
            end = float(chapter.get("end_time") or 0.0)
            if end <= start:
                continue
            label = chapter.get("title") or f"Chapter {i + 1}"
            plan.append((round(start, 3), round(min(end, duration), 3), label))
        if plan:
            return plan
        logger.info("chapters mode requested but no usable markers; using interval")

    return _interval_plan(duration, clip_length_seconds, max_clips)
