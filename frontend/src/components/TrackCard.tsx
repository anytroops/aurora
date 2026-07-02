import type { TrackAnalysis } from "../types";
import Waveform from "./Waveform";

const BAND_LABELS: [keyof TrackAnalysis["metrics"]["spectral_balance_pct"], string][] = [
  ["sub", "Sub"],
  ["bass", "Bass"],
  ["low_mid", "LoMid"],
  ["mid", "Mid"],
  ["high_mid", "HiMid"],
  ["high", "High"],
];

const SEVERITY_STYLES: Record<string, string> = {
  high: "bg-alert/15 text-alert border-alert/40",
  medium: "bg-warn/15 text-warn border-warn/40",
  low: "bg-accent/10 text-accent border-accent/30",
};

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-black/30 px-2.5 py-1.5">
      <div className="text-[10px] uppercase tracking-wider text-gray-500">{label}</div>
      <div className="text-sm font-semibold text-white tabular-nums">{value}</div>
    </div>
  );
}

export default function TrackCard({ track }: { track: TrackAnalysis }) {
  const m = track.metrics;
  const maxBand = Math.max(...Object.values(m.spectral_balance_pct), 1);

  return (
    <div
      data-testid="track-card"
      className="rounded-xl border border-edge bg-panel p-4 shadow-lg shadow-black/30"
    >
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h3 className="truncate font-display text-base font-semibold text-white">
          {track.name}
        </h3>
        <span className="shrink-0 text-xs text-gray-500">
          {m.duration_s.toFixed(1)}s · {m.sample_rate / 1000} kHz ·{" "}
          {m.channels === 2 ? "stereo" : "mono"}
        </span>
      </div>

      <Waveform url={track.url} />

      <div className="mt-3 grid grid-cols-4 gap-2 sm:grid-cols-8">
        <Metric label="LUFS" value={m.lufs_integrated?.toFixed(1) ?? "—"} />
        <Metric label="Peak dB" value={m.peak_dbfs.toFixed(1)} />
        <Metric label="RMS dB" value={m.rms_dbfs.toFixed(1)} />
        <Metric label="Crest" value={`${m.crest_factor_db.toFixed(1)}`} />
        <Metric label="Corr" value={m.correlation?.toFixed(2) ?? "—"} />
        <Metric label="Width" value={m.stereo_width?.toFixed(2) ?? "—"} />
        <Metric label="BPM" value={m.tempo_bpm?.toFixed(0) ?? "—"} />
        <Metric label="Key" value={m.key_estimate ?? "—"} />
      </div>

      <div className="mt-3">
        <div className="mb-1 text-[10px] uppercase tracking-wider text-gray-500">
          Spectral balance
        </div>
        <div className="flex h-16 items-end gap-1.5">
          {BAND_LABELS.map(([key, label]) => {
            const pct = m.spectral_balance_pct[key];
            return (
              <div key={key} className="flex flex-1 flex-col items-center gap-1">
                <div className="flex h-12 w-full items-end rounded-sm bg-black/30">
                  <div
                    className="w-full rounded-sm bg-accent/70"
                    style={{ height: `${Math.max((pct / maxBand) * 100, 2)}%` }}
                    title={`${label}: ${pct}%`}
                  />
                </div>
                <span className="text-[9px] text-gray-500">{label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {track.findings.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {track.findings.map((f, i) => (
            <div
              key={i}
              className={`rounded-md border px-3 py-2 text-xs ${SEVERITY_STYLES[f.severity]}`}
            >
              <span className="font-semibold">{f.title}.</span>{" "}
              <span className="opacity-80">{f.detail}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
