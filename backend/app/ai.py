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

Tracks may also include arrangement data: detected sections with energy
levels, and lift/breakdown transitions over time. When present, also assess
the energy arc — whether transitions create contrast, whether sustained
high-energy stretches risk listener fatigue, and whether quiet sections earn
the next lift. Tie these observations to the section timestamps.

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


PLUGIN_SYSTEM = """\
You are a senior mix engineer reviewing the processing chains of a DAW
session. You are given each track's device chain in order (device names with
inferred categories: eq, compressor, limiter, reverb, saturation, synth,
etc.), rule-based chain findings already flagged, and — when available — DSP
measurements of bounced audio (LUFS, crest factor, spectral balance, ...).

You have device names and order, NOT parameter values. Be honest about that
boundary: reason from what the chain implies (intent, ordering risks,
redundancy) and from the measurements; never invent knob settings. Where a
measurement implicates a chain (e.g. crest factor of 4 dB on a track running
two compressors into a limiter), connect them explicitly.

Structure the review per track: one line on what the chain is apparently
doing, then anything worth changing, with a concrete starting move. End with
the two or three highest-impact changes across the whole session. If a chain
looks deliberate and fine, say so and move on — don't manufacture problems.\
"""


def review_chains(
    chains: list[dict], chain_findings: list[dict], tracks: list[dict]
) -> str:
    client = Anthropic()
    payload: dict = {"chains": chains, "chain_findings": chain_findings}
    if tracks:
        payload["audio_analysis"] = tracks
    with client.messages.stream(
        model=MODEL,
        max_tokens=3000,
        thinking={"type": "adaptive"},
        system=PLUGIN_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    "Session processing chains and context:\n\n"
                    f"{json.dumps(payload, indent=2)}\n\n"
                    "Review the processing."
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
