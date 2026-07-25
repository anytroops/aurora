"""Shared fixtures: synthetic audio and DAW project files.

Everything here is generated, so the suite needs no binary assets in the repo.
"""

import gzip
import io

import numpy as np
import pytest
import soundfile as sf

SR = 22050


def wav_bytes(samples: np.ndarray, sr: int = SR) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, samples.astype("float32"), sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


@pytest.fixture
def clean_tone() -> bytes:
    """3s stereo sine at a sane level — no clipping, healthy dynamics."""
    t = np.linspace(0, 3.0, int(SR * 3.0), endpoint=False)
    mono = 0.25 * np.sin(2 * np.pi * 440 * t)
    return wav_bytes(np.stack([mono, mono], axis=1))


@pytest.fixture
def clipped_mix() -> bytes:
    """Deliberately hot: driven into the ceiling, heavy low-mid content."""
    t = np.linspace(0, 3.0, int(SR * 3.0), endpoint=False)
    mono = 0.6 * np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 300 * t)
    mono = np.clip(mono * 1.6, -1.0, 1.0)
    return wav_bytes(np.stack([mono, mono * 0.98], axis=1))


@pytest.fixture
def out_of_phase() -> bytes:
    """Left and right inverted — correlation should land near -1."""
    t = np.linspace(0, 2.0, int(SR * 2.0), endpoint=False)
    mono = 0.3 * np.sin(2 * np.pi * 220 * t)
    return wav_bytes(np.stack([mono, -mono], axis=1))


@pytest.fixture
def structured_song() -> np.ndarray:
    """60s mono: quiet intro, loud drop, quiet breakdown, loud outro."""
    rng = np.random.default_rng(7)

    def seg(dur: float, level: float, kind: str) -> np.ndarray:
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

    return np.concatenate(
        [
            seg(15, 0.12, "pad"),
            seg(15, 0.85, "full"),
            seg(15, 0.18, "sparse"),
            seg(15, 0.85, "full"),
        ]
    )


@pytest.fixture
def kick_sample() -> bytes:
    t = np.linspace(0, 0.6, int(SR * 0.6), endpoint=False)
    return wav_bytes(np.sin(2 * np.pi * (50 + 40 * np.exp(-t * 30)) * t) * np.exp(-t * 8) * 0.9)


@pytest.fixture
def kick_sample_2() -> bytes:
    t = np.linspace(0, 0.6, int(SR * 0.6), endpoint=False)
    return wav_bytes(np.sin(2 * np.pi * (58 + 40 * np.exp(-t * 30)) * t) * np.exp(-t * 8) * 0.85)


@pytest.fixture
def hat_sample() -> bytes:
    rng = np.random.default_rng(3)
    t = np.linspace(0, 0.4, int(SR * 0.4), endpoint=False)
    return wav_bytes(rng.standard_normal(len(t)) * np.exp(-t * 60) * 0.6)


REAPER_PROJECT = """<REAPER_PROJECT 0.1 "7.07/macOS-arm64" 1719900000
  TEMPO 128 4 4
  <TRACK {11111111}
    NAME "Drums"
    <ITEM
      NAME "drum_loop.wav"
    >
    <ITEM
      NAME "drum_fill.wav"
    >
    <FXCHAIN
      <VST "VST3: Pro-Q 3 (FabFilter)" "q.vst3" 0 "" 1
      >
      <VST "VST: ReaComp (Cockos)" "reacomp.dll" 0 "" 2
      >
    >
  >
  <TRACK {22222222}
    NAME "Bass"
    <ITEM
      NAME "bass_di.wav"
    >
    <FXCHAIN
      <VST3 "VST3: Serum (Xfer Records)" "Serum.vst3" 0 "" 3
      >
    >
  >
  <TRACK {33333333}
    NAME "Vox Lead"
    <ITEM
      NAME "vox.wav"
    >
  >
>
"""

ABLETON_PROJECT = """<?xml version="1.0" encoding="UTF-8"?>
<Ableton MajorVersion="5" MinorVersion="11.0_11202">
  <LiveSet>
    <Tracks>
      <MidiTrack Id="8">
        <Name><EffectiveName Value="Bass" /></Name>
        <DeviceChain>
          <DeviceChain>
            <Devices>
              <Operator Id="0"></Operator>
              <PluginDevice Id="1">
                <PluginDesc><Vst3PluginInfo><Name Value="Serum" /></Vst3PluginInfo></PluginDesc>
              </PluginDevice>
              <Saturator Id="2"></Saturator>
            </Devices>
          </DeviceChain>
          <MainSequencer><ClipTimeable><ArrangerAutomation><Events>
            <MidiClip Id="0"></MidiClip>
            <MidiClip Id="1"></MidiClip>
          </Events></ArrangerAutomation></ClipTimeable></MainSequencer>
        </DeviceChain>
      </MidiTrack>
      <AudioTrack Id="9">
        <Name><EffectiveName Value="Vocals" /></Name>
        <DeviceChain>
          <DeviceChain>
            <Devices>
              <Eq8 Id="0"></Eq8>
              <Compressor2 Id="1"></Compressor2>
              <AuPluginDevice Id="2">
                <PluginDesc><AuPluginInfo><Name Value="FabFilter Pro-Q 3" /></AuPluginInfo></PluginDesc>
              </AuPluginDevice>
            </Devices>
          </DeviceChain>
          <MainSequencer><Sample><ArrangerAutomation><Events>
            <AudioClip Id="0"></AudioClip>
          </Events></ArrangerAutomation></Sample></MainSequencer>
        </DeviceChain>
      </AudioTrack>
      <ReturnTrack Id="10">
        <Name><EffectiveName Value="A-Reverb" /></Name>
        <DeviceChain><DeviceChain><Devices>
          <Reverb Id="0"></Reverb>
        </Devices></DeviceChain></DeviceChain>
      </ReturnTrack>
    </Tracks>
    <MasterTrack>
      <DeviceChain><Mixer><Tempo><Manual Value="124" /></Tempo></Mixer></DeviceChain>
    </MasterTrack>
  </LiveSet>
</Ableton>
"""


@pytest.fixture
def reaper_bytes() -> bytes:
    return REAPER_PROJECT.encode()


@pytest.fixture
def ableton_bytes() -> bytes:
    return gzip.compress(ABLETON_PROJECT.encode())


@pytest.fixture
def parsed_reaper(reaper_bytes: bytes) -> dict:
    from app.daw import parse_project

    return parse_project(reaper_bytes, "test.rpp")


def metrics_stub(**overrides) -> dict:
    """A clean, finding-free metrics dict; override fields to trip one rule."""
    base = {
        "filename": "stub.wav",
        "duration_s": 60.0,
        "sample_rate": 44100,
        "channels": 2,
        "peak_dbfs": -1.0,
        "rms_dbfs": -14.0,
        "crest_factor_db": 13.0,
        "lufs_integrated": -14.0,
        "clipped_samples": 0,
        "max_clip_run": 0,
        "correlation": 0.8,
        "stereo_width": 0.4,
        "spectral_balance_pct": {
            "sub": 10.0,
            "bass": 25.0,
            "low_mid": 20.0,
            "mid": 25.0,
            "high_mid": 12.0,
            "high": 8.0,
        },
        "spectral_centroid_hz": 2000.0,
        "noise_floor_db": -70.0,
        "tempo_bpm": 120.0,
        "key_estimate": "A minor",
    }
    base.update(overrides)
    return base
