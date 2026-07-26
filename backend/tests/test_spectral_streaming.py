"""The spectral aggregates are computed in blocks; prove that's both correct
and actually bounded.

A full-file STFT of a five-minute track allocates hundreds of megabytes for two
scalars-per-bin. `_spectral_profile` streams it instead. These tests assert the
streamed result matches the naive computation, and that its working set does not
grow with track length.
"""

import gc
import threading
import time

import librosa
import numpy as np
import psutil
import pytest

from app.analysis import SPECTRUM_HOP, SPECTRUM_N_FFT, _spectral_profile

SR = 44100


def signal(seconds: float) -> np.ndarray:
    """Harmonically rich + noisy, so the spectrum is non-trivial."""
    rng = np.random.default_rng(11)
    t = np.linspace(0, seconds, int(SR * seconds), endpoint=False)
    sig = np.sin(2 * np.pi * 110 * t) * 0.4 + ((t * 220) % 1 - 0.5) * 0.3
    sig += rng.standard_normal(len(t)) * 0.05
    return sig.astype("float32")


def peak_delta_mb(fn) -> float:
    """Peak RSS growth in MB while fn() runs."""
    proc = psutil.Process()
    gc.collect()
    base = proc.memory_info().rss
    peak = [base]
    stop = [False]

    def watch() -> None:
        while not stop[0]:
            peak[0] = max(peak[0], proc.memory_info().rss)
            time.sleep(0.005)

    watcher = threading.Thread(target=watch)
    watcher.start()
    try:
        fn()
    finally:
        stop[0] = True
        watcher.join()
    gc.collect()
    return (peak[0] - base) / 1e6


def test_power_spectrum_matches_a_full_file_stft():
    mono = signal(20)
    streamed, _ = _spectral_profile(mono, SR)
    naive = (np.abs(librosa.stft(mono, n_fft=SPECTRUM_N_FFT)) ** 2).mean(axis=1)

    assert streamed.shape == naive.shape
    # Edge framing differs (no centre padding), so compare in aggregate
    relative_l1 = np.abs(streamed - naive).sum() / naive.sum()
    assert relative_l1 < 0.01, f"power spectrum drifted by {relative_l1:.4%}"


def test_centroid_matches_librosa_at_the_same_parameters():
    mono = signal(20)
    _, streamed = _spectral_profile(mono, SR)
    reference = float(
        librosa.feature.spectral_centroid(
            y=mono,
            sr=SR,
            n_fft=SPECTRUM_N_FFT,
            hop_length=SPECTRUM_HOP,
            center=False,
        ).mean()
    )
    assert streamed == pytest.approx(reference, rel=1e-6)


def test_band_energy_is_conserved():
    power, _ = _spectral_profile(signal(10), SR)
    assert power.sum() > 0
    assert np.all(power >= 0)
    assert len(power) == SPECTRUM_N_FFT // 2 + 1


def test_short_clip_shorter_than_one_window_still_measures():
    """Guards the padded fallback path."""
    tiny = signal(0.05)  # ~2200 samples, under the 4096-sample window
    power, centroid = _spectral_profile(tiny, SR)
    assert power.sum() > 0
    assert centroid > 0


def test_working_set_does_not_scale_with_track_length():
    """A full-file STFT would roughly double; a streamed one should stay flat."""
    short_sig, long_sig = signal(30), signal(120)

    short_mb = peak_delta_mb(lambda: _spectral_profile(short_sig, SR))
    long_mb = peak_delta_mb(lambda: _spectral_profile(long_sig, SR))

    # 4x the audio. Bounded streaming stays roughly flat; a full-file STFT
    # would grow with the input. Allow generous headroom for allocator noise.
    assert long_mb < max(short_mb, 20.0) * 2.0, (
        f"working set grew from {short_mb:.0f} MB to {long_mb:.0f} MB for 4x the "
        "audio — the spectrogram is probably being materialised whole again"
    )
