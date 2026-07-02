"""Arrangement analysis: energy over time, section detection, transition events."""

import math

import librosa
import numpy as np

HOP = 1024
MIN_SECTION_DURATION = 20.0  # below this, section detection isn't meaningful
TRANSITION_DELTA_DB = 4.0
CURVE_POINTS = 200


def _db(x: float, floor: float = -80.0) -> float:
    if x <= 0:
        return floor
    return max(20.0 * math.log10(x), floor)


def analyze_arrangement(mono: np.ndarray, sr: int) -> dict:
    duration = len(mono) / sr
    rms = librosa.feature.rms(y=mono, hop_length=HOP)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=HOP)
    rms_db = np.array([_db(float(v)) for v in rms])

    step = max(1, len(rms_db) // CURVE_POINTS)
    energy_curve = [
        {"t": round(float(t), 2), "db": round(float(d), 1)}
        for t, d in zip(times[::step], rms_db[::step])
    ]

    sections: list[dict] = []
    transitions: list[dict] = []
    n_sections = int(np.clip(duration // 15, 2, 10))
    if duration >= MIN_SECTION_DURATION and rms_db.size > n_sections * 4:
        try:
            mfcc = librosa.feature.mfcc(y=mono, sr=sr, hop_length=HOP, n_mfcc=13)
            bounds = librosa.segment.agglomerative(mfcc, n_sections)
            bound_times = librosa.frames_to_time(bounds, sr=sr, hop_length=HOP)
            edges = [float(t) for t in bound_times] + [duration]

            energies = []
            for start, end in zip(edges[:-1], edges[1:]):
                mask = (times >= start) & (times < end)
                energies.append(float(rms_db[mask].mean()) if mask.any() else -80.0)

            lo, hi = np.percentile(energies, [33, 66])
            for (start, end), energy in zip(zip(edges[:-1], edges[1:]), energies):
                level = "low" if energy <= lo else ("high" if energy >= hi else "mid")
                sections.append(
                    {
                        "start": round(start, 2),
                        "end": round(end, 2),
                        "energy_db": round(energy, 1),
                        "level": level,
                    }
                )

            for t in edges[1:-1]:
                before = rms_db[(times >= t - 3) & (times < t)]
                after = rms_db[(times >= t) & (times < t + 3)]
                if before.size and after.size:
                    delta = float(after.mean() - before.mean())
                    if delta >= TRANSITION_DELTA_DB:
                        transitions.append(
                            {"t": round(t, 2), "delta_db": round(delta, 1), "kind": "lift"}
                        )
                    elif delta <= -TRANSITION_DELTA_DB:
                        transitions.append(
                            {"t": round(t, 2), "delta_db": round(delta, 1), "kind": "breakdown"}
                        )
        except Exception:
            pass  # segmentation is best-effort; the energy curve still ships

    return {
        "energy_curve": energy_curve,
        "sections": sections,
        "transitions": transitions,
    }
