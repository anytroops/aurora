"""Endpoint contract tests.

No Anthropic credentials are configured in CI, so the AI-backed endpoints are
asserted on their documented degraded behavior (503, or a populated
`*_error` field) rather than on model output.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

AI_UNAVAILABLE = "No Anthropic API credentials configured"


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_analyze_returns_metrics_findings_arrangement(clipped_mix):
    r = client.post("/api/analyze", files={"file": ("hot.wav", clipped_mix, "audio/wav")})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"metrics", "findings", "arrangement"}
    assert body["metrics"]["clipped_samples"] > 0
    assert any(f["title"] == "Clipping detected" for f in body["findings"])


def test_analyze_rejects_empty_and_undecodable_files():
    empty = client.post("/api/analyze", files={"file": ("x.wav", b"", "audio/wav")})
    assert empty.status_code == 400

    junk = client.post("/api/analyze", files={"file": ("x.wav", b"not audio", "audio/wav")})
    assert junk.status_code == 422


def test_project_endpoint_parses_reaper(reaper_bytes):
    r = client.post("/api/project", files={"file": ("t.rpp", reaper_bytes, "text/plain")})
    assert r.status_code == 200
    assert r.json()["project"]["track_count"] == 3


def test_project_endpoint_rejects_unknown_format():
    r = client.post("/api/project", files={"file": ("t.flp", b"data", "text/plain")})
    assert r.status_code == 422
    assert "Unsupported project format" in r.json()["detail"]


def test_sample_endpoint_returns_vector(kick_sample):
    r = client.post("/api/sample", files={"file": ("kick.wav", kick_sample, "audio/wav")})
    assert r.status_code == 200
    assert len(r.json()["sample"]["vector"]) == 30


def test_ask_requires_a_question():
    assert client.post("/api/ask", json={"question": "  "}).status_code == 400


def test_ask_session_mode_requires_session_data():
    r = client.post("/api/ask", json={"question": "what tracks?", "mode": "session"})
    assert r.status_code == 400
    assert "upload audio or a project file" in r.json()["detail"]


def test_ask_dsp_mode_needs_no_session_data():
    """DSP-code mode must reach the AI layer, not the session-data guard."""
    r = client.post(
        "/api/ask", json={"question": "Write a biquad filter", "mode": "dsp_code"}
    )
    assert r.status_code == 503
    assert AI_UNAVAILABLE in r.json()["detail"]


def test_feedback_requires_tracks():
    assert client.post("/api/feedback", json={"tracks": []}).status_code == 400


def test_agents_are_listed_with_their_requirements():
    agents = client.get("/api/agents").json()["agents"]
    ids = {a["id"] for a in agents}
    assert ids == {"mixing", "mastering", "arrangement", "session_prep"}
    assert all(a["needs"] in {"tracks", "project"} for a in agents)


def test_unknown_agent_rejected():
    r = client.post("/api/agent-run", json={"agent": "nonexistent"})
    assert r.status_code == 400
    assert "Unknown agent" in r.json()["detail"]


def test_agent_input_requirements_enforced(parsed_reaper):
    needs_audio = client.post("/api/agent-run", json={"agent": "mixing"})
    assert needs_audio.status_code == 400
    assert "needs analyzed audio" in needs_audio.json()["detail"]

    needs_project = client.post("/api/agent-run", json={"agent": "session_prep"})
    assert needs_project.status_code == 400
    assert "needs a parsed project" in needs_project.json()["detail"]


def test_agent_pipeline_runs_deterministic_steps_without_credentials(parsed_reaper):
    """The rule-based pipeline must complete even when the AI pass can't."""
    r = client.post(
        "/api/agent-run", json={"agent": "session_prep", "project": parsed_reaper}
    )
    assert r.status_code == 200
    body = r.json()
    assert [s["name"] for s in body["steps"]] == [
        "Gather inputs",
        "Rule scan",
        "Compile brief",
        "Agent pass",
    ]
    assert body["report"] is None
    assert AI_UNAVAILABLE in body["report_error"]


def test_plugin_review_ships_rule_findings_without_credentials(parsed_reaper):
    r = client.post("/api/plugin-review", json={"project": parsed_reaper})
    assert r.status_code == 200
    body = r.json()
    assert body["chains"][0]["devices"][0]["category"] == "eq"
    assert any(f["title"].startswith("Unprocessed track") for f in body["findings"])
    assert body["review"] is None
    assert AI_UNAVAILABLE in body["review_error"]


def test_plugin_review_rejects_empty_project():
    assert client.post("/api/plugin-review", json={"project": {"tracks": []}}).status_code == 400


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/api/feedback", {"tracks": [{"metrics": {}, "findings": []}]}),
        ("/api/ask", {"question": "hi", "tracks": [{"metrics": {}}]}),
    ],
)
def test_ai_endpoints_degrade_to_503_without_credentials(path, payload):
    r = client.post(path, json=payload)
    assert r.status_code == 503
    assert AI_UNAVAILABLE in r.json()["detail"]
