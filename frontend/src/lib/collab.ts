import { useEffect, useRef, useState } from "react";
import type { Arrangement, Comment, DawProject, Finding, TrackMetrics } from "../types";

export interface SharedTrack {
  id: string;
  name: string;
  metrics: TrackMetrics;
  findings: Finding[];
  arrangement: Arrangement;
}

interface Handlers {
  onRemoteTrack: (track: SharedTrack) => void;
  onRemoteProject: (project: DawProject) => void;
}

function roomFromHash(): string {
  const match = window.location.hash.match(/room=([\w-]+)/);
  if (match) return match[1];
  const id = crypto.randomUUID().slice(0, 8);
  window.location.hash = `room=${id}`;
  return id;
}

export function useCollab(handlers: Handlers) {
  const [roomId] = useState(roomFromHash);
  const [connected, setConnected] = useState(false);
  const [peers, setPeers] = useState(1);
  const [comments, setComments] = useState<Comment[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/api/ws/${roomId}`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      switch (msg.type) {
        case "init":
          setPeers(msg.peers);
          setComments(msg.state.comments);
          for (const t of msg.state.tracks) handlersRef.current.onRemoteTrack(t);
          if (msg.state.project) handlersRef.current.onRemoteProject(msg.state.project);
          break;
        case "peers":
          setPeers(msg.peers);
          break;
        case "comment":
          setComments((prev) => [...prev, msg.comment]);
          break;
        case "track":
          handlersRef.current.onRemoteTrack(msg.track);
          break;
        case "project":
          handlersRef.current.onRemoteProject(msg.project);
          break;
      }
    };

    return () => ws.close();
  }, [roomId]);

  const send = (payload: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
    }
  };

  return {
    roomId,
    connected,
    peers,
    comments,
    shareUrl: `${window.location.origin}${window.location.pathname}#room=${roomId}`,
    sendComment: (author: string, text: string) => {
      const comment: Comment = {
        id: crypto.randomUUID(),
        author,
        text,
        ts: Date.now(),
      };
      setComments((prev) => [...prev, comment]);
      send({ type: "comment", comment });
    },
    announceTrack: (track: SharedTrack) => send({ type: "track", track }),
    announceProject: (project: DawProject) => send({ type: "project", project }),
  };
}
