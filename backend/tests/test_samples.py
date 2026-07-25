import math

from app.samples import sample_features


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def test_fingerprint_shape_and_metadata(kick_sample):
    s = sample_features(kick_sample, "kick.wav")
    assert s["filename"] == "kick.wav"
    assert s["duration_s"] > 0
    # 13 MFCC means + 13 stds + 4 spectral scalars
    assert len(s["vector"]) == 30
    assert all(isinstance(v, float) for v in s["vector"])


def test_identical_audio_fingerprints_identically(kick_sample):
    a = sample_features(kick_sample, "a.wav")["vector"]
    b = sample_features(kick_sample, "b.wav")["vector"]
    assert cosine(a, b) > 0.999


def test_similar_sources_rank_above_different_ones(kick_sample, kick_sample_2, hat_sample):
    kick = sample_features(kick_sample, "kick.wav")["vector"]
    other_kick = sample_features(kick_sample_2, "kick2.wav")["vector"]
    hat = sample_features(hat_sample, "hat.wav")["vector"]

    assert cosine(kick, other_kick) > cosine(kick, hat)
    # The two kicks should be a strong match, the hat clearly not
    assert cosine(kick, other_kick) > 0.9
    assert cosine(kick, hat) < 0.6


def test_fingerprint_is_level_invariant(kick_sample):
    """Halving the gain must not change the timbre fingerprint much.

    This is why MFCC coefficient 0 is dropped — it tracks loudness.
    """
    import io

    import numpy as np
    import soundfile as sf

    y, sr = sf.read(io.BytesIO(kick_sample), dtype="float32", always_2d=True)
    buf = io.BytesIO()
    sf.write(buf, (y * 0.5).astype("float32"), sr, format="WAV", subtype="PCM_16")

    loud = sample_features(kick_sample, "loud.wav")["vector"]
    quiet = sample_features(buf.getvalue(), "quiet.wav")["vector"]
    assert cosine(loud, quiet) > 0.95
