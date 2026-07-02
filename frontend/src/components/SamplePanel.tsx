import { useRef, useState } from "react";
import { analyzeSample } from "../lib/api";

interface SampleInfo {
  id: string;
  name: string;
  duration_s: number;
  vector: number[];
}

function cosine(a: number[], b: number[]): number {
  let dot = 0;
  let na = 0;
  let nb = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    na += a[i] * a[i];
    nb += b[i] * b[i];
  }
  const denom = Math.sqrt(na) * Math.sqrt(nb);
  return denom ? dot / denom : 0;
}

export default function SamplePanel() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [samples, setSamples] = useState<SampleInfo[]>([]);
  const [refId, setRefId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFiles = async (files: File[]) => {
    setBusy(true);
    setError(null);
    for (const file of files) {
      try {
        const s = await analyzeSample(file);
        setSamples((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            name: s.filename,
            duration_s: s.duration_s,
            vector: s.vector,
          },
        ]);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    }
    setBusy(false);
  };

  const reference = samples.find((s) => s.id === refId) ?? null;
  const ranked = reference
    ? samples
        .filter((s) => s.id !== reference.id)
        .map((s) => ({ ...s, similarity: cosine(reference.vector, s.vector) }))
        .sort((a, b) => b.similarity - a.similarity)
    : [];

  return (
    <div className="rounded-xl border border-edge bg-panel p-4" data-testid="sample-panel">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-white">
            Sample Intelligence
          </h2>
          <p className="text-xs text-gray-500">
            Drop in samples to build a library, then pick one to find its
            closest timbral matches — similarity search over audio-feature
            fingerprints.
          </p>
        </div>
        <button
          data-testid="sample-button"
          onClick={() => inputRef.current?.click()}
          disabled={busy}
          className="shrink-0 rounded-lg border border-edge bg-black/30 px-4 py-2 text-sm font-semibold text-gray-200 transition-colors hover:border-accent/60 disabled:opacity-40"
        >
          {busy ? "Fingerprinting…" : "Add samples"}
        </button>
        <input
          ref={inputRef}
          data-testid="sample-input"
          type="file"
          accept="audio/*,.wav,.mp3,.flac,.aiff,.ogg,.m4a"
          multiple
          className="hidden"
          onChange={(e) => {
            const files = Array.from(e.target.files ?? []);
            if (files.length) handleFiles(files);
            e.target.value = "";
          }}
        />
      </div>

      {error && (
        <div className="mt-3 rounded-md border border-alert/40 bg-alert/10 px-3 py-2 text-sm text-alert">
          {error}
        </div>
      )}

      {samples.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {samples.map((s) => (
            <button
              key={s.id}
              data-testid="sample-chip"
              onClick={() => setRefId(s.id)}
              className={`rounded-md border px-2.5 py-1 text-xs transition-colors ${
                s.id === refId
                  ? "border-accent bg-accent/15 text-accent"
                  : "border-edge bg-black/30 text-gray-300 hover:border-accent/60"
              }`}
            >
              {s.name}
              <span className="ml-1 text-gray-600 tabular-nums">
                {s.duration_s.toFixed(1)}s
              </span>
            </button>
          ))}
        </div>
      )}

      {reference && (
        <div className="mt-3" data-testid="sample-results">
          <div className="mb-1 text-[10px] uppercase tracking-wider text-gray-500">
            Most similar to “{reference.name}”
          </div>
          {ranked.length === 0 ? (
            <p className="text-sm text-gray-500">
              Add more samples to compare against.
            </p>
          ) : (
            <div className="space-y-1">
              {ranked.map((s) => (
                <div key={s.id} className="flex items-center gap-2">
                  <span className="w-48 truncate text-sm text-gray-200">{s.name}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-black/40">
                    <div
                      className="h-full rounded-full bg-accent/70"
                      style={{ width: `${Math.max(s.similarity, 0) * 100}%` }}
                    />
                  </div>
                  <span className="w-12 text-right text-xs text-gray-400 tabular-nums">
                    {(Math.max(s.similarity, 0) * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
