<!-- last_verified: 2026-07-06 -->
# yt-dlp VOD Archiver

A self-hosted, automated archive pipeline for **live streams and VODs** — built for content creators, media researchers, and fan communities who need a permanent copy before the upstream platform deletes it (often 60–90 days after broadcast). Register a source URL, run it, and the pipeline downloads the full VOD with **yt-dlp**, streams it straight into **[Backblaze B2](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-yt-dlp-vod-archiver)**, captures the video's metadata, cuts highlight clips with **ffmpeg**, and keeps a running manifest a lightweight in-app browser reads back.

Everything runs on local open-source tooling — **no second API key, B2 credentials only**. B2 is the storage layer for full VODs, highlight clips, per-video metadata JSON, and the channel index manifest, all via the S3-compatible API with a custom user agent and standardized `B2_*` env vars.

**What you get out of the box:**
- **Archives** — register / edit / delete / run a source URL (single VOD, playlist, or channel), with live run status.
- **VOD ingest to B2** — yt-dlp download streamed to B2 via boto3 managed multipart (multi-GB VODs never buffer in memory).
- **Highlight clips** — ffmpeg cuts clips by chapter markers or fixed interval, stream-copy (no re-encode).
- **Archive library** — a running `archive/index.json` manifest and a scoped `/archives` browser with inline clip playback.
- **Bucket explorer & upload** — the full-bucket `/files` browser and `/upload` page carried over from the starter kit.
- FastAPI backend with strict layered architecture and structural tests; agent-optimized docs.

## What it looks like

- **Dashboard** — archives, VODs archived, clips cut, total archived size, plus archive activity and recent archived videos.
- **Archives** — the list/detail flow: register a source, run it, and browse each archived video's metadata and clips.
- **Files** — the full B2 bucket explorer with preview, download, and delete.

## Quick Start

You need: Node.js >= 20, pnpm >= 9, Python >= 3.11, and a free **[Backblaze B2 account](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-yt-dlp-vod-archiver)**. No system ffmpeg is required — a static binary is bundled via `imageio-ffmpeg`.

### 1. Install dependencies

```bash
pnpm install
```

### 2. Set up the backend

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ../..
```

This installs `yt-dlp` and `imageio-ffmpeg` (the bundled ffmpeg) alongside the API deps.

### 3. Add your B2 credentials

```bash
cp .env.example .env
```

Open `.env` and fill in (all S3-compatible, no b2-native):

| Variable | Where it comes from |
|----------|---------------------|
| `B2_APPLICATION_KEY_ID` | keyID of a B2 application key with Read & Write |
| `B2_APPLICATION_KEY` | applicationKey (shown once — paste it now) |
| `B2_BUCKET_NAME` | your bucket's unique name |
| `B2_REGION` | e.g. `us-west-004` — the S3 endpoint is derived as `https://s3.<region>.backblazeb2.com` |
| `B2_PUBLIC_URL_BASE` | optional; leave blank to use short-lived presigned URLs |

