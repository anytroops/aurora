import { useState } from "react";
import AgentPanel from "./components/AgentPanel";
import ChatPanel from "./components/ChatPanel";
import ComparePanel from "./components/ComparePanel";
import FeedbackPanel from "./components/FeedbackPanel";
import ProjectPanel from "./components/ProjectPanel";
import SamplePanel from "./components/SamplePanel";
import TrackCard from "./components/TrackCard";
import UploadZone from "./components/UploadZone";
import {
  analyzeFile,
  analyzeProject,
  askQuestion,
  getFeedback,
  reviewPlugins,
} from "./lib/api";
import type { ChainReview, ChatEntry, DawProject, TrackAnalysis } from "./types";

export default function App() {
  const [tracks, setTracks] = useState<TrackAnalysis[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [project, setProject] = useState<DawProject | null>(null);
  const [projectBusy, setProjectBusy] = useState(false);
  const [projectError, setProjectError] = useState<string | null>(null);

  const [review, setReview] = useState<ChainReview | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const [feedback, setFeedback] = useState<string | null>(null);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [feedbackLoading, setFeedbackLoading] = useState(false);

  const [chat, setChat] = useState<ChatEntry[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  const handleFiles = async (files: File[]) => {
    setAnalyzing(true);
    setUploadError(null);
    for (const file of files) {
      try {
        const { metrics, findings, arrangement } = await analyzeFile(file);
        setTracks((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            name: file.name,
            url: URL.createObjectURL(file),
            metrics,
            findings,
            arrangement,
          },
        ]);
      } catch (e) {
        setUploadError(e instanceof Error ? e.message : String(e));
      }
    }
    setAnalyzing(false);
  };

  const handleProjectFile = async (file: File) => {
    setProjectBusy(true);
    setProjectError(null);
    try {
      setProject(await analyzeProject(file));
      setReview(null);
      setReviewError(null);
    } catch (e) {
      setProjectError(e instanceof Error ? e.message : String(e));
    } finally {
      setProjectBusy(false);
    }
  };

  const handleReview = async () => {
    if (!project) return;
    setReviewLoading(true);
    setReviewError(null);
    try {
      setReview(await reviewPlugins(project, aiTracks()));
    } catch (e) {
      setReviewError(e instanceof Error ? e.message : String(e));
    } finally {
      setReviewLoading(false);
    }
  };

  // Full energy curves are for rendering; the AI gets the section/transition
  // summary to keep the prompt compact.
  const aiTracks = () =>
    tracks.map(({ metrics, findings, arrangement }) => ({
      metrics,
      findings,
      arrangement: {
        sections: arrangement.sections,
        transitions: arrangement.transitions,
      },
    }));

  const handleFeedback = async () => {
    setFeedbackLoading(true);
    setFeedbackError(null);
    try {
      setFeedback(await getFeedback(aiTracks()));
    } catch (e) {
      setFeedbackError(e instanceof Error ? e.message : String(e));
    } finally {
      setFeedbackLoading(false);
    }
  };

  const handleAsk = async (question: string, mode: "session" | "dsp_code") => {
    setChatLoading(true);
    setChatError(null);
    try {
      const answer = await askQuestion(question, project, aiTracks(), mode);
      setChat((prev) => [...prev, { question, answer }]);
    } catch (e) {
      setChatError(e instanceof Error ? e.message : String(e));
    } finally {
      setChatLoading(false);
    }
  };

  const hasSessionData = project !== null || tracks.length > 0;

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold tracking-tight text-white">
          Aurora
        </h1>
        <p className="mt-1 text-sm text-gray-400">
          Drop in stems, a mix, or your DAW project file — get real DSP
          measurements, session structure, and AI engineering feedback grounded
          in them.
        </p>
      </header>

      <div className="space-y-4">
        <UploadZone onFiles={handleFiles} busy={analyzing} />

        {uploadError && (
          <div className="rounded-md border border-alert/40 bg-alert/10 px-3 py-2 text-sm text-alert">
            {uploadError}
          </div>
        )}

        <ProjectPanel
          project={project}
          onFile={handleProjectFile}
          busy={projectBusy}
          error={projectError}
          onReview={handleReview}
          review={review}
          reviewLoading={reviewLoading}
          reviewError={reviewError}
        />

        {tracks.map((t) => (
          <TrackCard key={t.id} track={t} />
        ))}

        <SamplePanel />

        {tracks.length >= 2 && <ComparePanel tracks={tracks} />}

        {tracks.length > 0 && (
          <FeedbackPanel
            onRequest={handleFeedback}
            loading={feedbackLoading}
            feedback={feedback}
            error={feedbackError}
            disabled={tracks.length === 0}
          />
        )}

        <AgentPanel tracks={aiTracks()} project={project} />

        <ChatPanel
          onAsk={handleAsk}
          entries={chat}
          loading={chatLoading}
          error={chatError}
          hasSessionData={hasSessionData}
        />
      </div>
    </div>
  );
}
