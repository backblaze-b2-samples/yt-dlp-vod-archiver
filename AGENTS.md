<!-- last_verified: 2026-06-25 -->
# AGENTS.md

This is the authoritative control surface for all coding agents. Read this first.

## 1. Repository Map

```
apps/web/          Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  src/app/archives/       Archives list + detail routes (primary feature)
  src/components/archives/ Archive UI (form dialog, list, detail, clip player)
services/api/      FastAPI backend (layered: types/config/repo/service/runtime)
  app/repo/               b2_client, ytdlp_client, ffmpeg_client, manifest
  app/service/            archives, pipeline, clipping (+ starter files/upload)
packages/shared/   Shared TypeScript types
docs/              System of record (features, workflows, security, reliability)
docs/exec-plans/   Execution plans and tech debt tracker
infra/railway/     Deployment config
```

## 2. What This App Is (and its reusable scaffolding)

This app is the **yt-dlp VOD Archiver**: register a source URL, run it, and the
background pipeline downloads the VOD (yt-dlp), streams it to B2, captures
metadata, and cuts highlight clips (ffmpeg). The primary entity is an **Archive**
(see [docs/features/archive-jobs.md](docs/features/archive-jobs.md)). It was built
on the vibe-coding-starter-kit; the starter scaffolding below is kept and reused.

**Keep as-is (do not strip, rename, or replace)**
- **UI kit / design system.** `apps/web/src/components/ui/` (shadcn primitives), the design tokens in `apps/web/src/app/globals.css`, and the `/design` reference page. Build new screens with these primitives; never edit the generated `components/ui/` files directly. Restyling happens through tokens in `globals.css`.
- **File Explorer.** `/files` route, `apps/web/src/app/files/`, and `apps/web/src/components/files/`. The Files sidebar entry stays. The archive detail page is a *scoped* explorer (`archive/<id>/`) and is additive — it never replaces `/files`.
- **Upload.** `/upload` route, `apps/web/src/app/upload/`, and `apps/web/src/components/upload/`. The Upload sidebar entry stays.
- The sidebar nav (Dashboard, Archives, Upload, Files, Settings, plus the Design System utility link).

