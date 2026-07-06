<!-- last_verified: 2026-07-06 -->
# Feature: VOD Ingest to B2

## Purpose
Download a source VOD with yt-dlp and stream it into Backblaze B2 without buffering
multi-GB files in memory.

## Used By
- Job: the background run thread (`service/pipeline.py`)
- API: triggered by `POST /archives/{id}/run`

## Core Functions
- `repo/ytdlp_client.py` — `probe(url)`, `entry_urls(info)`, `download(url, dest_dir)`, `summarize(info)`
- `repo/b2_client.py` — `upload_path(local_path, key, content_type)` (boto3 managed multipart),
  `upload_json(key, obj)` (per-video metadata)
- `service/pipeline.py` — orchestration (`_run`)

## Canonical Files
- yt-dlp adapter: `services/api/app/repo/ytdlp_client.py`
- Managed-multipart upload: `services/api/app/repo/b2_client.py::upload_path`

## Inputs
- Source URL (from the Archive), resolved to one or more per-video URLs (playlist/channel supported, capped)

## Outputs
- `archive/vods/<id>/<vid>.mp4` — the full VOD (managed multipart)
- `archive/meta/<id>/<vid>.json` — yt-dlp's sanitized metadata dict
- Manifest `ArchivedVideo` entry (video_id, title, duration, vod_key, meta_key, size, thumbnail)

## Flow
- Probe the URL (yt-dlp) → resolve entry URLs (single or playlist, up to `MAX_VIDEOS_PER_RUN`)
- Download each video into a temp dir; yt-dlp uses the bundled ffmpeg for muxing
- If yt-dlp reports no duration (direct-media URLs), probe the file with ffmpeg
- Upload the VOD via `client.upload_file` (managed multipart) and write metadata JSON
- Update the manifest with progress and the new video entry
- Progress is stage-weighted so the determinate bar advances instead of freezing:
  0-10% probing, then each video owns an equal slice of the 10-90% band with the
  bar stepping through download → upload → clipping (`_work_progress`), and 100%
  on completion

## Edge Cases
- URL yields no downloadable video → run fails with a clear error
- Large VOD → streamed from disk in parts, never fully buffered in memory
- Download/network error → run marked `failed`, `last_error` set; temp dir cleaned up

## UX States (if applicable)
- Progress + a per-stage step label ("downloading N/M" → "uploading N/M" → "cutting clips N/M") surfaced on the archive while running; the determinate bar advances with each stage rather than sitting at a fixed value

## Verification
- Test files: `services/api/tests/test_archives.py` (`test_run_pipeline_hermetic`, signature guard)
- Required cases: hermetic run (mocked yt-dlp/ffmpeg/B2) producing a video entry + VOD key
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure && pnpm build`
- Pass criteria: hermetic run yields `status=completed` with a `vod_key` under `archive/vods/<id>/`

## Related Docs
- [Archive Jobs](archive-jobs.md)
- [Highlight Clips](highlight-clips.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
