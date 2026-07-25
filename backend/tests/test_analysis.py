import pytest

from app.analysis import analyze_audio


def test_clean_tone_measurements(clean_tone):
    m, _ = analyze_audio(clean_tone, "tone.wav")
    assert m["channels"] == 2
    assert m["sample_rate"] == 22050
    assert m["duration_s"] == pytest.approx(3.0, abs=0.05)
    # 0.25 amplitude ≈ -12 dBFS peak
    assert m["peak_dbfs"] == pytest.approx(-12.0, abs=0.5)
    # A sine's crest factor is ~3 dB by definition
    assert m["crest_factor_db"] == pytest.approx(3.0, abs=0.5)
    assert m["clipped_samples"] == 0


def test_clipping_is_detected_with_run_length(clipped_mix):
    m, _ = analyze_audio(clipped_mix, "hot.wav")
    assert m["clipped_samples"] > 100
    assert m["max_clip_run"] >= 1
    assert m["peak_dbfs"] == pytest.approx(0.0, abs=0.1)


def test_loudness_is_measured(clean_tone):
    m, _ = analyze_audio(clean_tone, "tone.wav")
    assert m["lufs_integrated"] is not None
    assert -40 < m["lufs_integrated"] < 0


def test_correlated_and_inverted_channels(clean_tone, out_of_phase):
    correlated, _ = analyze_audio(clean_tone, "same.wav")
    assert correlated["correlation"] == pytest.approx(1.0, abs=0.01)

    inverted, _ = analyze_audio(out_of_phase, "flipped.wav")
    assert inverted["correlation"] == pytest.approx(-1.0, abs=0.01)
    # Fully inverted content is pure side energy
    assert inverted["stereo_width"] > 5


def test_spectral_balance_sums_to_full_spectrum(clean_tone):
    m, _ = analyze_audio(clean_tone, "tone.wav")
    assert sum(m["spectral_balance_pct"].values()) == pytest.approx(100.0, abs=0.5)


def test_spectral_balance_follows_content(clipped_mix):
    m, _ = analyze_audio(clipped_mix, "lowend.wav")
    bands = m["spectral_balance_pct"]
    # Content is 55 Hz + 300 Hz, so sub and low-mid must dominate the top bands
    assert bands["sub"] + bands["low_mid"] > bands["high_mid"] + bands["high"]


def test_key_and_tempo_estimated(structured_song):
    from tests.conftest import SR, wav_bytes

    m, _ = analyze_audio(wav_bytes(structured_song, SR), "song.wav")
    assert m["tempo_bpm"] is not None and m["tempo_bpm"] > 0
    assert m["key_estimate"] is not None
    assert m["key_estimate"].split()[-1] in {"major", "minor"}


def test_mono_file_reports_no_stereo_metrics():
    import numpy as np

    from tests.conftest import SR, wav_bytes

    t = np.linspace(0, 1.0, SR, endpoint=False)
    m, _ = analyze_audio(wav_bytes(0.2 * np.sin(2 * np.pi * 440 * t)), "mono.wav")
    assert m["channels"] == 1
    assert m["correlation"] is None
    assert m["stereo_width"] is None


def test_analyze_returns_arrangement_alongside_metrics(clean_tone):
    m, arrangement = analyze_audio(clean_tone, "tone.wav")
    assert m["filename"] == "tone.wav"
    assert set(arrangement) == {"energy_curve", "sections", "transitions"}


def test_undecodable_input_raises():
    with pytest.raises(Exception):
        analyze_audio(b"this is not audio", "fake.wav")
