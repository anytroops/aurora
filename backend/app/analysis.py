"""DSP analysis for uploaded audio: loudness, dynamics, stereo, spectrum, tempo, key."""

import io
import math
import tempfile

import librosa
import numpy as np
import pyloudnorm
import soundfile as sf

from .arrangement import analyze_arrangement

# Band edges in Hz; "high" runs to Nyquist
BANDS = [
    ("sub", 20, 60),
    ("bass", 60, 250),
    ("low_mid", 250, 500),
    ("mid", 500, 2000),
    ("high_mid", 2000, 6000),
    ("high", 6000, None),
]

# Krumhansl-Schmuckler key profiles
_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _db(x: float, floor: float = -120.0) -> float:
    if x <= 0:
        return floor
    return max(20.0 * math.log10(x), floor)


def _load(data: bytes, filename: str) -> tuple[np.ndarray, int]:
    """Return (samples, channels) float32 array and sample rate."""
    try:
        y, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=True)
        return y, sr
    except Exception:
        # Formats soundfile can't parse directly (some mp3/m4a) go through librosa
        suffix = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
            tmp.write(data)
            tmp.flush()
            y, sr = librosa.load(tmp.name, sr=None, mono=False)
        if y.ndim == 1:
            y = y[np.newaxis, :]
        return y.T.astype("float32"), int(sr)


def _estimate_key(y: np.ndarray, sr: int) -> str | None:
    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
        best, best_score = None, -2.0
        for shift in range(12):
            rolled = np.roll(chroma, -shift)
            for profile, mode in ((_MAJOR, "major"), (_MINOR, "minor")):
                score = np.corrcoef(rolled, profile)[0, 1]
                if score > best_score:
                    best_score, best = score, f"{_NOTES[shift]} {mode}"
        return best
    except Exception:
        return None


def _estimate_tempo(y: np.ndarray, sr: int) -> float | None:
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        tempo = float(np.atleast_1d(tempo)[0])
        return round(tempo, 1) if tempo > 0 else None
    except Exception:
        return None


def analyze_audio(data: bytes, filename: str) -> tuple[dict, dict]:
    """Return (metrics, arrangement) for the given audio file."""
    y, sr = _load(data, filename)
    n_samples, n_channels = y.shape
    duration = n_samples / sr
    mono = y.mean(axis=1)

    peak = float(np.abs(y).max())
    rms = float(np.sqrt(np.mean(mono**2)))
    peak_db = round(_db(peak), 2)
    rms_db = round(_db(rms), 2)
    crest_db = round(peak_db - rms_db, 2)

    # Integrated loudness (needs ≥ 400 ms of audio)
    lufs = None
    if duration >= 0.5:
        try:
            loudness = pyloudnorm.Meter(sr).integrated_loudness(y)
            if math.isfinite(loudness):
                lufs = round(float(loudness), 2)
        except Exception:
            pass

    # Clipping: samples at/near full scale, and the longest consecutive run
    clip_mask = np.abs(y).max(axis=1) >= 0.9995
    clipped_samples = int(clip_mask.sum())
    max_run = 0
    if clipped_samples:
        idx = np.flatnonzero(clip_mask)
        splits = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
        max_run = max(len(s) for s in splits)

    # Stereo image
    correlation = None
    stereo_width = None
    if n_channels == 2:
        left, right = y[:, 0], y[:, 1]
        if left.std() > 0 and right.std() > 0:
            correlation = round(float(np.corrcoef(left, right)[0, 1]), 3)
        mid = (left + right) / 2
        side = (left - right) / 2
        mid_rms = float(np.sqrt(np.mean(mid**2)))
        side_rms = float(np.sqrt(np.mean(side**2)))
        if mid_rms > 0:
            stereo_width = round(side_rms / mid_rms, 3)

    # Spectral balance: share of total power per band
    stft = np.abs(librosa.stft(mono, n_fft=4096)) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)
    power_per_bin = stft.mean(axis=1)
    total_power = float(power_per_bin.sum()) or 1.0
    bands = {}
    for name, lo, hi in BANDS:
        hi = hi if hi is not None else sr / 2
        mask = (freqs >= lo) & (freqs < hi)
        bands[name] = round(100.0 * float(power_per_bin[mask].sum()) / total_power, 2)

    centroid = float(librosa.feature.spectral_centroid(y=mono, sr=sr).mean())

    # Noise floor: 10th percentile of frame RMS
    frame_rms = librosa.feature.rms(y=mono)[0]
    noise_floor_db = round(_db(float(np.percentile(frame_rms, 10))), 2)

    metrics = {
        "filename": filename,
        "duration_s": round(duration, 3),
        "sample_rate": sr,
        "channels": n_channels,
        "peak_dbfs": peak_db,
        "rms_dbfs": rms_db,
        "crest_factor_db": crest_db,
        "lufs_integrated": lufs,
        "clipped_samples": clipped_samples,
        "max_clip_run": max_run,
        "correlation": correlation,
        "stereo_width": stereo_width,
        "spectral_balance_pct": bands,
        "spectral_centroid_hz": round(centroid, 1),
        "noise_floor_db": noise_floor_db,
        "tempo_bpm": _estimate_tempo(mono, sr),
        "key_estimate": _estimate_key(mono, sr),
    }
    return metrics, analyze_arrangement(mono, sr)
