"""EBU Tech 3341 compliance checks for the integrated-loudness pipeline.

These assert the *whole* measurement chain — WAV decode, channel handling, and
the ITU-R BS.1770-4 gated loudness algorithm — against the published test
signals from the EBU's compliance suite, each of which has a defined expected
result and tolerance. They are the difference between "we call a loudness
library" and "our loudness measurement is verifiably correct".

Reference: EBU Tech 3341, "Loudness Metering: EBU Mode metering to supplement
EBU R 128 loudness normalisation", test signals for integrated loudness.
"""

import io

import numpy as np
import pytest
import soundfile as sf

from app.analysis import analyze_audio

SR = 48000  # EBU test signals are specified at 48 kHz
TOLERANCE_LU = 0.1  # Tech 3341 tolerance for integrated loudness


def sine(dbfs: float, seconds: float, freq: int = 1000) -> np.ndarray:
    """Stereo 1 kHz sine at the given dBFS amplitude, identical in both channels."""
    t = np.linspace(0, seconds, int(SR * seconds), endpoint=False)
    mono = 10 ** (dbfs / 20) * np.sin(2 * np.pi * freq * t)
    return np.stack([mono, mono], axis=1)


def measure(*segments: np.ndarray) -> float:
    """Concatenate segments, encode as float WAV, and run the real pipeline."""
    buf = io.BytesIO()
    # 32-bit float so the quantisation floor can't perturb the -72 dBFS cases
    sf.write(buf, np.concatenate(segments), SR, format="WAV", subtype="FLOAT")
    metrics, _ = analyze_audio(buf.getvalue(), "ebu.wav")
    return metrics["lufs_integrated"]


@pytest.mark.parametrize("level", [-23.0, -33.0])
def test_case_1_and_2_steady_tone(level):
    """A steady 1 kHz stereo tone must read its own dBFS level in LUFS.

    K-weighting is defined so its gain at 1 kHz exactly cancels the -0.691
    offset in BS.1770, which is what makes this identity hold.
    """
    assert measure(sine(level, 20)) == pytest.approx(level, abs=TOLERANCE_LU)


def test_case_3_relative_gate_excludes_quiet_passages():
    """-36 dBFS lead-in/out around a -23 dBFS body must still integrate to -23.

    The relative gate (-10 LU below the ungated level) discards the quiet
    sections entirely; a naive un-gated mean would land well below -23.
    """
    assert measure(sine(-36, 10), sine(-23, 60), sine(-36, 10)) == pytest.approx(
        -23.0, abs=TOLERANCE_LU
    )


def test_case_4_absolute_and_relative_gates_together():
    """Adds -72 dBFS passages, which the absolute gate (-70 LUFS) must drop."""
    assert measure(
        sine(-72, 10), sine(-36, 10), sine(-23, 60), sine(-36, 10), sine(-72, 10)
    ) == pytest.approx(-23.0, abs=TOLERANCE_LU)


def test_case_5_mixed_levels_integrate_to_target():
    """20s @ -26, 20.1s @ -20, 20s @ -26 is specified to integrate to -23.0."""
    assert measure(sine(-26, 20), sine(-20, 20.1), sine(-26, 20)) == pytest.approx(
        -23.0, abs=TOLERANCE_LU
    )


def test_silence_is_reported_as_unmeasurable_not_as_a_number():
    """Fully gated material has no defined loudness; the API must say so.

    pyloudnorm returns -inf here, which would serialise to invalid JSON — the
    pipeline converts it to null instead.
    """
    buf = io.BytesIO()
    sf.write(buf, np.zeros((SR * 2, 2), dtype="float32"), SR, format="WAV")
    metrics, _ = analyze_audio(buf.getvalue(), "silence.wav")
    assert metrics["lufs_integrated"] is None


def test_channel_summation_is_energy_correct():
    """Doubling the channel count at equal level adds ~3 LU, not 6 or 0.

    BS.1770 sums per-channel mean squares, so identical content in two channels
    is +3.01 LU over one. This catches an averaging-vs-summing mistake, which is
    the classic way to get loudness quietly wrong.
    """
    t = np.linspace(0, 20, SR * 20, endpoint=False)
    mono_sig = 10 ** (-23 / 20) * np.sin(2 * np.pi * 1000 * t)

    def as_wav(x):
        buf = io.BytesIO()
        sf.write(buf, x, SR, format="WAV", subtype="FLOAT")
        return analyze_audio(buf.getvalue(), "x.wav")[0]["lufs_integrated"]

    mono = as_wav(mono_sig)
    stereo = as_wav(np.stack([mono_sig, mono_sig], axis=1))
    assert stereo - mono == pytest.approx(3.01, abs=0.1)
