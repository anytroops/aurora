"""AI mix feedback: sends computed DSP metrics to Claude for engineering analysis."""

import json
import os

from anthropic import Anthropic

MODEL = os.environ.get("AURORA_MODEL", "claude-opus-4-8")

SYSTEM = """\
You are a senior mix/mastering engineer reviewing measurements from a client's
tracks. You are given real DSP analysis (LUFS, peak/RMS/crest factor, clipping
counts, L/R correlation, stereo width, spectral band energy percentages,
spectral centroid, noise floor, tempo, key) plus any rule-based findings
already flagged.

Ground every observation in the numbers you were given — cite the specific
value when you make a claim. Do not give generic mixing advice that isn't
supported by the measurements. Structure your response as:

1. A one-paragraph overall read of the mix/tracks.
2. Prioritized, concrete actions (most impactful first), each tied to a
   measurement and with a specific starting point (frequency, dB amount,
   or target value).
3. Anything that looks intentional/fine that the producer shouldn't "fix".

Be direct and practical. If measurements are ambiguous, say what to check in
the session rather than guessing.\
"""


ASK_SYSTEM = """\
You are Aurora, an assistant embedded in a music-production analysis tool. You
are given structured data about the user's session: a parsed DAW project
(tracks, devices/plugins per track, clip counts, tempo) and/or DSP
measurements of uploaded audio (LUFS, crest factor, correlation, spectral
balance, etc.).

Answer the user's question grounded strictly in this data — cite the specific
track names, plugin names, and measured values you're relying on. If the data
doesn't contain what's needed to answer, say exactly what's missing instead of
guessing. Keep answers tight and practical.\
"""


def ask_project(question: str, project: dict | None, tracks: list[dict]) -> str:
    client = Anthropic()
    context: dict = {}
    if project:
        context["daw_project"] = project
    if tracks:
        context["audio_analysis"] = tracks
    with client.messages.stream(
        model=MODEL,
        max_tokens=2500,
        thinking={"type": "adaptive"},
        system=ASK_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    "Session data:\n\n"
                    f"{json.dumps(context, indent=2)}\n\n"
                    f"Question: {question}"
                ),
            }
        ],
    ) as stream:
        message = stream.get_final_message()
    return "".join(block.text for block in message.content if block.type == "text")


def get_mix_feedback(tracks: list[dict]) -> str:
    client = Anthropic()  # resolves ANTHROPIC_API_KEY or an `ant auth login` profile
    payload = json.dumps(tracks, indent=2)
    with client.messages.stream(
        model=MODEL,
        max_tokens=4000,
        thinking={"type": "adaptive"},
        system=SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    "Here is the analysis for the uploaded track(s), including "
                    "metrics and rule-based findings:\n\n"
                    f"{payload}\n\nGive me your engineering feedback."
                ),
            }
        ],
    ) as stream:
        message = stream.get_final_message()
    return "".join(block.text for block in message.content if block.type == "text")
