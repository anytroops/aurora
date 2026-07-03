import { useState } from "react";
import type { ChatEntry } from "../types";

export type ChatMode = "session" | "dsp_code";

interface Props {
  onAsk: (question: string, mode: ChatMode) => void;
  entries: ChatEntry[];
  loading: boolean;
  error: string | null;
  hasSessionData: boolean;
}

export default function ChatPanel({
  onAsk,
  entries,
  loading,
  error,
  hasSessionData,
}: Props) {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<ChatMode>("session");

  const sessionDisabled = mode === "session" && !hasSessionData;

  const submit = () => {
    const q = question.trim();
    if (!q || loading || sessionDisabled) return;
    setQuestion("");
    onAsk(q, mode);
  };

  return (
    <div className="rounded-xl border border-edge bg-panel p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-white">Ask Aurora</h2>
          <p className="text-xs text-gray-500">
            {mode === "session"
              ? "Answers grounded in the parsed project and measurements above."
              : "DSP / audio-code assistant: JUCE, VST3/AU, real-time C++, SIMD."}
          </p>
        </div>
        <div className="flex shrink-0 rounded-lg border border-edge bg-black/30 p-0.5 text-xs">
          {(
            [
              ["session", "Session"],
              ["dsp_code", "DSP code"],
            ] as [ChatMode, string][]
          ).map(([m, label]) => (
            <button
              key={m}
              data-testid={`chat-mode-${m}`}
              onClick={() => setMode(m)}
              className={`rounded-md px-3 py-1.5 font-semibold transition-colors ${
                mode === m ? "bg-accent text-ink" : "text-gray-400 hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3 space-y-3">
        {entries.map((e, i) => (
          <div key={i} data-testid="chat-entry">
            <div className="text-sm font-semibold text-accent">You: {e.question}</div>
            <div className="mt-1 whitespace-pre-wrap rounded-md bg-black/30 p-3 text-sm leading-relaxed text-gray-200">
              {e.answer}
            </div>
          </div>
        ))}
        {loading && <div className="text-sm text-gray-500">Thinking…</div>}
        {error && (
          <div className="rounded-md border border-alert/40 bg-alert/10 px-3 py-2 text-sm text-alert">
            {error}
          </div>
        )}
      </div>

      <div className="mt-3 flex gap-2">
        <input
          data-testid="chat-input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder={
            mode === "session"
              ? sessionDisabled
                ? "Upload audio or a project first, or switch to DSP code mode…"
                : "Ask about the project or mix…"
              : "e.g. Write a JUCE biquad with NEON-friendly inner loop…"
          }
          className="min-w-0 flex-1 rounded-lg border border-edge bg-black/30 px-3 py-2 text-sm text-white placeholder:text-gray-600 focus:border-accent/60 focus:outline-none"
        />
        <button
          data-testid="chat-send"
          onClick={submit}
          disabled={loading || !question.trim() || sessionDisabled}
          className="shrink-0 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Ask
        </button>
      </div>
    </div>
  );
}
