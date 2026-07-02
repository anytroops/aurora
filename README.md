# Aurora — AI Mix Analysis

Drop in audio stems or a full mix and get:

1. **Real DSP measurements** computed server-side with librosa/pyloudnorm —
   integrated LUFS, peak/RMS/crest factor, clipping detection, L/R correlation,
   stereo width (side/mid ratio), spectral band balance, spectral centroid,
   noise floor, tempo, and key estimate.
2. **Rule-based engineering findings** derived deterministically from those
   measurements (clipping, over-limiting, phase problems, low-mid mud, etc.) —
   these work with no API key.
3. **AI mix feedback**: the measurements are sent to Claude, which returns
   prioritized, number-grounded engineering actions.
4. **DAW project knowledge**: upload an Ableton Live set (`.als`) or REAPER
   project (`.rpp`) and Aurora parses the session structure — tracks, built-in
   devices and third-party plugins (VST/VST3/AU/CLAP/JS), clip counts, tempo.
5. **Project-aware chat**: ask questions ("which tracks have no processing?",
   "why does the low end feel crowded?") and Claude answers grounded in the
   parsed project structure and the DSP measurements together.
6. **Arrangement analysis**: energy curve over time, MFCC-based section
   detection, lift/breakdown transition markers — rendered as a timeline and
   included in the AI feedback context.
7. **Mix version comparison**: select two analyzed bounces and diff every
   measurement (loudness, dynamics, stereo image, per-band balance).
8. **Sample intelligence**: timbre fingerprints (MFCC statistics + spectral
   shape) with cosine-similarity search — pick a sample, find its closest
   matches in your library.

This is a deliberately scoped-down MVP of a much larger "AI studio OS" concept —
the slice that actually runs end to end.

## Stack

- **Frontend**: React + TypeScript + Vite + Tailwind CSS, wavesurfer.js waveforms
- **Backend**: FastAPI (Python), librosa + pyloudnorm + numpy for DSP,
  Anthropic SDK for feedback

## Running it

Backend (port 8000):

```sh
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8000
```

Frontend (port 5173, proxies `/api` to the backend):

```sh
cd frontend
npm install
npm run dev
```

For AI feedback, export `ANTHROPIC_API_KEY` (or log in with `ant auth login`)
before starting the backend. Without credentials, analysis and rule-based
findings still work; the feedback button returns a clear error.

Model defaults to `claude-opus-4-8`; override with `AURORA_MODEL`.
