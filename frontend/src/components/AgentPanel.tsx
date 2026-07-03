import { useState } from "react";
import type { AgentResult } from "../types";
import { runAgent } from "../lib/api";
import type { AiTrackPayload } from "../lib/api";
import type { DawProject } from "../types";

const AGENTS: { id: string; label: string; needs: "tracks" | "project"; blurb: string }[] = [
  { id: "mixing", label: "Mixing", needs: "tracks", blurb: "balance, EQ, compression plan" },
  { id: "mastering", label: "Mastering", needs: "tracks", blurb: "loudness, ceiling, chain order" },
  { id: "arrangement", label: "Arrangement", needs: "tracks", blurb: "energy arc, transitions" },
  { id: "session_prep", label: "Session Prep", needs: "project", blurb: "chain hygiene, routing" },
];

interface Props {
  tracks: AiTrackPayload[];
  project: DawProject | null;
}

export default function AgentPanel({ tracks, project }: Props) {
  const [running, setRunning] = useState<string | null>(null);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (agentId: string) => {
    setRunning(agentId);
    setError(null);
    setResult(null);
    try {
      setResult(await runAgent(agentId, project, tracks));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(null);
    }
  };

  return (
    <div className="rounded-xl border border-edge bg-panel p-4" data-testid="agent-panel">
      <h2 className="font-display text-lg font-semibold text-white">Agents</h2>
      <p className="text-xs text-gray-500">
        Scoped multi-step pipelines: gather session data, run the rule scan,
        compile a brief, then a specialized AI pass produces an executable plan.
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        {AGENTS.map((a) => {
          const unavailable =
            (a.needs === "tracks" && tracks.length === 0) ||
            (a.needs === "project" && !project);
          return (
            <button
              key={a.id}
              data-testid={`agent-${a.id}`}
              onClick={() => run(a.id)}
              disabled={running !== null || unavailable}
              title={
                unavailable
                  ? a.needs === "tracks"
                    ? "Needs analyzed audio"
                    : "Needs a parsed project file"
                  : a.blurb
              }
              className="rounded-lg border border-edge bg-black/30 px-3 py-2 text-left text-sm transition-colors hover:border-accent/60 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <span className="font-semibold text-white">
                {running === a.id ? "Running… " : ""}
                {a.label}
              </span>
              <span className="block text-[11px] text-gray-500">{a.blurb}</span>
            </button>
          );
        })}
      </div>

      {error && (
        <div className="mt-3 rounded-md border border-alert/40 bg-alert/10 px-3 py-2 text-sm text-alert">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-3" data-testid="agent-result">
          <div className="mb-2 space-y-1">
            {result.steps.map((s, i) => (
              <div key={i} className="flex items-baseline gap-2 text-xs">
                <span className="text-accent">✓</span>
                <span className="font-semibold text-gray-300">{s.name}</span>
                <span className="text-gray-500">{s.detail}</span>
              </div>
            ))}
          </div>
          {result.report_error && (
            <div className="rounded-md border border-alert/40 bg-alert/10 px-3 py-2 text-sm text-alert">
              {result.report_error}
            </div>
          )}
          {result.report && (
            <div className="whitespace-pre-wrap rounded-md bg-black/30 p-4 text-sm leading-relaxed text-gray-200">
              {result.report}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
