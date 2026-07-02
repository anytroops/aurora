import { useEffect, useRef } from "react";
import WaveSurfer from "wavesurfer.js";

export default function Waveform({ url }: { url: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WaveSurfer | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const ws = WaveSurfer.create({
      container: containerRef.current,
      url,
      height: 72,
      waveColor: "#3d4654",
      progressColor: "#7dd3a8",
      cursorColor: "#7dd3a8",
      barWidth: 2,
      barGap: 1,
      normalize: true,
    });
    wsRef.current = ws;
    return () => {
      ws.destroy();
      wsRef.current = null;
    };
  }, [url]);

  return (
    <div
      className="cursor-pointer rounded-md bg-black/30 px-2 py-1"
      onClick={() => wsRef.current?.playPause()}
      title="Click to play/pause"
    >
      <div ref={containerRef} />
    </div>
  );
}
