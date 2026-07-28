"""Guard against CPU-bound work sneaking back onto the event loop.

Analysing a full song is seconds of librosa work. Run directly inside an
`async def` handler it blocks the whole server — every other request and all
collaboration WebSocket traffic stalls behind it. The upload endpoints offload
to a worker thread; this test fails if that regresses.

The assertion is on *throughput*, not latency: when the loop is blocked a
concurrent request never gets scheduled to begin with, so its measured latency
stays small while the server serves essentially nothing. Measured here, a
2-second analysis allowed 82 concurrent requests when offloaded and 1 when not.
"""

import asyncio
import io
import time

import numpy as np
import pytest
import soundfile as sf
from httpx import ASGITransport, AsyncClient

from app.main import app

SR = 44100
MIN_CONCURRENT_REQUESTS = 10
# Generous for a contended CI runner, but bounded — see the guard below.
ANALYSIS_DEADLINE_S = 90


@pytest.fixture(scope="module")
def long_song() -> bytes:
    """90s of 44.1 kHz stereo — long enough that analysis takes ~2s."""
    t = np.linspace(0, 90, SR * 90, endpoint=False)
    sig = np.sin(2 * np.pi * 55 * t) * 0.4 + ((t * 110) % 1 - 0.5) * 0.3
    buf = io.BytesIO()
    sf.write(buf, np.stack([sig, sig * 0.96], axis=1).astype("float32"), SR, format="WAV")
    return buf.getvalue()


def test_analysis_does_not_block_the_event_loop(long_song):
    async def scenario() -> tuple[float, int]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:

            async def analyze() -> float:
                start = time.perf_counter()
                r = await client.post(
                    "/api/analyze",
                    files={"file": ("song.wav", long_song, "audio/wav")},
                    timeout=120,
                )
                assert r.status_code == 200
                return time.perf_counter() - start

            task = asyncio.create_task(analyze())
            await asyncio.sleep(0.05)  # let the request get going

            # httpx timeouts are not enforced over ASGITransport (there is no
            # socket to time out), so this loop needs its own wall-clock guard
            # or a stalled request would spin it forever.
            deadline = time.perf_counter() + ANALYSIS_DEADLINE_S
            served = 0
            while not task.done():
                if time.perf_counter() > deadline:
                    task.cancel()
                    pytest.fail(
                        f"analysis did not finish within {ANALYSIS_DEADLINE_S}s "
                        f"after {served} concurrent requests"
                    )
                r = await client.get("/api/health", timeout=60)
                assert r.status_code == 200
                served += 1
                await asyncio.sleep(0.02)

            return await task, served

    analysis_s, served = asyncio.run(scenario())

    assert analysis_s > 0.5, "song too short to prove anything — lengthen the fixture"
    assert served >= MIN_CONCURRENT_REQUESTS, (
        f"only {served} request(s) served during a {analysis_s * 1000:.0f} ms "
        "analysis — CPU work is back on the event loop"
    )
