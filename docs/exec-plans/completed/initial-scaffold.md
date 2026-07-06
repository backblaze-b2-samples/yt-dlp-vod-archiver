# Build plan — `yt-dlp-vod-archiver`

Source of truth for the starter tree: `.claude/scratch/vcsk-a916500e-63ff-43d2-bc6f-eece072e6ddf/`
(fresh clone). All keep/trim/add deltas are computed against that tree.

## 1. Purpose

`yt-dlp-vod-archiver` is a self-hosted, automated archive pipeline for content
creators, media researchers, and fan communities who need a permanent copy of
live streams and VODs before the upstream platform deletes them (typically after
60–90 days). You register an **Archive** (a source URL — a single VOD, a
playlist, or a channel), configure how highlight clips are cut, and run it. The
pipeline uses **yt-dlp** to download the full VOD, streams it straight into
Backblaze B2, captures the video's metadata JSON, cuts highlight clips with
**ffmpeg**, and updates a running manifest (`archive/index.json`) in B2 that a
lightweight in-app browser reads back. Everything runs on local OSS — no second
API key, **B2 credentials only**. B2 is the storage layer for full VODs,
highlight clips, per-video metadata JSON, and the channel index manifest, all via
the S3-compatible API with a custom user agent and standardized `B2_*` env vars.

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is the ceiling: keep the whole scaffold, strip nothing structural,
adapt the dashboard, and add the archive feature on top.

### KEEP (as-is — starter contract + non-negotiable bucket explorer)
- Entire shadcn/ui kit (`apps/web/src/components/ui/`), design tokens
  (`globals.css`), and `/design` reference page.
- **Bucket explorer — `/files` (NON-NEGOTIABLE keep).** Full-bucket browse:
  `apps/web/src/app/files/`, `components/files/*`, `lib/file-tree.ts`, and the
  Files sidebar entry. This is never removable.
- **Upload — `/upload`** (`app/upload/`, `components/upload/*`, `POST /upload`,
  `service/upload.py`, `runtime/upload.py`) + its metadata extraction
  (`service/metadata.py`, Pillow/PyPDF2). Reusable B2 surface; kept as-is.
- Layout shell (sidebar, header, health banner, command palette, theme provider),
  TanStack Query data layer (`lib/queries.ts`, `lib/query-client.tsx`,
  `lib/api-client.ts` core helpers), `/settings` + settings-form (adapt copy only).
- Backend spine: layered architecture (`types→config→repo→service→runtime`),
  `main.py` app/middleware/logging, `runtime/health.py`, `runtime/metrics.py`,
  `types/errors.py`, `types/formatting.py`, structural tests
  (`tests/test_structure.py`), `pyproject.toml` ruff config.
- Dev harness: `scripts/dev.sh`, `scripts/pick-port.mjs`, `scripts/doctor.mjs`
  (update its B2 var list — see rename table), root `package.json` scripts,
  `pnpm-workspace.yaml`, pre-commit config.

### TRIM (content adaptation / removal, not scaffold deletion)
- Dashboard default copy/metrics: the upload-centric stats cards, upload chart,
  and "recent uploads" table are illustrative — **adapt** them to archive metrics
  (per AGENTS.md §2, the dashboard is the designated adapt target). Not deleted;
  repurposed.
- Starter README screenshots `docs/images/b2-starterkit-*.png` — delete (they are
  branded starter-kit captures, not ours). README's "What it looks like" section
  drops the image embeds; the later screenshot pipeline step adds real ones.
