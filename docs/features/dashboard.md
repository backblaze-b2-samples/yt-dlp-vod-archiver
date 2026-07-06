<!-- last_verified: 2026-07-06 -->
# Feature: Dashboard

## Purpose
Provide an at-a-glance overview of VOD archive activity on Backblaze B2.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /archives/stats`, `GET /archives/stats/activity`, `GET /archives`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — 4 stat cards (archives, VODs, clips, total size)
- `apps/web/src/components/dashboard/activity-chart.tsx` — bar chart of videos archived per day
- `apps/web/src/components/dashboard/recent-videos-table.tsx` — latest archived videos across all archives
- `apps/web/src/lib/queries.ts` — `useArchiveStats()`, `useArchiveActivity()`, `useArchives()`
- `services/api/app/runtime/archives.py` — `GET /archives/stats`, `/archives/stats/activity`
- `services/api/app/service/archives.py` — `get_stats()`, `get_activity()` aggregation

## Canonical Files
- Stats cards: `apps/web/src/components/dashboard/stats-cards.tsx`
- Stats service logic: `services/api/app/service/archives.py`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /archives/stats` → `ArchiveStats` (total_archives, total_videos, total_clips, total_size_bytes, total_size_human)
- `GET /archives/stats/activity?days=7` → `DailyArchiveCount[]` (videos archived per day)
- `GET /archives` → `Archive[]`; the recent-videos table flattens `archives[].videos[]` client-side, newest first

## Flow
- Page loads → parallel API calls (archive stats, activity, archives list)
- Stats cards display archives, VODs archived, clips cut, total archived size
- Activity chart displays videos archived per day for the last 7 days
- Recent videos table shows the latest archived videos with title, size, clip count, date

## Edge Cases
- API unavailable → error states with retry where supported
- No archives / no videos → empty chart + table messages
- Many archives → stats are computed from the manifest (single JSON read)

## UX States
- Loading: skeleton placeholders for cards, table, and activity chart
- Empty: "No activity yet" / "No videos archived yet"
- Loaded: populated cards, chart, table

## Verification
- Test files: `services/api/tests/test_archives.py` (`test_stats_and_activity`)
- Required cases: stats with an archive, empty state, activity window length
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure && pnpm build`
- Pass criteria: all pytest tests green, no ruff violations, frontend builds

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
- [Archive Library](archive-library.md)