> Walkthroughs: [creating a bucket](https://www.backblaze.com/docs/cloud-storage-create-and-manage-buckets?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-yt-dlp-vod-archiver) and [creating app keys](https://secure.backblaze.com/app_keys.htm?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-yt-dlp-vod-archiver).

### 4. Run it

```bash
pnpm dev
```

Frontend at `localhost:3000`, API at `localhost:8000`. `pnpm dev` runs `pnpm doctor` first — a preflight that catches common setup gotchas (wrong Node/Python version, missing venv, missing or placeholder `.env`, busy ports).

### 5. Archive your first VOD

Open **Archives → New archive**. For a quick, reliable demo the create form suggests a small stable source:

```
https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4
```

Leave the defaults (interval clips, 5s, up to 3), click **Create**, then **Run**. The page polls while the pipeline downloads, uploads to B2, and cuts clips — then browse the archived video, its metadata, and playable clips.

## How it works

```
Register source URL  ──▶  POST /archives         (manifest entry: status=idle)
        │
        └─ Run  ──▶  POST /archives/{id}/run      (202; background thread)
                        │
   probe (yt-dlp) ─▶ download VOD ─▶ upload_file to B2 (managed multipart)
        │                                   │
        └─ write meta JSON to B2            └─ cut clips (ffmpeg -c copy) ─▶ upload to B2
                        │
                        └─ update archive/index.json  (status=completed, progress=100)
```

The UI polls `GET /archives/{id}` while `status === "running"`, so progress and the current step update live.

## Building on This Kit

The reusable B2 scaffolding stays: the UI kit (`apps/web/src/components/ui/` + tokens in `globals.css` + `/design`), the File Explorer (`/files`), and Upload (`/upload`). The Dashboard is repurposed here for archive metrics. See [AGENTS.md §2](AGENTS.md#2-building-on-this-starter-kit).

## Core Features

- [Archive Jobs](docs/features/archive-jobs.md) — register / edit / delete / run a source; lifecycle + status
- [VOD Ingest to B2](docs/features/vod-ingest.md) — yt-dlp download streamed to B2 via managed multipart
- [Highlight Clips](docs/features/highlight-clips.md) — ffmpeg clips by chapters or interval
- [Archive Library](docs/features/archive-library.md) — the running manifest + scoped `/archives` browser
- [File Upload](docs/features/file-upload.md) — drag-and-drop upload with real-time progress
- [File Browser](docs/features/file-browser.md) — list, preview, download, delete files
- [Dashboard](docs/features/dashboard.md) — archive metrics, activity chart, recent videos
- [Metadata Extraction](docs/features/metadata-extraction.md) — image/PDF metadata for uploads
- [Design System](docs/design-system.md) — tokens, primitives, error/empty states. Live preview at `/design`.

## Tech Stack

- TypeScript, Next.js 16, React 19, Tailwind v4, shadcn/ui, Recharts
- TanStack Query — caching, dedup, retry for every fetch (polling while a run is in progress)
- Python 3.11+, FastAPI, boto3, Pydantic v2
- **yt-dlp** (VOD download) + **ffmpeg** (clip cutting, bundled via `imageio-ffmpeg`) — local, CPU-only, no API key
- Backblaze B2 (S3-compatible object storage)
- pnpm workspaces (monorepo)

## Commands

| Command | What it does |
|---------|-------------|
| `pnpm dev` | Start frontend + backend |
| `pnpm dev:web` | Frontend only |
| `pnpm dev:api` | Backend only |
| `pnpm build` | Build frontend |
| `pnpm lint` | Lint frontend |
| `pnpm lint:api` | Lint backend (ruff) |
| `pnpm test:api` | Run backend tests |
| `pnpm check:structure` | Verify layering rules |
| `pnpm test:e2e` | Playwright e2e tests (run `pnpm --filter @yt-dlp-vod-archiver/web exec playwright install chromium` once first) |

## Documentation Map

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Agent table of contents — start here |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layout, layering, data flows |
| [docs/features/](docs/features/) | Feature docs |
| [docs/app-workflows.md](docs/app-workflows.md) | User journeys |
| [docs/dev-workflows.md](docs/dev-workflows.md) | Engineering workflows and testing |
| [docs/SECURITY.md](docs/SECURITY.md) | Security principles (URL/SSRF, prefix-scoped delete) |
| [docs/RELIABILITY.md](docs/RELIABILITY.md) | Reliability expectations (background runs) |
| [docs/exec-plans/](docs/exec-plans/) | Execution plans and tech debt tracker |

## License

MIT License - see [LICENSE](LICENSE) for details.

## Claude Agent B2 Skill

Manage Backblaze B2 from your terminal using natural language (list/search, audits, stale or large file detection, security checks, safe cleanup).

Repo: [https://github.com/backblaze-b2-samples/claude-skill-b2-cloud-storage](https://github.com/backblaze-b2-samples/claude-skill-b2-cloud-storage)
