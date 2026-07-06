<!-- last_verified: 2026-07-06 -->
# Security

Security principles and implementation for the yt-dlp VOD Archiver.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/PUT/DELETE/OPTIONS`
- **API -> source URL**: validated by an SSRF guard before yt-dlp fetches (see below)
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` + `B2_APPLICATION_KEY`, signature v4
- **Client -> B2**: Presigned URLs — inline (`Content-Disposition: inline`) for clip playback, attachment for downloads

## Source-URL Validation (SSRF guard)

Before yt-dlp fetches any source, `app/service/archives.py::validate_source_url`:

- Requires an `http` or `https` scheme (rejects `file:`, `ftp:`, etc.)
- Requires a host
- Rejects `localhost` and known metadata hosts
- If the host is an IP literal, rejects private, loopback, link-local, reserved, and
  multicast ranges

This prevents a user from pointing the downloader at internal/loopback services. The
guard runs on both create and edit.

## Archive Key & Deletion Safety

- Archive **ids are sanitized slugs** (lowercase alnum + hyphen), so they can't inject
  path traversal into object keys.
- Asset URLs (`GET /archives/asset`) reject traversal patterns (`../`, `%2e%2e`, null
  bytes, backslashes) and require the key to be under the `archive/` prefix.
- **Deletes are prefix-scoped only.** `DELETE /archives/{id}` removes exactly
  `archive/vods/<id>/`, `archive/meta/<id>/`, and `archive/clips/<id>/` plus the manifest
  entry. `repo/b2_client.py::delete_prefix` refuses an empty prefix — there is no
  bucket-wide delete path.

## Upload Validation (carried-over upload page)

- Filename sanitization: path traversal, null bytes, unsafe chars stripped
- MIME/extension consistency check against an allowlist
- Chunked streaming with size enforcement (100MB default)
- Empty file rejection

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- Only `B2_*` credentials are needed — no second API key
- `.env` is never committed; `.env.example` documents the required variables without values

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken the SSRF guard or key validation without explicit instruction
- Never introduce an unscoped/bucket-wide delete
- Always validate at system boundaries
