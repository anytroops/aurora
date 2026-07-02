import { useState } from "react";
import type { ChatEntry } from "../types";

interface Props {
  onAsk: (question: string) => void;
  entries: ChatEntry[];
  loading: boolean;
  error: string | null;
}

export default function ChatPanel({ onAsk, entries, loading, error }: Props) {
  const [question, setQuestion] = useState("");

  const submit = () => {
    const q = question.trim();
    if (!q || loading) return;
    setQuestion("");
    onAsk(q);
  };

  return (
    <div className="rounded-xl border border-edge bg-panel p-4">
      <h2 className="font-display text-lg font-semibold text-white">
        Ask about your session
      </h2>
      <p className="text-xs text-gray-500">
        Answers are grounded in the parsed project and the measurements above —
        e.g. “which tracks have no processing?” or “why does the mix sound
        muddy?”
      </p>

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
          placeholder="Ask a question about the project or mix…"
          className="min-w-0 flex-1 rounded-lg border border-edge bg-black/30 px-3 py-2 text-sm text-white placeholder:text-gray-600 focus:border-accent/60 focus:outline-none"
        />
        <button
          data-testid="chat-send"
          onClick={submit}
          disabled={loading || !question.trim()}
          className="shrink-0 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Ask
        </button>
      </div>
    </div>
  );
}
