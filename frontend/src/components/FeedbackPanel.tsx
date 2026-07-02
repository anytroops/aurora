interface Props {
  onRequest: () => void;
  loading: boolean;
  feedback: string | null;
  error: string | null;
  disabled: boolean;
}

export default function FeedbackPanel({
  onRequest,
  loading,
  feedback,
  error,
  disabled,
}: Props) {
  return (
    <div className="rounded-xl border border-edge bg-panel p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-white">
            AI Mix Feedback
          </h2>
          <p className="text-xs text-gray-500">
            Claude reads the measurements above and gives prioritized engineering
            actions.
          </p>
        </div>
        <button
          data-testid="feedback-button"
          onClick={onRequest}
          disabled={disabled || loading}
          className="shrink-0 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "Thinking…" : "Get feedback"}
        </button>
      </div>

      {error && (
        <div className="mt-3 rounded-md border border-alert/40 bg-alert/10 px-3 py-2 text-sm text-alert">
          {error}
        </div>
      )}

      {feedback && (
        <div
          data-testid="feedback-text"
          className="mt-3 whitespace-pre-wrap rounded-md bg-black/30 p-4 text-sm leading-relaxed text-gray-200"
        >
          {feedback}
        </div>
      )}
    </div>
  );
}
