"""Regenerate the README screenshots by driving the real app in headless Chromium.

Prerequisites: the backend running on :8001, the frontend on :5175, and
`playwright install chromium`. All fixture audio and project files are
synthesized here, so nothing binary needs to live in the repo.

    cd backend && .venv/bin/python ../docs/capture_screenshots.py
"""

import os
import tempfile

import numpy as np
import soundfile as sf
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
ASSETS = os.path.join(tempfile.gettempdir(), "aurora_shot_assets")
SR = 22050
rng = np.random.default_rng(7)


# ----------------------------------------------------------------- fixtures

def _segment(dur: float, level: float, kind: str) -> np.ndarray:
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    if kind == "pad":
        sig = np.sin(2 * np.pi * 220 * t) * 0.5 + np.sin(2 * np.pi * 277 * t) * 0.3
    elif kind == "full":
        kick = np.sin(2 * np.pi * 55 * t) * (np.sin(2 * np.pi * 2 * t) > 0.7)
        saw = ((t * 110) % 1 - 0.5) * 0.8
        hats = rng.standard_normal(len(t)) * 0.25 * (np.sin(2 * np.pi * 8 * t) > 0.8)
        sig = kick + saw + hats
    else:
        sig = np.sin(2 * np.pi * 440 * t) * 0.4 * (np.sin(2 * np.pi * 0.5 * t) > 0)
    return sig * level


def _kick(freq: float) -> np.ndarray:
    t = np.linspace(0, 0.6, int(SR * 0.6), endpoint=False)
    return np.sin(2 * np.pi * (freq + 40 * np.exp(-t * 30)) * t) * np.exp(-t * 8) * 0.9


def _hat(decay: float, dur: float = 0.5) -> np.ndarray:
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    return rng.standard_normal(len(t)) * np.exp(-t * decay) * 0.6


def _pad() -> np.ndarray:
    t = np.linspace(0, 2.0, int(SR * 2.0), endpoint=False)
    return (np.sin(2 * np.pi * 330 * t) + np.sin(2 * np.pi * 415 * t)) * 0.3


SESSION_RPP = """<REAPER_PROJECT 0.1 "7.07/macOS-arm64" 1719900000
  TEMPO 128 4 4
  <TRACK {1}
    NAME "Vocal Lead"
    <ITEM
      NAME "vox_comp.wav"
    >
    <FXCHAIN
      <VST "VST3: Pro-Q 3 (FabFilter)" "q.vst3" 0 "" 1
      >
      <VST "VST: ReaComp (Cockos)" "c.dll" 0 "" 2
      >
      <VST "VST3: CLA-2A Compressor (Waves)" "cla.vst3" 0 "" 3
      >
      <VST "VST3: ValhallaRoom (Valhalla DSP)" "vr.vst3" 0 "" 4
      >
    >
  >
  <TRACK {2}
    NAME "Drum Bus"
    <ITEM
      NAME "drums.wav"
    >
    <FXCHAIN
      <VST "VST3: Pro-L 2 (FabFilter)" "l.vst3" 0 "" 5
      >
      <VST "VST3: Pro-Q 3 (FabFilter)" "q.vst3" 0 "" 6
      >
    >
  >
  <TRACK {3}
    NAME "Synth Pad"
    <ITEM
      NAME "pad.wav"
    >
    <FXCHAIN
      <VST3 "VST3: Serum (Xfer Records)" "Serum.vst3" 0 "" 7
      >
      <VST "VST3: ValhallaVintageVerb (Valhalla DSP)" "vv.vst3" 0 "" 8
      >
    >
  >
  <TRACK {4}
    NAME "Bass DI"
    <ITEM
      NAME "bass.wav"
    >
  >
>
"""


def write_assets() -> None:
    os.makedirs(ASSETS, exist_ok=True)
    song = np.concatenate(
        [
            _segment(15, 0.12, "pad"),
            _segment(15, 0.85, "full"),
            _segment(15, 0.18, "sparse"),
            _segment(15, 0.85, "full"),
        ]
    )
    for name, mono in (
        ("mix_v1_hot.wav", np.clip(song * 1.5, -1, 1)),  # driven into the ceiling
        ("mix_v2_fixed.wav", song * 0.45),  # same arrangement, mixed cleaner
    ):
        stereo = np.stack([mono, mono * 0.97], axis=1).astype("float32")
        sf.write(f"{ASSETS}/{name}", stereo, SR)

    for name, sig in {
        "kick_deep.wav": _kick(50),
        "kick_punchy.wav": _kick(58),
        "hat_closed.wav": _hat(60),
        "hat_open.wav": _hat(15, 0.8),
        "pad_warm.wav": _pad(),
    }.items():
        sf.write(f"{ASSETS}/{name}", sig.astype("float32"), SR)

    with open(f"{ASSETS}/session.rpp", "w") as f:
        f.write(SESSION_RPP)


# ----------------------------------------------------------------- capture

def capture() -> None:
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1180, "height": 900}, device_scale_factor=2
        )
        page.goto("http://localhost:5175", wait_until="networkidle")
        page.wait_for_selector('[data-testid="collab-panel"]')

        page.set_input_files(
            '[data-testid="upload-zone"] input[type="file"]',
            [f"{ASSETS}/mix_v1_hot.wav", f"{ASSETS}/mix_v2_fixed.wav"],
        )
        page.wait_for_selector('[data-testid="compare-panel"]', timeout=90_000)
        page.wait_for_timeout(1500)  # let both waveforms finish drawing

        page.set_input_files('[data-testid="project-input"]', f"{ASSETS}/session.rpp")
        page.wait_for_selector('[data-testid="project-tree"]')
        page.click('[data-testid="review-button"]')
        page.wait_for_selector('[data-testid="chain-review"]', timeout=60_000)

        page.set_input_files(
            '[data-testid="sample-input"]',
            [
                f"{ASSETS}/{n}"
                for n in (
                    "kick_deep.wav",
                    "kick_punchy.wav",
                    "hat_closed.wav",
                    "hat_open.wav",
                    "pad_warm.wav",
                )
            ],
        )
        page.wait_for_function(
            "document.querySelectorAll('[data-testid=\"sample-chip\"]').length === 5",
            timeout=90_000,
        )
        page.locator('[data-testid="sample-chip"]').first.click()
        page.wait_for_selector('[data-testid="sample-results"]')

        page.fill('[data-testid="comment-author"]', "sean")
        page.fill(
            '[data-testid="comment-input"]',
            "v2 fixes the clipping — check the low end next",
        )
        page.click('[data-testid="comment-send"]')
        page.wait_for_selector('[data-testid="comment-list"]')
        page.wait_for_timeout(500)

        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(300)
        page.screenshot(path=f"{OUT}/hero.png")

        for testid, name in (
            ("track-card", "analysis"),
            ("project-tree", "project-chains"),
            ("compare-panel", "compare"),
            ("sample-panel", "samples"),
            ("agent-panel", "agents"),
            ("collab-panel", "collab"),
        ):
            page.locator(f'[data-testid="{testid}"]').first.screenshot(
                path=f"{OUT}/{name}.png"
            )
            print("wrote", name)

        browser.close()


if __name__ == "__main__":
    write_assets()
    capture()
    print("screenshots in", OUT)
