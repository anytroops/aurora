"""Plugin intelligence: categorize devices by role and derive chain-level findings.

Categorization is name-based (we have device names from the project file, not
parameter values), which is enough to reason about chain order and redundancy.
"""

# Checked in order; first matching category wins.
CATEGORY_PATTERNS: list[tuple[str, list[str]]] = [
    ("limiter", ["limiter", "maximizer", "pro-l", "brickwall"]),
    ("eq", ["eq", "pro-q", "filter", "tilt"]),
    ("compressor", ["comp", "glue", "1176", "la-2a", "opto", "vca", "squash"]),
    ("gate", ["gate", "expander", "de-esser", "deesser"]),
    ("reverb", ["reverb", "verb", "valhalla", "plate", "hall", "room"]),
    ("delay", ["delay", "echo"]),
    ("saturation", ["saturat", "distort", "drive", "shaper", "decapitator", "tape", "tube", "clip"]),
    ("pitch", ["tune", "melodyne", "pitch", "vocoder"]),
    ("synth", ["operator", "wavetable", "serum", "massive", "sylenth", "diva", "vital", "analog", "synth", "omnisphere"]),
    ("sampler", ["simpler", "sampler", "drum rack", "kontakt", "battery", "drum"]),
    ("utility", ["utility", "gain", "trim", "meter", "spectrum", "scope"]),
]


def categorize(device_name: str) -> str:
    lowered = device_name.lower()
    for category, patterns in CATEGORY_PATTERNS:
        if any(p in lowered for p in patterns):
            return category
    return "other"


def categorized_chains(project: dict) -> list[dict]:
    return [
        {
            "track": t["name"],
            "type": t["type"],
            "devices": [{"name": d, "category": categorize(d)} for d in t["devices"]],
        }
        for t in project["tracks"]
    ]


def derive_chain_findings(project: dict) -> list[dict]:
    findings: list[dict] = []

    def add(severity: str, title: str, detail: str) -> None:
        findings.append({"severity": severity, "title": title, "detail": detail})

    reverb_insert_tracks: list[str] = []
    multi_track = len(project["tracks"]) > 1

    for t in project["tracks"]:
        name = t["name"]
        cats = [categorize(d) for d in t["devices"]]
        is_bus = t.get("type") in ("return", "group")

        if not is_bus:
            if "reverb" in cats:
                reverb_insert_tracks.append(name)
            if t.get("clip_count", 0) > 0 and not t["devices"]:
                add(
                    "low",
                    f"Unprocessed track '{name}'",
                    "Has clips but no processing. Fine for a clean DI or a "
                    "placeholder — worth confirming it isn't just forgotten.",
                )

        n_comp = cats.count("compressor")
        if n_comp >= 2:
            add(
                "low",
                f"Stacked compressors on '{name}'",
                f"{n_comp} compressors in series. Legitimate as serial "
                "compression, but check the combined gain reduction — two "
                "working hard is a common over-compression source.",
            )

        if "limiter" in cats:
            after = set(cats[cats.index("limiter") + 1 :]) & {
                "eq",
                "compressor",
                "saturation",
            }
            if after:
                add(
                    "medium",
                    f"Processing after the limiter on '{name}'",
                    f"{', '.join(sorted(after))} follows the limiter, which can "
                    "push peaks back above its ceiling. The limiter usually "
                    "goes last in the chain.",
                )
            if not is_bus and multi_track:
                add(
                    "low",
                    f"Limiter on individual track '{name}'",
                    "Common on the master bus; on a single track a compressor "
                    "is usually the better tool unless you're clipping peaks "
                    "deliberately.",
                )

    if len(reverb_insert_tracks) >= 3:
        add(
            "low",
            f"Reverb inserted on {len(reverb_insert_tracks)} tracks",
            f"({', '.join(reverb_insert_tracks[:5])}) — a shared reverb return "
            "usually glues the space together better and saves CPU.",
        )

    return findings
