import asyncio
import os
from collections.abc import Callable

import anthropic
from fastapi import FastAPI, HTTPException, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .agents import AGENT_SPECS, run_agent
from .ai import ask_project, get_mix_feedback, review_chains
from .analysis import analyze_audio
from .collab import handle_session
from .daw import parse_project
from .findings import derive_findings
from .plugins import categorized_chains, derive_chain_findings
from .samples import sample_features

app = FastAPI(title="Aurora", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175", "http://127.0.0.1:5175"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class FeedbackRequest(BaseModel):
    tracks: list[dict]


class AskRequest(BaseModel):
    question: str
    project: dict | None = None
    tracks: list[dict] = []
    mode: str = "session"  # "session" | "dsp_code"


class PluginReviewRequest(BaseModel):
    project: dict
    tracks: list[dict] = []


class AgentRunRequest(BaseModel):
    agent: str
    project: dict | None = None
    tracks: list[dict] = []


# Analysis peaks at roughly 50x the input size (decoded float arrays, CQT and
# beat-tracking working sets), so an unbounded read is a denial-of-service
# vector: a single large upload can exhaust the machine. Bound the input.
MAX_AUDIO_UPLOAD_MB = int(os.environ.get("AURORA_MAX_AUDIO_MB", "100"))
MAX_PROJECT_UPLOAD_MB = int(os.environ.get("AURORA_MAX_PROJECT_MB", "25"))
_READ_CHUNK = 1 << 20


async def _read_bounded(file: UploadFile, limit_mb: int) -> bytes:
    """Read an upload in chunks, refusing anything over the limit."""
    limit = limit_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(_READ_CHUNK):
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"'{file.filename}' exceeds the {limit_mb} MB upload limit. "
                    "Bounce a shorter excerpt or raise AURORA_MAX_AUDIO_MB."
                ),
            )
        chunks.append(chunk)
    if not total:
        raise HTTPException(status_code=400, detail="Empty file.")
    return b"".join(chunks)


def _call_ai(fn: Callable[[], dict]) -> dict:
    try:
        return fn()
    except (anthropic.AuthenticationError, TypeError):
        # The SDK raises TypeError at request-build time when no credential
        # source (env var, auth token, or ant profile) can be resolved.
        raise HTTPException(
            status_code=503,
            detail=(
                "No Anthropic API credentials configured. Set ANTHROPIC_API_KEY "
                "(or run `ant auth login`) and restart the backend."
            ),
        )
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limited — try again shortly.")
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {e.message}")
    except anthropic.APIConnectionError:
        raise HTTPException(status_code=502, detail="Could not reach the Claude API.")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.websocket("/api/ws/{room_id}")
async def collab_ws(websocket: WebSocket, room_id: str) -> None:
    await handle_session(room_id, websocket)


@app.post("/api/analyze")
async def analyze(file: UploadFile) -> dict:
    data = await _read_bounded(file, MAX_AUDIO_UPLOAD_MB)
    try:
        # librosa work is CPU-bound and takes seconds on a full song; run it off
        # the event loop so concurrent requests and collab sockets keep flowing.
        metrics, arrangement = await asyncio.to_thread(
            analyze_audio, data, file.filename or "upload"
        )
    except Exception:
        raise HTTPException(
            status_code=422,
            detail=f"Could not decode '{file.filename}' as audio.",
        )
    return {
        "metrics": metrics,
        "findings": derive_findings(metrics),
        "arrangement": arrangement,
    }


@app.post("/api/project")
async def project(file: UploadFile) -> dict:
    data = await _read_bounded(file, MAX_PROJECT_UPLOAD_MB)
    try:
        project = await asyncio.to_thread(
            parse_project, data, file.filename or "project"
        )
        return {"project": project}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=422, detail=f"Could not parse '{file.filename}'."
        )


@app.post("/api/sample")
async def sample(file: UploadFile) -> dict:
    data = await _read_bounded(file, MAX_AUDIO_UPLOAD_MB)
    try:
        features = await asyncio.to_thread(
            sample_features, data, file.filename or "sample"
        )
        return {"sample": features}
    except Exception:
        raise HTTPException(
            status_code=422,
            detail=f"Could not decode '{file.filename}' as audio.",
        )


@app.get("/api/agents")
def list_agents() -> dict:
    return {
        "agents": [
            {"id": agent_id, "label": spec["label"], "needs": spec["needs"]}
            for agent_id, spec in AGENT_SPECS.items()
        ]
    }


@app.post("/api/agent-run")
def agent_run(body: AgentRunRequest) -> dict:
    spec = AGENT_SPECS.get(body.agent)
    if spec is None:
        raise HTTPException(status_code=400, detail=f"Unknown agent '{body.agent}'.")
    if spec["needs"] == "tracks" and not body.tracks:
        raise HTTPException(
            status_code=400,
            detail=f"{spec['label']} needs analyzed audio — upload a track first.",
        )
    if spec["needs"] == "project" and body.project is None:
        raise HTTPException(
            status_code=400,
            detail=f"{spec['label']} needs a parsed project — upload an .als/.rpp first.",
        )
    return run_agent(body.agent, body.tracks, body.project)


@app.post("/api/plugin-review")
def plugin_review(body: PluginReviewRequest) -> dict:
    if not body.project.get("tracks"):
        raise HTTPException(status_code=400, detail="Project has no tracks.")
    chains = categorized_chains(body.project)
    findings = derive_chain_findings(body.project)

    # Rule-based results always ship; the AI layer degrades to an error note.
    review = None
    review_error = None
    try:
        review = review_chains(chains, findings, body.tracks)
    except (anthropic.AuthenticationError, TypeError):
        review_error = (
            "No Anthropic API credentials configured. Set ANTHROPIC_API_KEY "
            "(or run `ant auth login`) and restart the backend."
        )
    except anthropic.RateLimitError:
        review_error = "Rate limited — try again shortly."
    except anthropic.APIStatusError as e:
        review_error = f"Claude API error: {e.message}"
    except anthropic.APIConnectionError:
        review_error = "Could not reach the Claude API."

    return {
        "chains": chains,
        "findings": findings,
        "review": review,
        "review_error": review_error,
    }


@app.post("/api/feedback")
def feedback(body: FeedbackRequest) -> dict:
    if not body.tracks:
        raise HTTPException(status_code=400, detail="No tracks provided.")
    return _call_ai(lambda: {"feedback": get_mix_feedback(body.tracks)})


@app.post("/api/ask")
def ask(body: AskRequest) -> dict:
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Empty question.")
    if body.mode == "session" and body.project is None and not body.tracks:
        raise HTTPException(
            status_code=400,
            detail="Nothing to ask about yet — upload audio or a project file first.",
        )
    return _call_ai(
        lambda: {
            "answer": ask_project(
                body.question, body.project, body.tracks, mode=body.mode
            )
        }
    )
