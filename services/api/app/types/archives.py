"""Pydantic models for the VOD archive pipeline.

These are the only shapes that cross layer boundaries for archive features.
The running manifest in B2 (`archive/index.json`) serializes an
`ArchiveManifest` directly.
"""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

# Finite clip strategies. Kept as a Literal so both the API and the frontend
# selector share one closed set of values.
ClipMode = Literal["chapters", "interval", "none"]

# What the clip planner *actually* did, recorded per archived video so a
# "chapters" run that silently fell back to intervals (no chapter markers on the
# source) is legible in the UI instead of looking identical to interval mode.
ClipStrategy = Literal[
    "none", "interval", "chapters", "chapters_fallback_interval"
]


class RunStatus(StrEnum):
    """Lifecycle state of an archive's most recent run."""

    idle = "idle"
    running = "running"
    completed = "completed"
    failed = "failed"


class Clip(BaseModel):
    """A single highlight clip cut from a VOD and stored in B2."""

    key: str
    start: float
    end: float
    label: str


class ArchivedVideo(BaseModel):
    """One VOD that has been ingested to B2, plus its clips."""

    video_id: str
    title: str
    duration_seconds: float
    vod_key: str
    meta_key: str
    size_bytes: int
    thumbnail_url: str | None = None
    archived_at: datetime
    clips: list[Clip] = Field(default_factory=list)
    clip_strategy: ClipStrategy = "interval"


class ArchiveConfig(BaseModel):
    """User-editable configuration for an archive (create/edit payload)."""

    url: str
    title: str = ""
    clip_mode: ClipMode = "interval"
    clip_length_seconds: int = Field(default=5, ge=1, le=600)
    max_clips: int = Field(default=3, ge=1, le=50)


class Archive(BaseModel):
    """A registered source URL plus its clip config, run state, and videos.

    Persisted as an entry in the running manifest.
    """

    id: str
    title: str
    url: str
    clip_mode: ClipMode = "interval"
    clip_length_seconds: int = 5
    max_clips: int = 3
    status: RunStatus = RunStatus.idle
    progress: int = 0
    current_step: str = "idle"
    last_error: str | None = None
    created_at: datetime
    last_run_at: datetime | None = None
    videos: list[ArchivedVideo] = Field(default_factory=list)


class ArchiveManifest(BaseModel):
    """The running manifest stored at `archive/index.json`."""

    archives: list[Archive] = Field(default_factory=list)
    updated_at: datetime | None = None


class ArchiveStats(BaseModel):
    """Aggregate metrics for the dashboard."""

    total_archives: int
    total_videos: int
    total_clips: int
    total_size_bytes: int
    total_size_human: str


class DailyArchiveCount(BaseModel):
    """Count of videos archived on a single day (dashboard activity chart)."""

    date: str
    videos: int
