import { useRef, useState, type DragEvent } from "react";

interface Props {
  onFiles: (files: File[]) => void;
  busy: boolean;
}

export default function UploadZone({ onFiles, busy }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length) onFiles(files);
  };

  return (
    <div
      data-testid="upload-zone"
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
        dragging ? "border-accent bg-panel" : "border-edge hover:border-accent/60"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="audio/*,.wav,.mp3,.flac,.aiff,.ogg,.m4a"
        multiple
        className="hidden"
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          if (files.length) onFiles(files);
          e.target.value = "";
        }}
      />
      <p className="text-lg font-medium text-white">
        {busy ? "Analyzing…" : "Drop audio files here"}
      </p>
      <p className="mt-1 text-sm text-gray-400">
        WAV, MP3, FLAC, AIFF — stems or full mixes. Analysis runs locally on the
        backend; nothing leaves your machine except metrics sent for AI feedback.
      </p>
    </div>
  );
}