- Starter-specific exec-plan history in `docs/exec-plans/completed/*` — remove the
  five starter-era plans (they describe the starter's own build, not ours); keep
  the `active/.gitkeep` and `tech-debt-tracker.md`.

  > **Note on the tension the skill asks me to record:** nothing about a VOD
  > archiver argues for removing the bucket explorer, so `/files` stays in KEEP
  > verbatim. The new `/archives` explorer is *scoped* to `archive/` and is
  > additive, not a replacement.

### ADD (new for yt-dlp-vod-archiver)
- **Primary entity — Archive** (full CRUD + run; see §4).
  - Backend types `types/archives.py`: `Archive`, `ArchiveConfig`,
    `ArchivedVideo`, `Clip`, `ArchiveManifest`, `RunStatus` (Pydantic).
  - `repo/ytdlp_client.py` — wraps the `yt_dlp` library: `probe(url)` → info
    (id, title, duration, chapters, thumbnail) and `download(url, dest_dir)` →
    (local file path, info dict). External tool contained in `repo/` per the
    invariant. Points yt-dlp at the bundled ffmpeg via `ffmpeg_location`.
  - `repo/ffmpeg_client.py` — wraps ffmpeg (binary from `imageio_ffmpeg.
    get_ffmpeg_exe()`): `cut_clip(src_path, start_s, end_s, dest_path)` using
    stream copy (`-ss/-to/-c copy`) — no libass/drawtext needed.
  - `repo/b2_client.py` — extend with `upload_path(local_path, key, content_type)`
    using boto3 **managed multipart transfer** (`client.upload_file`) so multi-GB
    VODs stream without buffering in memory; `upload_json(key, obj)`,
    `get_json(key)`, and `delete_prefix(prefix)` (list+`delete_objects`, batched)
    for prefix-scoped cleanup.
  - `repo/manifest.py` — read/modify/write `archive/index.json` (the running
    manifest) with a module-level `Lock` to serialize read-modify-write in-process.
  - `service/archives.py` — registry CRUD over the manifest (create/list/get/
    update/delete an Archive entry), slug derivation, URL validation.
  - `service/pipeline.py` — the run orchestration: monitor→ingest→metadata→clip→
    index. Runs in a daemon `threading.Thread` (yt-dlp download is blocking);
    updates the manifest entry's `status`/`progress`/`current_step` at each stage
    so a page reload reflects live state. Split across files if either nears the
    300-line limit (e.g. `service/clipping.py` for clip-plan logic).
  - `runtime/archives.py` — thin routes: `GET /archives`, `POST /archives`,
    `GET /archives/{id}`, `PUT /archives/{id}`, `DELETE /archives/{id}`,
    `POST /archives/{id}/run` (returns 202, status=running). No business logic.
  - Register `archives.router` in `main.py`; add `"PUT"` to CORS `allow_methods`.
- **Frontend**
  - `packages/shared/src/types.ts` — add `Archive`, `ArchivedVideo`, `Clip`,
    `ArchiveManifest`, `RunStatus` TS mirrors.
  - `lib/api-client.ts` — `getArchives`, `getArchive`, `createArchive`,
    `updateArchive`, `deleteArchive`, `runArchive`.
  - `lib/queries.ts` — `useArchives`, `useArchive(id)` (with `refetchInterval`
    while `status==="running"`), `useCreateArchive`, `useUpdateArchive`,
    `useDeleteArchive`, `useRunArchive`; extend `qk` query-key factory.
  - `/archives` list page (`app/archives/page.tsx`) + `components/archives/
    archive-list.tsx` — cards/table with status badge and per-row Run / View /
    Edit / Delete. Empty + error + loading states.
  - `/archives/[id]` detail page (`app/archives/[id]/page.tsx`) +
    `components/archives/archive-detail.tsx` — **the sample-specific asset
    explorer, scoped to `archive/<id>/`**: header (title/url/status), Run/Edit/
    Delete actions, and a list of archived videos each expandable to show its
    captured metadata (from the meta JSON) and its highlight clips with an inline
    `<video>` player (presigned URL) + download. Clips are real MP4s and MUST
    actually paint.
  - `components/archives/archive-form-dialog.tsx` — shared create/edit form
    (react-hook-form + zod), modeled on `settings/settings-form.tsx`. Used by both
    Create and Edit. See §4 form UX.
  - `components/archives/delete-archive-dialog.tsx` — AlertDialog like
    `file-browser`'s delete confirm.
  - Sidebar: add `{ title: "Archives", href: "/archives", icon: Film }` to
    `app-sidebar.tsx` nav (place first, above Upload). Add `"/archives": "Archives"`
    to `header.tsx` `pageTitles`.
  - Dashboard: repurpose `components/dashboard/*` to archive metrics
    (archives, VODs archived, clips cut, total archived size; archive activity
    over N days; recent archived videos) reading new archive stats. Keep the same
    `runtime→service→repo` + TanStack Query flow (no bare `useEffect+fetch`).
  - Archive stats endpoint `GET /archives/stats` (+ `/archives/stats/activity`)
    for the dashboard, added in `runtime/archives.py`/`service/archives.py`.
- **Deps**
  - Backend `requirements.txt`: `yt-dlp` (pin to a recent released version verified
    at build time — yt-dlp is date-versioned and must be reasonably fresh) and
    `imageio-ffmpeg>=0.5.1` (ships a static ffmpeg binary; avoids a system ffmpeg
    dependency — per the known "Homebrew ffmpeg has no libass / bundle
    imageio-ffmpeg" gotcha).
  - Frontend: none — inline `<video>` for clip preview, existing shadcn primitives.

## 3. B2 surface (S3-compatible only — no b2-native)

All via the S3 API on the boto3 client (custom `user_agent_extra`, `region_name`
from `B2_REGION`):
- `put_object` — small JSON: `archive/index.json`, `archive/meta/<id>/<vid>.json`.
- `upload_file` (managed multipart) — full VOD `archive/vods/<id>/<vid>.mp4`,
  clips `archive/clips/<id>/<vid>/clip_NN.mp4`. Drives the sustained-write story.
- `list_objects_v2` — bucket explorer, stats, prefix listing.
- `head_object` — object metadata.
- `generate_presigned_url` (GET) — download + inline clip/VOD preview.
- `delete_object` / `delete_objects` — prefix-scoped archive deletion only
  (`archive/vods/<id>/`, `archive/meta/<id>/`, `archive/clips/<id>/`, and the
  index entry). **Never** an unscoped/bucket-wide delete (CLAUDE.local.md safety).

No b2-native API anywhere. No justification needed — everything is S3.

## 4. Key features

Primary entity: **Archive** (a monitored source URL + clip config). All five
lifecycle verbs are user-accessible → **all built, `omitted_ui_verbs` is empty.**

| Verb | UI surface | Notes |
|------|-----------|-------|
| Create | "New archive" → `ArchiveFormDialog` | URL + title + clip config |
| Read | `/archives` list + `/archives/[id]` detail (scoped explorer) | manifest-driven |
| Edit | "Edit" → same dialog, pre-filled | change title/clip config |
| Delete | "Delete" → AlertDialog | prefix-scoped B2 cleanup + index entry |
| Run | "Run" button → `POST /archives/{id}/run` | background pipeline, UI polls status |

Feature list (seeds README + `docs/features/<feature>.md` stubs):
1. **Archive jobs** — register/edit/delete/run a source; lifecycle + status.
2. **VOD ingest to B2** — yt-dlp download streamed to B2 via managed multipart.
3. **Video metadata capture** — yt-dlp per-video JSON written to `archive/meta/`.
4. **Highlight clips** — ffmpeg cuts clips by chapter markers or fixed interval.
5. **Archive library & manifest** — `archive/index.json` running manifest + the
   scoped `/archives` browser.
6. **Bucket explorer & upload** — kept full-bucket `/files` + `/upload`.

### External API provider
**None.** Per `api-provider-selection.md` Step 1, the app's whole point is
yt-dlp + ffmpeg + B2; there is no non-B2 external API. Per-feature deployment:

| Feature | deployment | provider/model | per-run cost | key env var |
|---------|-----------|----------------|--------------|-------------|
| VOD ingest | **local** | yt-dlp (OSS lib) | $0 | none |
| Highlight clips | **local** | ffmpeg (bundled via imageio-ffmpeg) | $0 | none |
| Metadata capture | **local** | yt-dlp | $0 | none |

All heavy work is on-device I/O + stream-copy — **no ML inference, no GPU
required**. The local-default/GPU-autodetect rule is satisfied trivially (CPU-only
tools; no CUDA/MPS path is meaningful). Only credentials are the standard `B2_*`.
No Genblaze (the description doesn't mention it).

### Highlight-clip strategy (deterministic, local, keyless)
`clip_mode` selector, three values:
- `chapters` — one clip per yt-dlp chapter marker (start→end), up to `max_clips`.
- `interval` — evenly-spaced clips of `clip_length_seconds`, up to `max_clips`
  (works on any video incl. chapterless; the safe demo default).
- `none` — archive VOD + metadata only, no clips.
No transcript/chat API needed (would require a second key — out of scope per
"B2 credentials only"). Chat/keyword modes noted as future work in the docs.

### Form UX conventions (create/edit `ArchiveFormDialog`)
Finite-value fields use selectors (both create + edit); create surfaces safe
defaults as placeholder/`FormDescription` guidance (no autofill button):
- `url` — free text `Input`. **Create hint** (FormDescription): recommend a small,
  reliably-fetchable demo source, e.g.
  `https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4`
  (~2.5 MB, ~15 s, stable CDN — yt-dlp generic extractor handles it).
- `title` — free text `Input`, placeholder "For Bigger Blazes".
- `clip_mode` — **RadioGroup/Select** {chapters, interval, none}. Create default
  hint: `interval` (works on any video).
- `clip_length_seconds` — **Select** of presets {5, 15, 30, 60}. Create hint: 5.
- `max_clips` — **Select** of presets {1, 3, 5, 10}. Create hint: 3.
Edit opens pre-filled from the real archive. Exemplar: `settings-form.tsx`.

### Manifest shape (`archive/index.json` — the running manifest)
```jsonc
{
  "archives": [{
    "id": "for-bigger-blazes", "title": "...", "url": "...",
    "clip_mode": "interval", "clip_length_seconds": 5, "max_clips": 3,
    "status": "completed", "progress": 100, "current_step": "done",
    "last_error": null, "created_at": "...", "last_run_at": "...",
    "videos": [{
      "video_id": "...", "title": "...", "duration_seconds": 15,
      "vod_key": "archive/vods/<id>/<vid>.mp4",
      "meta_key": "archive/meta/<id>/<vid>.json",
      "size_bytes": 2500000, "thumbnail_url": "...", "archived_at": "...",
      "clips": [{ "key": "archive/clips/<id>/<vid>/clip_01.mp4",
                  "start": 0, "end": 5, "label": "Segment 1" }]
    }]
  }],
  "updated_at": "..."
}
```

### Run lifecycle (background, poll-driven)
`POST /archives/{id}/run` → set entry `status=running`, spawn a daemon thread,
return 202. Thread: probe (yt-dlp) → download VOD → `upload_path` to B2 →
write meta JSON → compute clip plan → cut clips (ffmpeg) → upload clips → update
manifest entry (videos + clips + `status=completed`), updating `progress`/
`current_step` at each stage. On failure: `status=failed`, `last_error` set. A
module-level `set` of running ids + `Lock` prevents double-runs. UI `useArchive`
polls (`refetchInterval`) while `status==="running"`.

### Env var rename (Standard #3 — parent CLAUDE.md, b2-doctor gate)
Starter uses non-standard names; rename everywhere:
| Starter | Standard #3 |
|---------|-------------|
| `B2_KEY_ID` | `B2_APPLICATION_KEY_ID` |
| `B2_ENDPOINT` | `B2_REGION` (endpoint derived: `https://s3.{region}.backblazeb2.com`) |
| `B2_APPLICATION_KEY` | `B2_APPLICATION_KEY` (unchanged) |
| `B2_BUCKET_NAME` | `B2_BUCKET_NAME` (unchanged) |
| `B2_PUBLIC_URL` | `B2_PUBLIC_URL_BASE` |
Touches: `config/settings.py`, `repo/b2_client.py` (endpoint from region +
`region_name`), `main.py` (`REQUIRED_B2_SETTINGS`/`PLACEHOLDER_VALUES`),
`scripts/doctor.mjs` (`REQUIRED_B2_VARS`/`PLACEHOLDERS`), `.env.example`,
`README.md`, `infra/railway/README.md`, any docs. Custom user agent stays on
every client.

### Security
- **URL validation** before yt-dlp fetch (SSRF guard): scheme must be
  `http`/`https`; reject loopback/private/link-local hosts. Document in
  `docs/SECURITY.md`.
- Derive archive `id` as a sanitized slug; sanitize keys (reuse the traversal
  guards). Prefix-scoped deletes only.

## 5. Doc transforms
- **Rewrite**: `README.md` (VOD-archiver purpose, features, quickstart w/ renamed
  env vars, ffmpeg-bundled note, commands, no starter screenshots), `AGENTS.md`
  (repo map + §2 building-on + doc map reflect archives), `ARCHITECTURE.md`
  (archive pipeline data flow, ytdlp/ffmpeg repo adapters, background run),
  `docs/app-workflows.md` (create→run→browse journey), `docs/SECURITY.md`
  (URL/SSRF + prefix-scoped delete), `docs/RELIABILITY.md` (background-run failure
  handling), `docs/features/dashboard.md` (archive metrics), `infra/railway/
  README.md` (env names/app name).
- **Keep**: `docs/features/file-upload.md`, `file-browser.md`,
  `metadata-extraction.md` (generic, still accurate), `docs/design-system.md`,
  `docs/dev-workflows.md` (minor: new deps + ffmpeg note).
- **Add (new feature docs, from `_template.md`)**: `docs/features/archive-jobs.md`,
  `docs/features/vod-ingest.md`, `docs/features/highlight-clips.md`,
  `docs/features/archive-library.md`.
- **Delete**: `docs/images/b2-starterkit-*.png`, starter-era
  `docs/exec-plans/completed/2026-02-*.md` (keep tech-debt-tracker + active).

## 6. Rename table
| From | To |
|------|----|
| dir `vibe-coding-starter-kit` | `yt-dlp-vod-archiver` |
| pkg scope `@vibe-coding-starter-kit/*` | `@yt-dlp-vod-archiver/*` (root+apps/web+packages/shared package.json, all imports, root script `--filter` names) |
| root pkg `name: vibe-coding-starter-kit` | `yt-dlp-vod-archiver` |
| `APP_NAME = "OSS Starter Kit"` | `"yt-dlp VOD Archiver"` |
| `APP_DESCRIPTION` | `"Automated VOD & live-stream archive pipeline on Backblaze B2"` |
| FastAPI `title="OSS Starter Kit API"` | `"yt-dlp VOD Archiver API"` |
| `user_agent_extra="b2ai-oss-start"` | `"b2ai-yt-dlp-vod-archiver"` |
| UTM `utm_content=b2ai-oss-start` (sidebar footer, README, doctor app-keys link) | `utm_content=b2ai-yt-dlp-vod-archiver` |
| env `B2_KEY_ID`/`B2_ENDPOINT`/`B2_PUBLIC_URL` | `B2_APPLICATION_KEY_ID`/`B2_REGION`/`B2_PUBLIC_URL_BASE` |

## 7. Standards & invariants to hold
- S3 API only; custom UA on every client; Standard #3 env names.
- Layering `types→config→repo→service→runtime`; `boto3` + `yt_dlp` + ffmpeg only
  in `repo/`; thin route handlers; Pydantic at boundaries; files <300 lines;
  structured logging (no `print`); ruff + eslint clean.
- New archive tests must be **hermetic** (mock `repo/ytdlp_client`,
  `repo/ffmpeg_client`, and B2 — no network/downloads), plus a no-network
  import/signature guard. Keep existing upload/files/health/metrics tests green.
- Verify criterion: `pnpm lint && pnpm lint:api && pnpm test:api &&
  pnpm check:structure && pnpm build` all pass; end-to-end a demo Archive can be
  created, run, and its VOD + clips + metadata browsed with media actually
  painting.