**App-specific surfaces (this app's core)**
- **Archives.** `/archives` (list) and `/archives/[id]` (detail), `apps/web/src/components/archives/`, and the archive backend (`app/types/archives.py`, `app/repo/{ytdlp_client,ffmpeg_client,manifest}.py`, `app/service/{archives,pipeline,clipping}.py`, `app/runtime/archives.py`). This is the primary feature.
- **Dashboard.** `/` route and `apps/web/src/components/dashboard/` are repurposed for archive metrics (archives, VODs, clips, total size; activity chart; recent videos). Aggregations flow through the same `runtime -> service -> repo` layering and TanStack Query hooks in `apps/web/src/lib/queries.ts` — no bare `useEffect + fetch`. Update `docs/features/dashboard.md` in the same PR as any dashboard change (see §9).

**Why the scaffolding contract exists**
- The UI kit, Files, and Upload pages are reusable B2-backed surfaces — keep them so the app stays a coherent B2 sample. All external tools (`boto3`, `yt_dlp`, ffmpeg) stay contained in `app/repo/` (§3).

## 3. Architectural Invariants

**Backend layering**: `types` -> `config` -> `repo` -> `service` -> `runtime`

- No backward imports across layers
- No `boto3`, `yt_dlp`, or ffmpeg outside `repo/` — all external tools wrapped in `repo/` adapters
- No business logic in route handlers (`runtime/`)
- All request/response data validated at boundary (Pydantic models)
- The background run pipeline (`service/pipeline.py`) confines its mutable state to a
  module-level running-ids set + lock; manifest writes are serialized by a lock in `repo/manifest.py`

**Frontend**: shadcn/ui components in `src/components/ui/` are generated — never modify them.

**Data fetching**: every API call flows through TanStack Query hooks in `apps/web/src/lib/queries.ts`. No bare `useEffect + fetch` patterns. New endpoints touch three files: `runtime/<router>.py`, `lib/api-client.ts`, `lib/queries.ts`.

## 4. Quality Expectations

- **DRY** — do not duplicate logic, types, or constants. Extract shared code only when used in 2+ places.
- Structured JSON logging only — no `print()` statements
- No raw SDK calls outside `repo/` layer
- Files stay under 300 lines
- Tests added or updated for every behavior change
- Docs updated in same PR as code changes
- Lint clean before merge
- Prefer boring, composable libraries over clever abstractions
- No implicit type assumptions — use typed models

## 5. Mechanical Enforcement

| Rule | Enforced by |
|------|-------------|
| No backward imports | `tests/test_structure.py::test_no_backward_imports` |
| No boto3 outside repo/ | `tests/test_structure.py::test_boto3_only_in_repo` |
| File size < 300 lines | `tests/test_structure.py::test_file_size_limits` |
| All layers exist | `tests/test_structure.py::test_all_layers_exist` |
| No bare print() | `ruff` rule T20 |
| Import ordering | `ruff` rule I001 |
| Frontend strict equality | `eslint` rule eqeqeq |
| No unused vars | `eslint` + `ruff` rules |

## 6. Commands

```bash
# Run
pnpm dev               # start both frontend and backend
pnpm dev:web           # frontend only
pnpm dev:api           # backend only

# Test & Lint
pnpm lint              # frontend lint (eslint)
pnpm build             # frontend type check + build
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest)
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests
```

## 7. Agent Workflow

1. Read this file first.
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) before structural changes.
3. For non-trivial changes, create a plan in `docs/exec-plans/active/`.
4. Implement the smallest coherent change.
5. Run: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
6. Update docs in the same PR (see §9).
7. Move completed plans to `docs/exec-plans/completed/`.
8. Only change files relevant to the task. No drive-by improvements.

## 8. Frontend Conventions

See [docs/dev-workflows.md](docs/dev-workflows.md) for full details.

## 9. Doc Update Mapping

| Change Type | Update Location |
|-------------|-----------------|
| Feature logic, inputs, outputs, tests | `docs/features/<feature>.md` |
| User journeys | `docs/app-workflows.md` |
| System layout, deployments | `ARCHITECTURE.md` |
| Dev or testing process | `docs/dev-workflows.md` |
| Setup or scope changes | `README.md` |
| Security changes | `docs/SECURITY.md` |
| Reliability changes | `docs/RELIABILITY.md` |
| Active work plans | `docs/exec-plans/active/` |
| Known tech debt | `docs/exec-plans/tech-debt-tracker.md` |

If documentation and implementation conflict, update docs in the same PR. Documentation rot destroys agent reliability.

## 10. Doc Map

| Topic | Location |
|-------|----------|
| System layout, data flows, boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Primary feature (Archive lifecycle) | [docs/features/archive-jobs.md](docs/features/archive-jobs.md) |
| VOD ingest / clips / library | [docs/features/vod-ingest.md](docs/features/vod-ingest.md), [highlight-clips.md](docs/features/highlight-clips.md), [archive-library.md](docs/features/archive-library.md) |
| Feature docs | [docs/features/](docs/features/) |
| User journeys | [docs/app-workflows.md](docs/app-workflows.md) |
| Engineering workflows and testing | [docs/dev-workflows.md](docs/dev-workflows.md) |
| Security principles | [docs/SECURITY.md](docs/SECURITY.md) |
| Reliability expectations | [docs/RELIABILITY.md](docs/RELIABILITY.md) |
| Execution plans | [docs/exec-plans/](docs/exec-plans/) |
| Tech debt | [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md) |

## 11. When Unsure

- Prefer boring, stable libraries
- Prefer small PRs over large changes
- Add tests with every change
- Never bypass lint rules without explicit instruction
- Ask before making destructive or irreversible changes
