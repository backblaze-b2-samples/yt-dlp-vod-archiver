<!-- last_verified: 2026-03-10 -->
# Tech Debt Tracker

Known tech debt items. Agents update this when they discover or create tech debt.

| Description | Impact | Proposed Resolution | Priority | Status |
|---|---|---|---|---|
| `datetime.utcnow()` deprecated in Python 3.12+ | Naive datetimes, future breakage | Replace with `datetime.now(UTC)` in `repo/b2_client.py`, `service/metadata.py` | High | Resolved |
| S3 client recreated on every API call | Connection pool wasted, added latency | Cache client as module-level singleton via `lru_cache` | High | Resolved |
| `get_upload_stats()` pagination broken at 1000 objects | Stats silently wrong for large buckets | Check `IsTruncated` + use `ContinuationToken` | High | Resolved |
| `record_upload()` never called | `/metrics` always reports 0 uploads | Call from `runtime/upload.py` after successful upload | Medium | Resolved |
| Metrics counters not thread-safe | Race conditions under concurrent requests | Use `threading.Lock` (matches `service/files.py` pattern) | Medium | Resolved |
| `_humanize_bytes` duplicated in Python (repo + service) | DRY violation, drift risk | Extract to `app/types/formatting.py` shared util | Medium | Resolved |
| `humanizeBytes` duplicated in TypeScript | DRY violation | Extract to `lib/utils.ts` | Low | Open |
| `formatDate` duplicated in TypeScript | DRY violation | Extract to `lib/utils.ts` | Low | Open |
| No test harness for feature specs | No automated verification | Add pytest fixtures + test files per feature | Medium | Resolved (partial — tests added for upload, files, activity, errors) |

## 2026-07-06 — verify

Nitpicks from the sample-3-verify UX funnel (goal: register + run an archive, then browse its metadata and playable highlight clips). All non-blocking; backlog only.

- New-archive dialog — the recommended demo source appears only as static helper text under the Source URL field (input left empty) → a first-time user must manually copy the ~90-char URL; add a one-click "Use demo URL" autofill affordance (shot: `.local/verify/A2/03-new-archive-dialog.png`).
- Archives list, post-create — a newly created archive is `Idle` and requires a separate click on the card's `Run`; the Create→Run handoff is a deliberate two-step → a "Create & run" option would shave one step off the fastest onboarding path (shot: `.local/verify/A2/11-list-bbb-running.png`).
- Archive detail, mid-run — the determinate progress bar advances across stages (10→50→70→100) but holds a single value *within* a stage; yt-dlp's own intra-download % is not surfaced → on a large VOD the bar would park at 10% for the whole download with only stage text as the liveness cue (shot: `.local/verify/B2/04-run-2-downloading-1-1-10-.png`).
- Archive detail, expanded video panel — the inline metadata panel surfaces title/duration/size only; resolution/codec/bitrate live only in the downloadable Metadata JSON → surface resolution inline for a more complete at-a-glance metadata view (shot: `.local/verify/C2/interval-02-detail-expanded.png`).
