import numpy as np

from app.arrangement import CURVE_POINTS, analyze_arrangement
from tests.conftest import SR


def test_sections_and_transitions_track_the_structure(structured_song):
    a = analyze_arrangement(structured_song, SR)

    # Four 15s blocks: quiet, loud, quiet, loud
    assert len(a["sections"]) == 4
    starts = [s["start"] for s in a["sections"]]
    assert starts == sorted(starts)
    for expected, section in zip([0, 15, 30, 45], a["sections"]):
        assert abs(section["start"] - expected) < 1.0

    levels = [s["level"] for s in a["sections"]]
    assert levels[1] == "high" and levels[2] == "low"

    # Boundaries should register as a lift, a breakdown, then a lift
    kinds = [t["kind"] for t in a["transitions"]]
    assert kinds == ["lift", "breakdown", "lift"]
    assert a["transitions"][1]["delta_db"] < -4
    assert a["transitions"][2]["delta_db"] > 4


def test_energy_curve_is_bounded_and_ordered(structured_song):
    curve = analyze_arrangement(structured_song, SR)["energy_curve"]
    # Integer striding can overshoot the target by up to 2x, but the curve must
    # stay bounded rather than scaling with track length (1292 raw frames here).
    assert 0 < len(curve) <= 2 * CURVE_POINTS
    times = [p["t"] for p in curve]
    assert times == sorted(times)
    assert times[0] >= 0
    # The loud section must read hotter than the intro
    intro = [p["db"] for p in curve if p["t"] < 14]
    drop = [p["db"] for p in curve if 16 < p["t"] < 29]
    assert max(drop) > max(intro)


def test_steady_signal_produces_no_transitions():
    t = np.linspace(0, 40, SR * 40, endpoint=False)
    steady = 0.3 * np.sin(2 * np.pi * 440 * t)
    assert analyze_arrangement(steady, SR)["transitions"] == []


def test_short_clip_skips_segmentation_but_still_returns_a_curve():
    t = np.linspace(0, 2.0, int(SR * 2.0), endpoint=False)
    a = analyze_arrangement(0.3 * np.sin(2 * np.pi * 440 * t), SR)
    assert a["sections"] == []
    assert a["transitions"] == []
    assert len(a["energy_curve"]) > 0


def test_silence_does_not_crash():
    a = analyze_arrangement(np.zeros(SR * 30), SR)
    assert all(p["db"] <= -79 for p in a["energy_curve"])
