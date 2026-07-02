from collections.abc import Callable

import anthropic
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .ai import ask_project, get_mix_feedback
from .analysis import analyze_audio
from .daw import parse_project
from .findings import derive_findings
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


@app.post("/api/analyze")
async def analyze(file: UploadFile) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    try:
        metrics, arrangement = analyze_audio(data, file.filename or "upload")
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
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    try:
        return {"project": parse_project(data, file.filename or "project")}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=422, detail=f"Could not parse '{file.filename}'."
        )


@app.post("/api/sample")
async def sample(file: UploadFile) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    try:
        return {"sample": sample_features(data, file.filename or "sample")}
    except Exception:
        raise HTTPException(
            status_code=422,
            detail=f"Could not decode '{file.filename}' as audio.",
        )


@app.post("/api/feedback")
def feedback(body: FeedbackRequest) -> dict:
    if not body.tracks:
        raise HTTPException(status_code=400, detail="No tracks provided.")
    return _call_ai(lambda: {"feedback": get_mix_feedback(body.tracks)})


@app.post("/api/ask")
def ask(body: AskRequest) -> dict:
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Empty question.")
    if body.project is None and not body.tracks:
        raise HTTPException(
            status_code=400,
            detail="Nothing to ask about yet — upload audio or a project file first.",
        )
    return _call_ai(
        lambda: {"answer": ask_project(body.question, body.project, body.tracks)}
    )
