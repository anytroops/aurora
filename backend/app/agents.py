"""Autonomous agents: multi-step analysis pipelines with specialized AI passes.

Each agent runs a deterministic pipeline (gather → rule scan → brief) whose
steps are logged and returned, then hands the compiled brief to Claude with
an agent-specific charter. The deterministic steps always complete; the AI
pass degrades to an error note without credentials.
"""

import json

import anthropic
from anthropic import Anthropic

from .ai import MODEL
from .plugins import categorized_chains, derive_chain_findings

AGENT_SPECS: dict[str, dict] = {
    "mixing": {
        "label": "Mixing Agent",
        "needs": "tracks",
        "charter": (
            "You are an autonomous mixing engineer. Deliverable: a mix action "
            "plan. Work through: level balance and headroom, spectral masking "
            "risks between elements, EQ moves (frequency + dB starting "
            "points), compression settings per source, stereo image and mono "
            "compatibility. Prioritize by audible impact."
        ),
    },
    "mastering": {
        "label": "Mastering Agent",
        "needs": "tracks",
        "charter": (
            "You are an autonomous mastering engineer. Deliverable: a "
            "mastering chain plan for this material. Work through: integrated "
            "loudness vs streaming targets (-14 LUFS) and club/CD contexts, "
            "true-peak ceiling, dynamics (crest factor budget), tonal balance "
            "corrections, stereo width treatment, and a recommended chain "
            "order with starting settings. State what should NOT be done to "
            "this material."
        ),
    },
    "arrangement": {
        "label": "Arrangement Agent",
        "needs": "tracks",
        "charter": (
            "You are an autonomous arrangement consultant. Deliverable: an "
            "arrangement revision plan. Work through: the energy arc section "
            "by section (use the timestamps), contrast between sections, "
            "transition strength, sustained-energy fatigue risks, and where "
            "to add or strip elements. Reference sections by their times."
        ),
    },
    "session_prep": {
        "label": "Session Prep Agent",
        "needs": "project",
        "charter": (
            "You are an autonomous session-preparation assistant. "
            "Deliverable: a session cleanup checklist. Work through: signal "
            "chain hygiene (ordering, redundancy), routing suggestions "
            "(inserts vs sends), unprocessed or empty tracks, gain staging "
            "risks implied by the chains, and naming/organization. Output a "
            "concrete, ordered checklist the engineer can execute top to "
            "bottom."
        ),
    },
}

AGENT_SYSTEM = """\
You are one of Aurora's autonomous audio engineering agents, executing a
scoped assignment over real session data (DSP measurements, arrangement
structure, parsed DAW project chains — whatever is provided in the brief).

{charter}

Ground every claim in the data provided — cite values, track names, plugin
names, and timestamps. You have measurements and structure, not audio
playback or plugin parameter values; where a decision needs listening or
knob inspection, say so explicitly instead of inventing. Format the
deliverable so it can be executed without re-reading: numbered actions,
most impactful first.\
"""


def run_agent(agent_id: str, tracks: list[dict], project: dict | None) -> dict:
    spec = AGENT_SPECS[agent_id]
    steps: list[dict] = []

    def step(name: str, detail: str) -> None:
        steps.append({"name": name, "detail": detail})

    # Step 1 — gather inputs
    parts = []
    if tracks:
        parts.append(f"{len(tracks)} analyzed track(s)")
    if project:
        parts.append(
            f"project '{project.get('filename', '?')}' "
            f"({project.get('track_count', 0)} tracks)"
        )
    step("Gather inputs", ", ".join(parts) if parts else "no inputs")

    # Step 2 — rule scan
    brief: dict = {"assignment": spec["label"]}
    finding_count = 0
    if tracks:
        brief["audio_analysis"] = tracks
        finding_count += sum(len(t.get("findings", [])) for t in tracks)
    if project:
        chain_findings = derive_chain_findings(project)
        brief["project_chains"] = categorized_chains(project)
        brief["chain_findings"] = chain_findings
        brief["tempo_bpm"] = project.get("tempo_bpm")
        finding_count += len(chain_findings)
    step("Rule scan", f"{finding_count} rule-based finding(s) compiled")

    # Step 3 — compile brief
    brief_json = json.dumps(brief, indent=2)
    step("Compile brief", f"{len(brief_json):,} characters of structured context")

    # Step 4 — AI pass (degrades to an error note; earlier steps still ship)
    report = None
    report_error = None
    try:
        client = Anthropic()
        with client.messages.stream(
            model=MODEL,
            max_tokens=4000,
            thinking={"type": "adaptive"},
            system=AGENT_SYSTEM.format(charter=spec["charter"]),
            messages=[
                {
                    "role": "user",
                    "content": f"Brief:\n\n{brief_json}\n\nExecute your assignment.",
                }
            ],
        ) as stream:
            message = stream.get_final_message()
        report = "".join(b.text for b in message.content if b.type == "text")
        step("Agent pass", f"{spec['label']} report generated")
    except (anthropic.AuthenticationError, TypeError):
        report_error = (
            "No Anthropic API credentials configured. Set ANTHROPIC_API_KEY "
            "(or run `ant auth login`) and restart the backend."
        )
        step("Agent pass", "skipped — no API credentials")
    except anthropic.RateLimitError:
        report_error = "Rate limited — try again shortly."
        step("Agent pass", "failed — rate limited")
    except anthropic.APIStatusError as e:
        report_error = f"Claude API error: {e.message}"
        step("Agent pass", "failed — API error")
    except anthropic.APIConnectionError:
        report_error = "Could not reach the Claude API."
        step("Agent pass", "failed — connection error")

    return {
        "agent": agent_id,
        "label": spec["label"],
        "steps": steps,
        "report": report,
        "report_error": report_error,
    }
