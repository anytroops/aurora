import { useRef } from "react";
import type { ChainReview, DawProject } from "../types";

interface Props {
  project: DawProject | null;
  onFile: (file: File) => void;
  busy: boolean;
  error: string | null;
  onReview: () => void;
  review: ChainReview | null;
  reviewLoading: boolean;
  reviewError: string | null;
}

const TYPE_STYLES: Record<string, string> = {
  audio: "bg-accent/15 text-accent",
  midi: "bg-sky-400/15 text-sky-300",
  return: "bg-purple-400/15 text-purple-300",
  group: "bg-warn/15 text-warn",
  track: "bg-accent/15 text-accent",
};

const CATEGORY_STYLES: Record<string, string> = {
  eq: "border-sky-400/40 text-sky-300",
  compressor: "border-warn/40 text-warn",
  limiter: "border-alert/50 text-alert",
  gate: "border-teal-400/40 text-teal-300",
  reverb: "border-purple-400/40 text-purple-300",
  delay: "border-purple-400/40 text-purple-300",
  saturation: "border-orange-400/40 text-orange-300",
  pitch: "border-pink-400/40 text-pink-300",
  synth: "border-accent/40 text-accent",
  sampler: "border-accent/40 text-accent",
};

const SEVERITY_STYLES: Record<string, string> = {
  high: "bg-alert/15 text-alert border-alert/40",
  medium: "bg-warn/15 text-warn border-warn/40",
  low: "bg-accent/10 text-accent border-accent/30",
};

export default function ProjectPanel({
  project,
  onFile,
  busy,
  error,
  onReview,
  review,
  reviewLoading,
  reviewError,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  const chipStyle = (trackIdx: number, deviceIdx: number): string => {
    const category = review?.chains[trackIdx]?.devices[deviceIdx]?.category;
    return (category && CATEGORY_STYLES[category]) || "border-edge text-gray-400";
  };

  return (
    <div className="rounded-xl border border-edge bg-panel p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-white">
            Project Knowledge
          </h2>
          <p className="text-xs text-gray-500">
            Upload an Ableton (.als) or REAPER (.rpp) session — Aurora reads the
            tracks, plugins, and structure so the AI can reason about your
            actual project.
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          {project && (
            <button
              data-testid="review-button"
              onClick={onReview}
              disabled={reviewLoading}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {reviewLoading ? "Reviewing…" : "Review chains"}
            </button>
          )}
          <button
            data-testid="project-button"
            onClick={() => inputRef.current?.click()}
            disabled={busy}
            className="rounded-lg border border-edge bg-black/30 px-4 py-2 text-sm font-semibold text-gray-200 transition-colors hover:border-accent/60 disabled:opacity-40"
          >
            {busy ? "Parsing…" : project ? "Replace project" : "Upload project"}
          </button>
        </div>
        <input
          ref={inputRef}
          data-testid="project-input"
          type="file"
          accept=".als,.rpp"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onFile(file);
            e.target.value = "";
          }}
        />
      </div>

      {error && (
        <div className="mt-3 rounded-md border border-alert/40 bg-alert/10 px-3 py-2 text-sm text-alert">
          {error}
        </div>
      )}

      {project && (
        <div className="mt-4" data-testid="project-tree">
          <div className="mb-3 flex flex-wrap gap-2 text-xs">
            <span className="rounded-md bg-black/30 px-2.5 py-1.5 font-semibold text-white">
              {project.daw}
            </span>
            <span className="rounded-md bg-black/30 px-2.5 py-1.5 text-gray-300">
              {project.filename}
            </span>
            {project.tempo_bpm != null && (
              <span className="rounded-md bg-black/30 px-2.5 py-1.5 text-gray-300 tabular-nums">
                {project.tempo_bpm} BPM
              </span>
            )}
            <span className="rounded-md bg-black/30 px-2.5 py-1.5 text-gray-300 tabular-nums">
              {project.track_count} tracks · {project.clip_count} clips ·{" "}
              {project.plugin_count} devices
            </span>
          </div>

          <div className="space-y-1.5">
            {project.tracks.map((t, i) => (
              <div
                key={i}
                className="flex flex-wrap items-center gap-2 rounded-md bg-black/30 px-3 py-2"
              >
                <span
                  className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                    TYPE_STYLES[t.type] ?? TYPE_STYLES.track
                  }`}
                >
                  {t.type}
                </span>
                <span className="text-sm font-medium text-white">{t.name}</span>
                <span className="text-[11px] text-gray-500 tabular-nums">
                  {t.clip_count} clip{t.clip_count === 1 ? "" : "s"}
                </span>
                <span className="flex flex-wrap gap-1">
                  {t.devices.map((d, j) => (
                    <span
                      key={j}
                      className={`rounded border px-1.5 py-0.5 text-[11px] ${chipStyle(i, j)}`}
                    >
                      {d}
                    </span>
                  ))}
                </span>
              </div>
            ))}
          </div>

          {reviewError && (
            <div className="mt-3 rounded-md border border-alert/40 bg-alert/10 px-3 py-2 text-sm text-alert">
              {reviewError}
            </div>
          )}

          {review && (
            <div className="mt-3 space-y-3" data-testid="chain-review">
              {review.findings.length > 0 && (
                <div className="space-y-1.5">
                  {review.findings.map((f, i) => (
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
              {review.review_error && (
                <div className="rounded-md border border-alert/40 bg-alert/10 px-3 py-2 text-sm text-alert">
                  {review.review_error}
                </div>
              )}
              {review.review && (
                <div className="whitespace-pre-wrap rounded-md bg-black/30 p-4 text-sm leading-relaxed text-gray-200">
                  {review.review}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
