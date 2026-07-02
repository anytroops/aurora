import { useState } from "react";
import type { TrackAnalysis, TrackMetrics } from "../types";

type Row = {
  label: string;
  unit: string;
  get: (m: TrackMetrics) => number | null;
  decimals: number;
};

const ROWS: Row[] = [
  { label: "Loudness", unit: "LUFS", get: (m) => m.lufs_integrated, decimals: 1 },
  { label: "Peak", unit: "dBFS", get: (m) => m.peak_dbfs, decimals: 1 },
  { label: "RMS", unit: "dBFS", get: (m) => m.rms_dbfs, decimals: 1 },
  { label: "Crest factor", unit: "dB", get: (m) => m.crest_factor_db, decimals: 1 },
  { label: "L/R correlation", unit: "", get: (m) => m.correlation, decimals: 2 },
  { label: "Stereo width", unit: "", get: (m) => m.stereo_width, decimals: 2 },
  { label: "Noise floor", unit: "dBFS", get: (m) => m.noise_floor_db, decimals: 1 },
  { label: "Sub (<60 Hz)", unit: "%", get: (m) => m.spectral_balance_pct.sub, decimals: 1 },
  { label: "Bass (60–250)", unit: "%", get: (m) => m.spectral_balance_pct.bass, decimals: 1 },
  { label: "Low-mid (250–500)", unit: "%", get: (m) => m.spectral_balance_pct.low_mid, decimals: 1 },
  { label: "Mid (500–2k)", unit: "%", get: (m) => m.spectral_balance_pct.mid, decimals: 1 },
  { label: "High-mid (2k–6k)", unit: "%", get: (m) => m.spectral_balance_pct.high_mid, decimals: 1 },
  { label: "High (6k+)", unit: "%", get: (m) => m.spectral_balance_pct.high, decimals: 1 },
];

function fmt(v: number | null, decimals: number): string {
  return v == null ? "—" : v.toFixed(decimals);
}

export default function ComparePanel({ tracks }: { tracks: TrackAnalysis[] }) {
  const [aId, setAId] = useState(tracks[0]?.id ?? "");
  const [bId, setBId] = useState(tracks[1]?.id ?? "");

  const a = tracks.find((t) => t.id === aId) ?? tracks[0];
  const b = tracks.find((t) => t.id === bId) ?? tracks[1];
  if (!a || !b) return null;

  const select = (value: string, onChange: (v: string) => void, testid: string) => (
    <select
      data-testid={testid}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="min-w-0 flex-1 rounded-lg border border-edge bg-black/30 px-2 py-1.5 text-sm text-white focus:border-accent/60 focus:outline-none"
    >
      {tracks.map((t) => (
        <option key={t.id} value={t.id}>
          {t.name}
        </option>
      ))}
    </select>
  );

  return (
    <div className="rounded-xl border border-edge bg-panel p-4" data-testid="compare-panel">
      <h2 className="font-display text-lg font-semibold text-white">
        Version comparison
      </h2>
      <p className="text-xs text-gray-500">
        Diff two bounces to see exactly what changed between mix versions.
      </p>

      <div className="mt-3 flex items-center gap-2">
        {select(a.id, setAId, "compare-a")}
        <span className="shrink-0 text-xs text-gray-500">vs</span>
        {select(b.id, setBId, "compare-b")}
      </div>

      <table className="mt-3 w-full text-sm">
        <thead>
          <tr className="text-left text-[10px] uppercase tracking-wider text-gray-500">
            <th className="py-1 font-medium">Measurement</th>
            <th className="py-1 text-right font-medium">A</th>
            <th className="py-1 text-right font-medium">B</th>
            <th className="py-1 text-right font-medium">Δ (B − A)</th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => {
            const va = row.get(a.metrics);
            const vb = row.get(b.metrics);
            const delta = va != null && vb != null ? vb - va : null;
            const big = delta != null && Math.abs(delta) >= (row.unit === "%" ? 3 : 1);
            return (
              <tr key={row.label} className="border-t border-edge/60">
                <td className="py-1.5 text-gray-300">
                  {row.label}
                  {row.unit && (
                    <span className="ml-1 text-[10px] text-gray-600">{row.unit}</span>
                  )}
                </td>
                <td className="py-1.5 text-right text-white tabular-nums">
                  {fmt(va, row.decimals)}
                </td>
                <td className="py-1.5 text-right text-white tabular-nums">
                  {fmt(vb, row.decimals)}
                </td>
                <td
                  className={`py-1.5 text-right font-semibold tabular-nums ${
                    delta == null || Math.abs(delta) < 0.005
                      ? "text-gray-600"
                      : big
                        ? delta > 0
                          ? "text-accent"
                          : "text-sky-300"
                        : "text-gray-400"
                  }`}
                >
                  {delta == null
                    ? "—"
                    : `${delta > 0 ? "+" : ""}${delta.toFixed(row.decimals)}`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {(a.metrics.clipped_samples > 0 || b.metrics.clipped_samples > 0) && (
        <p className="mt-2 text-xs text-gray-500 tabular-nums">
          Clipped samples: A {a.metrics.clipped_samples.toLocaleString()} · B{" "}
          {b.metrics.clipped_samples.toLocaleString()}
        </p>
      )}
    </div>
  );
}
