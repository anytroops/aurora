from app.findings import derive_findings
from tests.conftest import metrics_stub


def titles(metrics: dict) -> list[str]:
    return [f["title"] for f in derive_findings(metrics)]


def test_clean_mix_has_no_findings():
    assert derive_findings(metrics_stub()) == []


def test_clipping_flagged_high():
    findings = derive_findings(metrics_stub(clipped_samples=5000, max_clip_run=60))
    clipping = next(f for f in findings if f["title"] == "Clipping detected")
    assert clipping["severity"] == "high"
    assert "5000" in clipping["detail"]


def test_isolated_clipped_samples_tolerated():
    # A handful of full-scale samples is not worth a finding
    assert "Clipping detected" not in titles(metrics_stub(clipped_samples=4))


def test_hot_and_quiet_masters_flagged():
    assert "Very hot master" in titles(metrics_stub(lufs_integrated=-4.0))
    assert "Quiet program level" in titles(metrics_stub(lufs_integrated=-25.0))
    assert "Very hot master" not in titles(metrics_stub(lufs_integrated=-14.0))


def test_missing_loudness_is_not_a_finding():
    assert not [t for t in titles(metrics_stub(lufs_integrated=None)) if "master" in t]


def test_over_limited_dynamics_flagged():
    assert "Heavily limited dynamics" in titles(metrics_stub(crest_factor_db=4.0))
    assert "Heavily limited dynamics" not in titles(metrics_stub(crest_factor_db=8.0))


def test_phase_problem_flagged_high():
    findings = derive_findings(metrics_stub(correlation=-0.6))
    phase = next(f for f in findings if f["title"] == "Possible phase problem")
    assert phase["severity"] == "high"


def test_mono_file_skips_stereo_rules():
    mono = metrics_stub(channels=1, correlation=None, stereo_width=None)
    assert "Possible phase problem" not in titles(mono)
    assert "Very wide stereo image" not in titles(mono)


def test_spectral_balance_rules():
    assert "Low-mid buildup (mud)" in titles(
        metrics_stub(spectral_balance_pct={**metrics_stub()["spectral_balance_pct"], "low_mid": 40.0})
    )
    assert "Excessive sub energy" in titles(
        metrics_stub(spectral_balance_pct={**metrics_stub()["spectral_balance_pct"], "sub": 45.0})
    )
    dark = {**metrics_stub()["spectral_balance_pct"], "high_mid": 1.0, "high": 1.0}
    assert "Dark top end" in titles(metrics_stub(spectral_balance_pct=dark))


def test_noise_floor_needs_both_conditions():
    # Loud floor AND little separation from program level
    assert "High noise floor" in titles(metrics_stub(noise_floor_db=-30.0, rms_dbfs=-14.0))
    # Loud floor but plenty of separation → no finding
    assert "High noise floor" not in titles(metrics_stub(noise_floor_db=-40.0, rms_dbfs=-5.0))


def test_findings_carry_valid_severities():
    findings = derive_findings(
        metrics_stub(clipped_samples=9000, crest_factor_db=3.0, correlation=-0.9)
    )
    assert len(findings) >= 3
    assert all(f["severity"] in {"high", "medium", "low"} for f in findings)
    assert all(f["title"] and f["detail"] for f in findings)
