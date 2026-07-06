<!-- last_verified: 2026-07-06 -->
# Reliability

Reliability expectations and practices for this project.

## Background Archive Runs

- `POST /archives/{id}/run` returns `202` immediately and does the work on a daemon
  thread — the HTTP request never blocks on a multi-GB download.
- Run state is persisted to the manifest at each stage (`status`, `progress`,
  `current_step`), so a page reload always reflects live progress. The UI polls
  `GET /archives/{id}` while `status === "running"`.
- **Failures never crash the server.** `service/pipeline.py` wraps the whole run in a
  try/except that sets `status=failed` and records `last_error` on the manifest entry;
  the UI surfaces it inline.
- **Double-run guard.** A module-level set of running ids plus a lock means a second
  `run` for an in-progress archive returns `409` instead of starting a duplicate.
- **Manifest integrity.** All read-modify-write of `archive/index.json` is serialized
  by a lock in `repo/manifest.py`, so concurrent requests and the run thread can't
  clobber each other in-process.
- **Bounded work.** A run processes at most `MAX_VIDEOS_PER_RUN` videos from a
  playlist/channel source so a single run stays bounded.
- Temporary downloads use a `TemporaryDirectory` that is always cleaned up, even on error.

## Health Checks

- `GET /health` verifies B2 connectivity and returns `healthy` or `degraded`
- Health endpoint is always available, even when B2 is down

## Error Handling

- HTTP handlers return structured error responses with appropriate status codes
- External service failures (B2) are caught and surfaced as 500/503 responses
- No unhandled exceptions leak stack traces to clients
- Uncaught exceptions are converted to a typed JSON 500 (`{"detail": "Internal server error"}`, modeled by `app.types.ErrorResponse`) by the catch-all in `timing_middleware`
- **Error responses carry CORS headers.** `CORSMiddleware` is registered LAST in `main.py` so it is the outermost middleware and wraps every response — including uncaught-exception 500s produced by the inner catch-all. This is intentional and load-bearing: if a 500 shipped without `Access-Control-Allow-Origin`, the browser would block it and the frontend would surface only an opaque "network error", hiding the real server bug. Regression-guarded by `tests/test_error_handling.py::test_unhandled_exception_500_carries_cors_headers`.

## Logging

- Structured JSON logging via Python stdlib
- Every request gets a `request_id` for tracing
- Log levels: ERROR for failures, WARNING for degraded state, INFO for requests

## Observability

- Request timing middleware logs duration for every request
- `/metrics` endpoint exposes basic Prometheus-format counters
- Upload success/failure counts tracked

## Graceful Degradation

- File listing returns empty list (not error) when B2 has no objects
- Metadata extraction failures don't block upload (return partial metadata)
- Frontend shows skeleton states while loading, error states on failure

## Deployment

- Railway health checks on `/health`
- Zero-downtime deploys via rolling updates
- Environment-specific configuration via env vars (no config files in prod)
