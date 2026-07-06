<!-- last_verified: 2026-07-06 -->
# Feature: Archive Library & Manifest

## Purpose
Maintain a running manifest of every archive and its results in B2, and expose a scoped
browser to read it back with inline clip playback.

## Used By
- UI: `/archives` (list) and `/archives/[id]` (detail scoped explorer)
- API: `GET /archives`, `GET /archives/{id}`, `GET /archives/asset`

## Core Functions
- `repo/manifest.py` — read/modify/write `archive/index.json` under a lock
- `service/archives.py` — `list_archives`, `get_archive`, `get_asset_url`
- `apps/web/src/components/archives/archive-detail.tsx` — scoped explorer + `ClipCard`
- `apps/web/src/lib/queries.ts` — `useArchives` (polls the list every 2s while any archive is running, then stops), `useArchive` (polls while running), `useArchiveAsset`

## Canonical Files
- Manifest access: `services/api/app/repo/manifest.py`
- Scoped explorer: `apps/web/src/components/archives/archive-detail.tsx`

## Inputs
- Archive id (detail); asset key (presigned URL requests, scoped to `archive/`)

## Outputs
- `archive/index.json` — the running manifest (`ArchiveManifest`: archives[] + updated_at)
- `GET /archives/asset` → `{ url }` presigned (inline for `<video>`, attachment for downloads)

## Flow
- The manifest is the single source of truth (no database)
- List/detail read it via TanStack Query; the list polls every 2s while any archive is `running` (so the primary Run surface reflects live progress and completion without a manual reload) and the detail page polls while its own `status === "running"`. Both stop polling once nothing is running.
- Each clip/VOD/metadata asset is fetched through a presigned URL scoped to the `archive/` prefix
- Clips render inline in `<video>`; VOD and metadata JSON have download links

## Edge Cases
- Missing manifest → treated as empty (`ArchiveManifest()`)
- Concurrent writes (request + run thread) → serialized by a module-level lock
- Asset key outside `archive/` or containing traversal → 400

## UX States (if applicable)
- Empty: "Nothing archived yet" until a run completes
- Loading: skeletons for the list and each clip preview
- Error: inline error if a clip preview URL can't be signed

## Verification
- Test files: `services/api/tests/test_archives.py` (`test_list_empty`, `test_asset_url_scope`, `test_create_and_get`)
- Required cases: empty manifest, asset-key scoping, round-trip create→read
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure && pnpm build`
- Pass criteria: manifest round-trips; asset URLs reject out-of-scope keys; clips paint in `<video>`

## Related Docs
- [Archive Jobs](archive-jobs.md)
- [Dashboard](dashboard.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
