<!-- last_verified: 2026-07-06 -->
# App Workflows

User journeys inside the application.

## Archive a VOD (create → run → browse)

- User navigates to `/archives`
- Clicks **New archive** → the create dialog opens
  - Enters a **Source URL** (a single VOD, playlist, or channel). The form hints a
    small, reliably-fetchable demo source.
  - Optional **Title** (derived from the URL if blank)
  - Selects **Clip mode** (interval / chapters / none), **Clip length**, and **Max clips**
    from selectors — create surfaces safe defaults (interval / 5s / 3) as guidance.
  - Clicks **Create** → a manifest entry appears with status `idle`
- Clicks **Run** on the archive → `POST /archives/{id}/run` returns 202 and the entry
  flips to `running`
- The list and detail pages poll `GET /archives/{id}` while `status === "running"`,
  showing a progress bar and the current step (probing → downloading → cutting clips)
- On completion the archive shows `completed` with its archived videos
- On failure the archive shows `failed` with the error message
- See: [Archive Jobs](features/archive-jobs.md)

## Browse an archive (scoped explorer)

- User opens `/archives/[id]`
- Header shows title, source URL, status, and Run / Edit / Delete actions
- **Archived videos** are listed; expanding one reveals:
  - Captured metadata (duration, size, VOD key) and download links for the VOD and
    the metadata JSON
  - Highlight **clips**, each with an inline `<video>` player (presigned URL) and a
    download button
- See: [Archive Library](features/archive-library.md)

## Edit or delete an archive

- **Edit**: opens the same dialog, pre-filled from the real archive; change the title
  or clip config and save
- **Delete**: confirmation dialog → prefix-scoped B2 cleanup (`archive/vods|meta|clips/<id>/`)
  plus removal of the manifest entry. Never a bucket-wide delete.

## View Dashboard

- User navigates to `/` (home)
- Stats cards show: archives, VODs archived, clips cut, total archived size
- Activity chart shows videos archived per day (last 7 days)
- Recent archived videos table shows the latest videos across all archives
- Empty states guide the user to create their first archive
- See: [Dashboard](features/dashboard.md)

## Browse & Upload files (carried-over B2 surfaces)

- `/files` — the full bucket explorer: tree view, preview, download, delete
- `/upload` — drag-and-drop upload with progress and metadata extraction
- See: [File Browser](features/file-browser.md), [File Upload](features/file-upload.md)
