"""Uploads must be bounded.

Analysis peaks at roughly 50x the input size, so an unbounded read is a
denial-of-service vector rather than a mere inconvenience: one oversized upload
can exhaust the host. These tests assert the limit is enforced before any
decoding happens, and that the limit is configurable.
"""

import pytest
from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)


@pytest.fixture
def tiny_limit(monkeypatch):
    """Shrink the limits so tests don't have to generate 100 MB."""
    monkeypatch.setattr(main, "MAX_AUDIO_UPLOAD_MB", 2)
    monkeypatch.setattr(main, "MAX_PROJECT_UPLOAD_MB", 1)


@pytest.mark.parametrize("path,filename", [("/api/analyze", "big.wav"), ("/api/sample", "big.wav")])
def test_oversized_audio_rejected_with_413(tiny_limit, path, filename):
    payload = b"\0" * (3 * 1024 * 1024)  # 3 MB against a 2 MB limit
    r = client.post(path, files={"file": (filename, payload, "audio/wav")})
    assert r.status_code == 413
    assert "exceeds the 2 MB upload limit" in r.json()["detail"]


def test_oversized_project_rejected_with_413(tiny_limit):
    payload = b"<REAPER_PROJECT 0.1>\n" + b"x" * (2 * 1024 * 1024)
    r = client.post("/api/project", files={"file": ("big.rpp", payload, "text/plain")})
    assert r.status_code == 413
    assert "1 MB upload limit" in r.json()["detail"]


def test_rejection_happens_before_decoding(tiny_limit):
    """Oversized junk must 413, not 422 — i.e. we never tried to decode it."""
    payload = b"definitely not audio" * 200_000  # ~4 MB of garbage
    r = client.post("/api/analyze", files={"file": ("junk.wav", payload, "audio/wav")})
    assert r.status_code == 413


def test_file_at_the_limit_is_accepted(tiny_limit, clean_tone):
    """A legitimate file under the limit still gets analyzed."""
    assert len(clean_tone) < 2 * 1024 * 1024
    r = client.post("/api/analyze", files={"file": ("ok.wav", clean_tone, "audio/wav")})
    assert r.status_code == 200


def test_empty_upload_still_reports_400(tiny_limit):
    r = client.post("/api/analyze", files={"file": ("empty.wav", b"", "audio/wav")})
    assert r.status_code == 400
    assert r.json()["detail"] == "Empty file."


def test_limits_are_environment_configurable(monkeypatch):
    """The defaults are sane, and operators can raise them."""
    assert main.MAX_AUDIO_UPLOAD_MB == 100
    assert main.MAX_PROJECT_UPLOAD_MB == 25

    monkeypatch.setenv("AURORA_MAX_AUDIO_MB", "512")
    import importlib

    reloaded = importlib.reload(main)
    try:
        assert reloaded.MAX_AUDIO_UPLOAD_MB == 512
    finally:
        monkeypatch.delenv("AURORA_MAX_AUDIO_MB")
        importlib.reload(main)
