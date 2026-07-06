<!-- last_verified: 2026-07-06 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with archive metrics (archives, VODs, clips, total size), activity chart, recent videos
  - Archives: list (`/archives`) and detail (`/archives/[id]`) — register, run, and browse a source
  - File upload + full-bucket file browser (carried over from the starter kit)
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - Archive registry CRUD + background run pipeline (probe → ingest → metadata → clip → index)
  - B2 S3 integration via boto3; yt-dlp and ffmpeg contained in the repo layer
  - Health check endpoint with B2 connectivity verification
  - Structured JSON logging with request tracing; Prometheus-format metrics endpoint
- **packages/shared/** — TypeScript type definitions mirroring the Pydantic models

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access — boto3 (B2), yt-dlp, ffmpeg, manifest read/write
  |
service/   Business logic — registry CRUD, run pipeline, clip planning
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. **External tools live only in `repo/`**: `boto3`, `yt_dlp`, and `ffmpeg` (via `imageio-ffmpeg`) are never imported outside `repo/`
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (archives.py, files.py, ...)
    config/                Settings loaded from environment
    repo/                  b2_client.py, ytdlp_client.py, ffmpeg_client.py, manifest.py
    service/               archives.py, pipeline.py, clipping.py, files.py, ...
    runtime/               archives.py, files.py, upload.py, health.py, metrics.py
  tests/                   pytest tests (structural + hermetic archive + upload/files)
```

## The Archive Pipeline

A single **Archive** entry (a source URL + clip config) is the primary entity. Its
lifecycle and results live in a running manifest in B2 — there is no database.

### Repo adapters

- `repo/ytdlp_client.py` — wraps `yt_dlp`: `probe(url)`, `entry_urls(info)`,
  `download(url, dest_dir)`, `summarize(info)`. Points yt-dlp at the bundled
  ffmpeg via `ffmpeg_location`.
- `repo/ffmpeg_client.py` — wraps the static ffmpeg from `imageio_ffmpeg.get_ffmpeg_exe()`:
  `cut_clip(src, start, end, dest)` (stream copy, `+faststart`) and `probe_duration(path)`.
- `repo/b2_client.py` — S3 access: `upload_path` (managed multipart for large VODs),
  `upload_json` / `get_json` (small JSON), `get_presigned_url` (inline or attachment),
  `delete_prefix` (prefix-scoped, batched), plus the starter's file operations.
- `repo/manifest.py` — read/modify/write `archive/index.json` under a module-level
  `Lock` so concurrent requests and the run thread can't clobber each other.

### Background run

`POST /archives/{id}/run` marks the entry `status=running` and spawns a daemon
`threading.Thread` (yt-dlp downloads block). The thread runs
probe → download → upload VOD → write metadata JSON → plan clips → cut clips →
upload clips, updating the manifest entry's `status` / `progress` / `current_step`
at each stage. On failure it sets `status=failed` and `last_error`. A module-level
set of running ids plus a lock prevents double-runs. The UI polls
`GET /archives/{id}` while `status === "running"`.

## Boundary Invariants

- **No external SDK leakage**: `boto3`, `yt_dlp`, and ffmpeg live only in `app/repo/`.
- **No raw dicts at boundaries**: all cross-layer data uses typed Pydantic models.
- **Validated inputs**: source URLs pass an SSRF guard; object keys are traversal-checked
  and scoped to the `archive/` prefix for asset URLs.

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently` (web `:3000`, API `:8000`)
- **Railway** — two services from the same repo; see `infra/railway/README.md`
- The archive pipeline is CPU-only local I/O + stream-copy — **no ML, no GPU required**.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the sole data store:
  - `archive/index.json` — the running manifest (registered archives + run state + results)
  - `archive/vods/<id>/<vid>.mp4` — full VODs (managed multipart)
  - `archive/clips/<id>/<vid>/clip_NN.mp4` — highlight clips
  - `archive/meta/<id>/<vid>.json` — per-video yt-dlp metadata
  - `uploads/` — files from the carried-over upload page
- No application database — the manifest in B2 is the source of truth.

## External Services

- **Backblaze B2 S3 API** — storage, retrieval, deletion, presigned URLs.
- **yt-dlp** fetches from arbitrary source URLs (guarded by the SSRF check). No non-B2 API key.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware` is
  registered LAST in `main.py` (outermost) so it wraps **every** response, including
  uncaught-exception 500s. See [docs/RELIABILITY.md](docs/RELIABILITY.md#error-handling).
- **API -> source URL** — validated against an SSRF allowlist (http/https only; no
  loopback/private/link-local hosts) before yt-dlp fetches.
- **API -> B2** — authenticated via application keys, signature v4.
- **Client -> B2** — presigned URLs (inline for clip playback, attachment for download).

## Data Flows

- **Create**: Browser -> `POST /archives` -> service validates URL + derives slug -> manifest add
- **Run**: Browser -> `POST /archives/{id}/run` (202) -> background thread -> B2 writes -> manifest updates
- **Browse**: Browser -> `GET /archives/{id}` -> manifest read; clips fetched via `GET /archives/asset` presigned inline URLs
- **Delete**: Browser -> `DELETE /archives/{id}` -> prefix-scoped B2 deletes (`archive/vods|meta|clips/<id>/`) + manifest removal

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (also the catch-all converting uncaught exceptions to a typed JSON 500)
- `/metrics` (Prometheus format) and `/health` (B2 connectivity check)

## Canonical Files

- Route handler: `services/api/app/runtime/archives.py`
- Run orchestration: `services/api/app/service/pipeline.py`
- Registry logic: `services/api/app/service/archives.py`
- Repo adapters: `services/api/app/repo/{b2_client,ytdlp_client,ffmpeg_client,manifest}.py`
- Pydantic models: `services/api/app/types/archives.py`
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`; hermetic archive tests: `tests/test_archives.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`; hooks: `apps/web/src/lib/queries.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Archive Jobs](docs/features/archive-jobs.md)
- [VOD Ingest to B2](docs/features/vod-ingest.md)
- [Highlight Clips](docs/features/highlight-clips.md)
- [Archive Library](docs/features/archive-library.md)
- [File Upload](docs/features/file-upload.md)
- [File Browser](docs/features/file-browser.md)
- [Dashboard](docs/features/dashboard.md)
- [Metadata Extraction](docs/features/metadata-extraction.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
