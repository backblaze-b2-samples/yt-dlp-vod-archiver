<!-- last_verified: 2026-07-06 -->
# Feature: Archive Jobs

## Purpose
Register, edit, delete, and run an **Archive** — a monitored source URL plus its clip
configuration. This is the app's primary entity and lifecycle.

## Used By
- UI: `/archives` (list) and `/archives/[id]` (detail); `ArchiveFormDialog`, `DeleteArchiveDialog`
- API: `GET/POST /archives`, `GET/PUT/DELETE /archives/{id}`, `POST /archives/{id}/run`
- Job: background run thread in `service/pipeline.py`

## Core Functions
- `service/archives.py` — `create_archive`, `list_archives`, `get_archive`, `update_archive`, `delete_archive`, `run_archive`, `validate_source_url`
- `repo/manifest.py` — `add_archive`, `replace_archive`, `update_archive`, `remove_archive`, `list_archives`
- `runtime/archives.py` — thin route handlers

## Canonical Files
- Registry logic: `services/api/app/service/archives.py`
- Form UI (create + edit): `apps/web/src/components/archives/archive-form-dialog.tsx`

## Inputs
- `ArchiveConfig` (create/edit): `url` (str, http/https, SSRF-checked), `title` (str, optional),
  `clip_mode` ("interval" | "chapters" | "none"), `clip_length_seconds` (int), `max_clips` (int)

## Outputs
- `Archive` (id slug, title, url, clip config, status, progress, current_step, last_error, videos[])
- Side effects: entry written to `archive/index.json` in B2; run spawns a background thread

## Flow
- Create → validate URL, derive a unique slug id, append manifest entry (status `idle`)
- Run → mark `running`, spawn daemon thread (see [VOD Ingest](vod-ingest.md)), return 202
- Edit → update title/clip config on the existing entry (id unchanged)
- Delete → prefix-scoped B2 cleanup + manifest removal

## Edge Cases
- Non-http(s) / loopback / private URL → 400 (SSRF guard)
- Run while already running → 409 (double-run guard)
- Run/edit/delete of an unknown id → 404
- Duplicate title → slug is de-duplicated (`title`, `title-2`, …)

## UX States (if applicable)
- Empty: "No archives yet" with a New-archive action
- Loading: skeleton rows
- Error: inline `ErrorState` with retry
- Running: progress bar + current step (polled)
- Failed: inline error message

## Verification
- Test files: `services/api/tests/test_archives.py`
- Required cases: create + get, private-URL rejection, update, delete (prefix-scoped), double-run guard
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure && pnpm build`
- Pass criteria: all pytest green, ruff clean, frontend builds

## Related Docs
- [VOD Ingest to B2](vod-ingest.md)
- [Highlight Clips](highlight-clips.md)
- [Archive Library](archive-library.md)
- [App Workflows](../app-workflows.md)
