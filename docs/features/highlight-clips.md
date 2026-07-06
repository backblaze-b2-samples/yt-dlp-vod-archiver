<!-- last_verified: 2026-07-06 -->
# Feature: Highlight Clips

## Purpose
Cut short highlight clips from an archived VOD with ffmpeg (stream copy, no re-encode)
and store them in B2 for inline playback.

## Used By
- Job: the background run thread (`service/pipeline.py::_make_clips`)
- UI: inline `<video>` players on `/archives/[id]` (`ClipCard`)

## Core Functions
- `service/clipping.py` — `build_clip_plan(duration, clip_mode, clip_length_seconds, max_clips, chapters)` → `(plan, strategy)`; `strategy` records what actually ran (`chapters`, `interval`, `chapters_fallback_interval`, or `none`)
- `repo/ffmpeg_client.py` — `cut_clip(src, start, end, dest)` (`-ss/-t -c copy +faststart`), `probe_duration(path)`
- `service/pipeline.py` — `_make_clips` (cut + upload each clip; stores `clip_strategy` on the `ArchivedVideo`)

## Canonical Files
- Clip planning: `services/api/app/service/clipping.py`
- ffmpeg adapter: `services/api/app/repo/ffmpeg_client.py`

## Inputs
- VOD duration, `clip_mode`, `clip_length_seconds`, `max_clips`, and chapter markers (if any)

## Outputs
- `archive/clips/<id>/<vid>/clip_NN.mp4` — one MP4 per clip
- Manifest `Clip` entries (key, start, end, label)
- `ArchivedVideo.clip_strategy` — the strategy actually used, so a `chapters` run that fell back to intervals is legible in the UI instead of looking identical to interval mode

## Flow
- `none` → no clips (`strategy = none`)
- `chapters` → one clip per chapter marker (up to `max_clips`, `strategy = chapters`); when the
  video has no usable chapter markers it falls back to interval mode and records
  `strategy = chapters_fallback_interval`
- `interval` → evenly-spaced clips of `clip_length_seconds` (up to `max_clips`, `strategy = interval`); works on any video
- Each planned clip is cut with the bundled ffmpeg (stream copy → fast, CPU-only, no libass/drawtext)
  and uploaded to B2; a clip that fails to cut is skipped, not fatal

## Edge Cases
- Duration ≤ clip length → a single clip covering the whole video
- Chapterless video in `chapters` mode → interval fallback
- A single clip failing → logged and skipped; the run continues

## UX States (if applicable)
- Clips render inline via presigned URLs; a per-clip download button is provided
- No clips cut → "No clips were cut for this video."
- Chapters requested but the source had no chapter markers → an inline note on the video row explains the fallback to interval clips (`clip_strategy === "chapters_fallback_interval"`)

## Verification
- Test files: `services/api/tests/test_archives.py` (`test_run_pipeline_hermetic`, `test_clip_plan_records_strategy`)
- Required cases: interval plan produces the expected number of clips; the planner reports the strategy actually used (interval / chapters / chapters_fallback_interval / none)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure && pnpm build`
- Pass criteria: hermetic run yields the expected clip count; real clips play in `<video>`

## Notes / Future Work
- Transcript- or chat-keyword-driven clip modes would require a second external API key and
  are intentionally out of scope ("B2 credentials only").

## Related Docs
- [Archive Jobs](archive-jobs.md)
- [VOD Ingest to B2](vod-ingest.md)
