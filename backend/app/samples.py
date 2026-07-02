"""Sample intelligence: compact timbre fingerprints for similarity search.

The vector is MFCC means+stds (timbre) plus normalized spectral-shape
scalars. Similarity between samples is cosine distance over these vectors,
computed client-side so the library lives in the browser session.
"""

import librosa
import numpy as np

from .analysis import _load

FINGERPRINT_SECONDS = 5  # a sample's identity is in its first few seconds


def sample_features(data: bytes, filename: str) -> dict:
    y, sr = _load(data, filename)
    mono = y.mean(axis=1)
    duration = len(mono) / sr
    mono = mono[: sr * FINGERPRINT_SECONDS]

    # Coefficient 0 is effectively loudness and swamps timbre differences —
    # drop it so similarity reflects spectral shape, not level.
    mfcc = librosa.feature.mfcc(y=mono, sr=sr, n_mfcc=14)[1:]
    centroid = float(librosa.feature.spectral_centroid(y=mono, sr=sr).mean())
    rolloff = float(librosa.feature.spectral_rolloff(y=mono, sr=sr).mean())
    zcr = float(librosa.feature.zero_crossing_rate(mono).mean())
    flatness = float(librosa.feature.spectral_flatness(y=mono).mean())

    nyquist = sr / 2
    vector = np.concatenate(
        [
            mfcc.mean(axis=1),
            mfcc.std(axis=1),
            [centroid / nyquist * 20, rolloff / nyquist * 20, zcr * 20, flatness * 20],
        ]
    )

    return {
        "filename": filename,
        "duration_s": round(duration, 3),
        "vector": [round(float(v), 5) for v in vector],
    }
