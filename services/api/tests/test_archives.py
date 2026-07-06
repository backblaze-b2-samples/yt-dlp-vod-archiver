"""Hermetic tests for the VOD archive pipeline.

No network, no downloads: B2 is replaced with an in-memory manifest store and
yt-dlp / ffmpeg are monkeypatched. A signature guard proves the repo adapters
import and expose the expected surface without touching the network.
"""

import pytest

from app.types import ArchiveConfig


@pytest.fixture
def mem_manifest(monkeypatch):
    """Back the manifest with an in-memory dict instead of B2."""
    store: dict[str, dict] = {}

    def fake_get(key):
        return store.get(key)

    def fake_put(key, obj):
        store[key] = obj

    monkeypatch.setattr("app.repo.manifest.get_json", fake_get)
    monkeypatch.setattr("app.repo.manifest.upload_json", fake_put)
    return store


# ----- Registry CRUD (via the HTTP API) -----


async def test_list_empty(client, mem_manifest):
    resp = await client.get("/archives")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_and_get(client, mem_manifest):
    resp = await client.post(
        "/archives",
        json={
            "url": "https://example.com/ForBiggerBlazes.mp4",
            "title": "For Bigger Blazes",
            "clip_mode": "interval",
            "clip_length_seconds": 5,
            "max_clips": 3,
        },
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["id"] == "for-bigger-blazes"
    assert created["status"] == "idle"
    assert created["clip_mode"] == "interval"

    got = await client.get(f"/archives/{created['id']}")
    assert got.status_code == 200
    assert got.json()["title"] == "For Bigger Blazes"


async def test_create_rejects_private_url(client, mem_manifest):
    for bad in ("http://127.0.0.1/x.mp4", "ftp://example.com/x", "http://localhost/x"):
        resp = await client.post("/archives", json={"url": bad})
        assert resp.status_code == 400, bad


async def test_update_archive(client, mem_manifest):
    created = (
        await client.post("/archives", json={"url": "https://example.com/a.mp4"})
    ).json()
    resp = await client.put(
        f"/archives/{created['id']}",
        json={
            "url": "https://example.com/a.mp4",
            "title": "Renamed",
            "clip_mode": "none",
            "clip_length_seconds": 30,
            "max_clips": 1,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Renamed"
    assert resp.json()["clip_mode"] == "none"


async def test_update_missing_404(client, mem_manifest):
    resp = await client.put("/archives/nope", json={"url": "https://example.com/a.mp4"})
    assert resp.status_code == 404


async def test_delete_archive(client, mem_manifest, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.service.archives.delete_prefix", lambda prefix: calls.append(prefix)
    )
    created = (
        await client.post("/archives", json={"url": "https://example.com/a.mp4"})
    ).json()
    resp = await client.delete(f"/archives/{created['id']}")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": True, "id": created["id"]}
    # Prefix-scoped cleanup only (vods, meta, clips) — never bucket-wide.
    assert calls == [
        f"archive/vods/{created['id']}/",
        f"archive/meta/{created['id']}/",
        f"archive/clips/{created['id']}/",
    ]
    assert (await client.get(f"/archives/{created['id']}")).status_code == 404


async def test_stats_and_activity(client, mem_manifest):
    await client.post("/archives", json={"url": "https://example.com/a.mp4"})
    stats = await client.get("/archives/stats")
    assert stats.status_code == 200
    assert stats.json()["total_archives"] == 1
    assert stats.json()["total_videos"] == 0

    activity = await client.get("/archives/stats/activity?days=7")
    assert activity.status_code == 200
    assert len(activity.json()) == 7


async def test_asset_url_scope(client, mem_manifest):
    # Traversal + non-archive prefixes rejected.
    bad = await client.get("/archives/asset?key=uploads/secret.mp4")
    assert bad.status_code == 400
    traversal = await client.get("/archives/asset?key=archive/../etc/passwd")
    assert traversal.status_code == 400


# ----- Background run (mocked tools, synchronous _run) -----


async def test_run_pipeline_hermetic(mem_manifest, monkeypatch):
    from app.repo import ffmpeg_client, ytdlp_client
    from app.service import archives as svc
    from app.service import pipeline

    archive = svc.create_archive(
        ArchiveConfig(
            url="https://example.com/demo.mp4",
            title="Demo",
            clip_mode="interval",
            clip_length_seconds=5,
            max_clips=3,
        )
    )

    monkeypatch.setattr(ytdlp_client, "probe", lambda url: {"webpage_url": url})
    monkeypatch.setattr(ytdlp_client, "entry_urls", lambda info: ["https://example.com/demo.mp4"])
    monkeypatch.setattr(
        ytdlp_client, "download", lambda url, d: ("/tmp/demo.mp4", {"id": "demo"})
    )
    monkeypatch.setattr(
        ytdlp_client,
        "summarize",
        lambda info: {
            "video_id": "demo",
            "title": "Demo",
            "duration_seconds": 10.0,
            "thumbnail_url": None,
            "chapters": [],
        },
    )
    monkeypatch.setattr(ffmpeg_client, "cut_clip", lambda *a, **k: None)
    monkeypatch.setattr("app.service.pipeline.upload_path", lambda p, key, ct=None: 123)
    monkeypatch.setattr("app.service.pipeline.upload_json", lambda key, obj: None)

    pipeline._run(archive.id)

    result = svc.get_archive(archive.id)
    assert result.status == "completed"
    assert result.progress == 100
    assert len(result.videos) == 1
    assert result.videos[0].vod_key == f"archive/vods/{archive.id}/demo.mp4"
    assert len(result.videos[0].clips) == 3


async def test_double_run_guarded(mem_manifest, monkeypatch):
    from app.service import archives as svc
    from app.service import pipeline

    archive = svc.create_archive(ArchiveConfig(url="https://example.com/x.mp4"))
    monkeypatch.setattr(pipeline, "_running", {archive.id})
    # Already running -> start_run refuses, run endpoint would 409.
    assert pipeline.start_run(archive.id) is False


# ----- No-network import / signature guard -----


def test_repo_adapter_signatures():
    import inspect

    from app.repo import b2_client, ffmpeg_client, manifest, ytdlp_client

    assert callable(ytdlp_client.probe)
    assert callable(ytdlp_client.download)
    assert callable(ffmpeg_client.cut_clip)
    assert callable(ffmpeg_client.probe_duration)
    assert callable(b2_client.upload_path)
    assert callable(b2_client.delete_prefix)
    assert callable(manifest.update_archive)
    # upload_path takes (local_path, key, content_type)
    params = list(inspect.signature(b2_client.upload_path).parameters)
    assert params[:2] == ["local_path", "key"]
