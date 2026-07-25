"""Record the README demo GIF by driving the real app in headless Chromium.

Frames are captured as PNGs during a scripted walkthrough, then assembled with
Pillow. Requires the backend on :8001, the frontend on :5175, and the fixture
assets from capture_screenshots.py.

    cd backend && .venv/bin/python ../docs/capture_demo.py
"""

import os
import shutil
import tempfile

from PIL import Image
from playwright.sync_api import sync_playwright

from capture_screenshots import ASSETS, write_assets

DOCS = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DOCS, "screenshots", "demo.gif")
FRAMES = os.path.join(tempfile.gettempdir(), "aurora_demo_frames")
WIDTH, HEIGHT = 1000, 680
FRAME_MS = 420  # playback pace


class Recorder:
    def __init__(self, page):
        self.page = page
        self.n = 0

    def frame(self, hold: int = 1) -> None:
        """Capture one frame, repeated `hold` times to pause on it."""
        path = f"{FRAMES}/{self.n:04d}.png"
        self.page.screenshot(path=path)
        self.n += 1
        for _ in range(hold - 1):
            shutil.copy(path, f"{FRAMES}/{self.n:04d}.png")
            self.n += 1

    def frames_until(self, selector: str, timeout_ms: int = 90_000, every: int = 350) -> None:
        """Capture frames while waiting for `selector` to appear."""
        waited = 0
        while waited < timeout_ms:
            if self.page.locator(selector).count():
                break
            self.page.wait_for_timeout(every)
            waited += every
            self.frame()
        self.page.wait_for_selector(selector, timeout=timeout_ms)
        self.frame()


def record() -> None:
    if os.path.isdir(FRAMES):
        shutil.rmtree(FRAMES)
    os.makedirs(FRAMES)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        page.goto("http://localhost:5175", wait_until="networkidle")
        page.wait_for_selector('[data-testid="collab-panel"]')
        rec = Recorder(page)
        rec.frame(hold=3)

        # 1. Analyze a hot mix
        page.set_input_files(
            '[data-testid="upload-zone"] input[type="file"]',
            f"{ASSETS}/mix_v1_hot.wav",
        )
        rec.frames_until('[data-testid="track-card"]')
        page.locator('[data-testid="track-card"]').first.scroll_into_view_if_needed()
        page.wait_for_timeout(900)  # waveform draw
        rec.frame(hold=5)

        # Findings and the arrangement timeline
        page.mouse.wheel(0, 320)
        page.wait_for_timeout(400)
        rec.frame(hold=5)

        # 2. A second bounce unlocks the comparison
        page.set_input_files(
            '[data-testid="upload-zone"] input[type="file"]',
            f"{ASSETS}/mix_v2_fixed.wav",
        )
        rec.frames_until('[data-testid="compare-panel"]')
        page.locator('[data-testid="compare-panel"]').scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        rec.frame(hold=6)

        # 3. Parse a DAW project and review its chains
        page.set_input_files('[data-testid="project-input"]', f"{ASSETS}/session.rpp")
        page.wait_for_selector('[data-testid="project-tree"]')
        page.locator('[data-testid="project-tree"]').scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        rec.frame(hold=4)

        page.click('[data-testid="review-button"]')
        rec.frames_until('[data-testid="chain-review"]', timeout_ms=60_000)
        page.locator('[data-testid="chain-review"]').scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        rec.frame(hold=6)

        # 4. Sample similarity search
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
        page.locator('[data-testid="sample-panel"]').scroll_into_view_if_needed()
        page.wait_for_function(
            "document.querySelectorAll('[data-testid=\"sample-chip\"]').length === 5",
            timeout=90_000,
        )
        rec.frame(hold=2)
        page.locator('[data-testid="sample-chip"]').first.click()
        page.wait_for_selector('[data-testid="sample-results"]')
        page.wait_for_timeout(300)
        rec.frame(hold=6)

        # 5. Leave a note in the shared session room
        page.locator('[data-testid="collab-panel"]').scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        page.fill('[data-testid="comment-author"]', "sean")
        rec.frame()
        for chunk in ("v2 fixes the clipping", " — check the low end next"):
            page.type('[data-testid="comment-input"]', chunk, delay=18)
            rec.frame()
        page.click('[data-testid="comment-send"]')
        page.wait_for_selector('[data-testid="comment-list"]')
        page.wait_for_timeout(300)
        rec.frame(hold=8)

        browser.close()
        print(f"captured {rec.n} frames")


def assemble() -> None:
    paths = sorted(f"{FRAMES}/{f}" for f in os.listdir(FRAMES) if f.endswith(".png"))
    frames = [Image.open(p).convert("RGB") for p in paths]
    # Adaptive palette keeps the dark UI from banding; GIF caps at 256 colors.
    quantized = [f.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG) for f in frames]
    quantized[0].save(
        OUT,
        save_all=True,
        append_images=quantized[1:],
        duration=FRAME_MS,
        loop=0,
        optimize=True,
    )
    mb = os.path.getsize(OUT) / 1e6
    print(f"wrote {OUT} — {len(frames)} frames, {mb:.1f} MB")


if __name__ == "__main__":
    write_assets()
    record()
    assemble()
