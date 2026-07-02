export interface SpectralBalance {
  sub: number;
  bass: number;
  low_mid: number;
  mid: number;
  high_mid: number;
  high: number;
}

export interface TrackMetrics {
  filename: string;
  duration_s: number;
  sample_rate: number;
  channels: number;
  peak_dbfs: number;
  rms_dbfs: number;
  crest_factor_db: number;
  lufs_integrated: number | null;
  clipped_samples: number;
  max_clip_run: number;
  correlation: number | null;
  stereo_width: number | null;
  spectral_balance_pct: SpectralBalance;
  spectral_centroid_hz: number;
  noise_floor_db: number;
  tempo_bpm: number | null;
  key_estimate: string | null;
}

export interface Finding {
  severity: "high" | "medium" | "low";
  title: string;
  detail: string;
}

export interface DawTrack {
  name: string;
  type: string;
  devices: string[];
  clip_count: number;
}

export interface DawProject {
  daw: string;
  filename: string;
  tempo_bpm: number | null;
  track_count: number;
  clip_count: number;
  plugin_count: number;
  tracks: DawTrack[];
}

export interface ChatEntry {
  question: string;
  answer: string;
}

export interface TrackAnalysis {
  id: string;
  name: string;
  url: string; // object URL for waveform rendering
  metrics: TrackMetrics;
  findings: Finding[];
}
