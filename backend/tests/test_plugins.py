import pytest

from app.plugins import categorize, categorized_chains, derive_chain_findings


@pytest.mark.parametrize(
    "device,expected",
    [
        ("VST3: Pro-Q 3 (FabFilter)", "eq"),
        ("EQ Eight", "eq"),
        ("VST: ReaComp (Cockos)", "compressor"),
        ("CLA-2A Compressor (Waves)", "compressor"),
        ("Glue Compressor", "compressor"),
        ("VST3: Pro-L 2 (FabFilter)", "limiter"),
        ("ValhallaVintageVerb", "reverb"),
        ("Saturator", "saturation"),
        ("Decapitator", "saturation"),
        ("Serum", "synth"),
        ("Drum Rack", "sampler"),
        ("Auto-Tune Pro", "pitch"),
        ("Utility", "utility"),
        ("Some Unknown Widget", "other"),
    ],
)
def test_device_categorization(device, expected):
    assert categorize(device) == expected


def test_limiter_wins_over_compressor_in_ambiguous_names():
    # "Pro-L 2" would also match nothing else, but a name carrying both words
    # must resolve to limiter because limiter patterns are checked first.
    assert categorize("Maximizer / Compressor Bundle") == "limiter"


def test_categorized_chains_preserve_order(parsed_reaper):
    chains = categorized_chains(parsed_reaper)
    drums = next(c for c in chains if c["track"] == "Drums")
    assert [d["category"] for d in drums["devices"]] == ["eq", "compressor"]
    assert drums["devices"][0]["name"] == "VST3: Pro-Q 3 (FabFilter)"


def chain_project(*tracks: dict) -> dict:
    """Build a minimal project dict from (name, devices, [type], [clips])."""
    return {
        "tracks": [
            {
                "name": t["name"],
                "type": t.get("type", "track"),
                "devices": t["devices"],
                "clip_count": t.get("clip_count", 1),
            }
            for t in tracks
        ]
    }


def titles(project: dict) -> list[str]:
    return [f["title"] for f in derive_chain_findings(project)]


def test_processing_after_limiter_flagged():
    p = chain_project({"name": "Drum Bus", "devices": ["Pro-L 2", "Pro-Q 3"]})
    finding = next(
        f for f in derive_chain_findings(p) if f["title"].startswith("Processing after")
    )
    assert finding["severity"] == "medium"
    assert "eq" in finding["detail"]


def test_limiter_last_in_chain_is_clean():
    p = chain_project({"name": "Master", "devices": ["Pro-Q 3", "Pro-L 2"]})
    assert not any(t.startswith("Processing after") for t in titles(p))


def test_stacked_compressors_flagged():
    p = chain_project({"name": "Vox", "devices": ["ReaComp", "CLA-2A Compressor"]})
    assert "Stacked compressors on 'Vox'" in titles(p)


def test_single_compressor_is_clean():
    p = chain_project({"name": "Vox", "devices": ["ReaComp"]})
    assert not any("Stacked" in t for t in titles(p))


def test_unprocessed_track_with_clips_flagged():
    p = chain_project({"name": "Bass DI", "devices": [], "clip_count": 2})
    assert "Unprocessed track 'Bass DI'" in titles(p)


def test_empty_track_without_clips_is_not_flagged():
    p = chain_project({"name": "Spare", "devices": [], "clip_count": 0})
    assert titles(p) == []


def test_reverb_sprawl_needs_three_insert_tracks():
    two = chain_project(
        {"name": "A", "devices": ["ValhallaRoom"]},
        {"name": "B", "devices": ["ValhallaPlate"]},
    )
    assert not any("Reverb inserted" in t for t in titles(two))

    three = chain_project(
        {"name": "A", "devices": ["ValhallaRoom"]},
        {"name": "B", "devices": ["ValhallaPlate"]},
        {"name": "C", "devices": ["ValhallaVintageVerb"]},
    )
    assert "Reverb inserted on 3 tracks" in titles(three)


def test_reverb_on_return_track_is_not_sprawl():
    p = chain_project(
        {"name": "A-Verb", "devices": ["Reverb"], "type": "return"},
        {"name": "B-Verb", "devices": ["Reverb"], "type": "return"},
        {"name": "C-Verb", "devices": ["Reverb"], "type": "return"},
    )
    assert not any("Reverb inserted" in t for t in titles(p))


def test_limiter_on_bus_does_not_trigger_single_track_advice():
    p = chain_project(
        {"name": "Drum Bus", "devices": ["Pro-L 2"], "type": "group"},
        {"name": "Other", "devices": ["Pro-Q 3"]},
    )
    assert not any("Limiter on individual track" in t for t in titles(p))
