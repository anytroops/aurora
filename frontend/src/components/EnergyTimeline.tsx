import type { Arrangement } from "../types";

const LEVEL_COLORS: Record<string, string> = {
  low: "rgba(125, 211, 168, 0.10)",
  mid: "rgba(232, 180, 90, 0.14)",
  high: "rgba(232, 122, 106, 0.16)",
};

function fmt(t: number): string {
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function EnergyTimeline({
  arrangement,
  duration,
}: {
  arrangement: Arrangement;
  duration: number;
}) {
  const pts = arrangement.energy_curve;
  if (pts.length < 2 || duration <= 0) return null;

  const W = 600;
  const H = 72;
  const dbs = pts.map((p) => p.db);
  const min = Math.min(...dbs);
  const max = Math.max(...dbs);
  const x = (t: number) => (t / duration) * W;
  const y = (db: number) => H - 6 - ((db - min) / (max - min || 1)) * (H - 18);

  const line = pts
    .map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)},${y(p.db).toFixed(1)}`)
    .join(" ");
  const area = `${line} L${W},${H} L0,${H} Z`;

  return (
    <div data-testid="energy-timeline">
      <div className="mb-1 mt-3 text-[10px] uppercase tracking-wider text-gray-500">
        Energy / arrangement
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full rounded-md bg-black/30"
        preserveAspectRatio="none"
      >
        {arrangement.sections.map((s, i) => (
          <rect
            key={i}
            x={x(s.start)}
            y={0}
            width={x(s.end) - x(s.start)}
            height={H}
            fill={LEVEL_COLORS[s.level]}
          />
        ))}
        {arrangement.sections.slice(1).map((s, i) => (
          <line
            key={i}
            x1={x(s.start)}
            x2={x(s.start)}
            y1={0}
            y2={H}
            stroke="#232830"
            strokeWidth={1}
          />
        ))}
        <path d={area} fill="rgba(125, 211, 168, 0.15)" />
        <path d={line} fill="none" stroke="#7dd3a8" strokeWidth={1.5} />
        {arrangement.transitions.map((tr, i) => (
          <path
            key={i}
            d={
              tr.kind === "lift"
                ? `M${x(tr.t) - 5},10 L${x(tr.t) + 5},10 L${x(tr.t)},2 Z`
                : `M${x(tr.t) - 5},2 L${x(tr.t) + 5},2 L${x(tr.t)},10 Z`
            }
            fill={tr.kind === "lift" ? "#7dd3a8" : "#7cb8e8"}
          >
            <title>
              {tr.kind} at {fmt(tr.t)} ({tr.delta_db > 0 ? "+" : ""}
              {tr.delta_db} dB)
            </title>
          </path>
        ))}
      </svg>
      {arrangement.sections.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {arrangement.sections.map((s, i) => (
            <span
              key={i}
              className="rounded border border-edge px-1.5 py-0.5 text-[10px] text-gray-400 tabular-nums"
            >
              {fmt(s.start)}–{fmt(s.end)} · {s.level} ({s.energy_db} dB)
            </span>
          ))}
          {arrangement.transitions.map((tr, i) => (
            <span
              key={`t${i}`}
              className={`rounded border px-1.5 py-0.5 text-[10px] tabular-nums ${
                tr.kind === "lift"
                  ? "border-accent/40 text-accent"
                  : "border-sky-400/40 text-sky-300"
              }`}
            >
              {tr.kind === "lift" ? "▲" : "▼"} {tr.kind} {fmt(tr.t)} (
              {tr.delta_db > 0 ? "+" : ""}
              {tr.delta_db} dB)
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
