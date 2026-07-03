import type {
  AgentResult,
  Arrangement,
  ChainReview,
  DawProject,
  Finding,
  Section,
  TrackMetrics,
  Transition,
} from "../types";

export interface AiTrackPayload {
  metrics: TrackMetrics;
  findings: Finding[];
  arrangement?: { sections: Section[]; transitions: Transition[] };
}

async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body.detail ?? res.statusText;
  } catch {
    return res.statusText;
  }
}

export async function analyzeFile(
  file: File,
): Promise<{ metrics: TrackMetrics; findings: Finding[]; arrangement: Arrangement }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/analyze", { method: "POST", body: form });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function analyzeProject(file: File): Promise<DawProject> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/project", { method: "POST", body: form });
  if (!res.ok) throw new Error(await readError(res));
  const body = await res.json();
  return body.project;
}

export async function askQuestion(
  question: string,
  project: DawProject | null,
  tracks: AiTrackPayload[],
  mode: "session" | "dsp_code" = "session",
): Promise<string> {
  const res = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, project, tracks, mode }),
  });
  if (!res.ok) throw new Error(await readError(res));
  const body = await res.json();
  return body.answer;
}

export async function analyzeSample(
  file: File,
): Promise<{ filename: string; duration_s: number; vector: number[] }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/sample", { method: "POST", body: form });
  if (!res.ok) throw new Error(await readError(res));
  const body = await res.json();
  return body.sample;
}

export async function runAgent(
  agent: string,
  project: DawProject | null,
  tracks: AiTrackPayload[],
): Promise<AgentResult> {
  const res = await fetch("/api/agent-run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent, project, tracks }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function reviewPlugins(
  project: DawProject,
  tracks: AiTrackPayload[],
): Promise<ChainReview> {
  const res = await fetch("/api/plugin-review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project, tracks }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function getFeedback(tracks: AiTrackPayload[]): Promise<string> {
  const res = await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tracks }),
  });
  if (!res.ok) throw new Error(await readError(res));
  const body = await res.json();
  return body.feedback;
}
