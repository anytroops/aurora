import { useState } from "react";
import type { Comment } from "../types";

interface Props {
  connected: boolean;
  peers: number;
  comments: Comment[];
  shareUrl: string;
  onComment: (author: string, text: string) => void;
}

export default function CollabPanel({
  connected,
  peers,
  comments,
  shareUrl,
  onComment,
}: Props) {
  const [author, setAuthor] = useState(
    () => localStorage.getItem("aurora_author") ?? "",
  );
  const [text, setText] = useState("");
  const [copied, setCopied] = useState(false);

  const submit = () => {
    const t = text.trim();
    const a = author.trim() || "anonymous";
    if (!t) return;
    localStorage.setItem("aurora_author", a);
    onComment(a, t);
    setText("");
  };

  return (
    <div className="rounded-xl border border-edge bg-panel p-4" data-testid="collab-panel">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-white">
            Session Room
          </h2>
          <p className="text-xs text-gray-500">
            Everyone with the link sees the same analyses and comments, live.
            Audio never leaves your machine — only measurements sync.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span
            data-testid="collab-status"
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs ${
              connected ? "bg-accent/10 text-accent" : "bg-alert/10 text-alert"
            }`}
          >
            <span className="text-[8px]">●</span>
            {connected ? `live · ${peers} here` : "offline"}
          </span>
          <button
            data-testid="collab-share"
            onClick={() => {
              navigator.clipboard.writeText(shareUrl).then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              });
            }}
            className="rounded-lg border border-edge bg-black/30 px-3 py-1.5 text-xs font-semibold text-gray-200 transition-colors hover:border-accent/60"
          >
            {copied ? "Copied!" : "Copy invite link"}
          </button>
        </div>
      </div>

      {comments.length > 0 && (
        <div className="mt-3 max-h-56 space-y-1.5 overflow-y-auto" data-testid="comment-list">
          {comments.map((c) => (
            <div key={c.id} className="rounded-md bg-black/30 px-3 py-2 text-sm">
              <span className="font-semibold text-accent">{c.author}</span>{" "}
              <span className="text-[10px] text-gray-600 tabular-nums">
                {new Date(c.ts).toLocaleTimeString()}
              </span>
              <div className="text-gray-200">{c.text}</div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-3 flex gap-2">
        <input
          data-testid="comment-author"
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          placeholder="Name"
          className="w-28 rounded-lg border border-edge bg-black/30 px-3 py-2 text-sm text-white placeholder:text-gray-600 focus:border-accent/60 focus:outline-none"
        />
        <input
          data-testid="comment-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="Leave a note for the session…"
          className="min-w-0 flex-1 rounded-lg border border-edge bg-black/30 px-3 py-2 text-sm text-white placeholder:text-gray-600 focus:border-accent/60 focus:outline-none"
        />
        <button
          data-testid="comment-send"
          onClick={submit}
          disabled={!text.trim()}
          className="shrink-0 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Post
        </button>
      </div>
    </div>
  );
}
