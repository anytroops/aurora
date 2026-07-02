"""Deterministic engineering findings derived from analysis metrics.

These run without any AI so the app degrades gracefully when no API key is
configured; the AI layer narrates on top of them.
"""

STREAMING_TARGET_LUFS = -14.0


def derive_findings(m: dict) -> list[dict]:
    findings: list[dict] = []

    def add(severity: str, title: str, detail: str) -> None:
        findings.append({"severity": severity, "title": title, "detail": detail})

    if m["clipped_samples"] > 8:
        add(
            "high",
            "Clipping detected",
            f"{m['clipped_samples']} samples at full scale (longest run "
            f"{m['max_clip_run']}). Pull the output ceiling down or reduce gain "
            "before the final limiter.",
        )

    lufs = m.get("lufs_integrated")
    if lufs is not None:
        if lufs > -9:
            add(
                "medium",
                "Very hot master",
                f"Integrated loudness is {lufs} LUFS. Streaming services normalize "
                f"to ~{STREAMING_TARGET_LUFS} LUFS, so the extra limiting buys no "
                "loudness on playback — only lost dynamics.",
            )
        elif lufs < -20:
            add(
                "low",
                "Quiet program level",
                f"Integrated loudness is {lufs} LUFS vs the ~{STREAMING_TARGET_LUFS} "
                "LUFS streaming target. Fine for a stem; low for a finished master.",
            )

    if m["crest_factor_db"] < 6:
        add(
            "medium",
            "Heavily limited dynamics",
            f"Crest factor is {m['crest_factor_db']} dB (peak-to-RMS). Under ~6 dB "
            "usually means the limiter is flattening transients.",
        )

    corr = m.get("correlation")
    if corr is not None and corr < 0.2:
        add(
            "high",
            "Possible phase problem",
            f"L/R correlation is {corr}. Content this decorrelated can cancel "
            "badly when summed to mono — check phase on doubled or widened parts.",
        )

    width = m.get("stereo_width")
    if width is not None and width > 1.2:
        add(
            "low",
            "Very wide stereo image",
            f"Side/mid energy ratio is {width}. Verify mono compatibility.",
        )

    bands = m["spectral_balance_pct"]
    if bands["low_mid"] > 30:
        add(
            "medium",
            "Low-mid buildup (mud)",
            f"{bands['low_mid']}% of spectral energy sits in 250–500 Hz. A broad "
            "cut around 300 Hz on the dense elements usually cleans this up.",
        )
    if bands["sub"] > 35:
        add(
            "medium",
            "Excessive sub energy",
            f"{bands['sub']}% of energy is below 60 Hz. Check for unfiltered sub "
            "rumble on non-bass elements.",
        )
    if bands["high"] + bands["high_mid"] < 5:
        add(
            "low",
            "Dark top end",
            f"Only {round(bands['high'] + bands['high_mid'], 2)}% of energy above "
            "2 kHz. May be intentional; if not, look at HF loss from stacked "
            "processing.",
        )

    if m["noise_floor_db"] > -45 and m["rms_dbfs"] - m["noise_floor_db"] < 20:
        add(
            "low",
            "High noise floor",
            f"Quiet-section level is ~{m['noise_floor_db']} dBFS, within 20 dB of "
            "the program RMS. Consider gating or a cleaner take.",
        )

    return findings
