export type PhaseState =
  | "pending"
  | "running"
  | "completed"
  | "failed";

export type AnalysisStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed";

export type AnalysisStatusPayload = {
  sha256: string;
  status: AnalysisStatus;
  current_phase: string | null;
  phases: Record<string, PhaseState>;
  error: string | null;
  filename?: string;
  pipeline_name?: string;
  output_dir?: string | null;
  created_at?: string;
};

export type AnalysisListPayload = {
  available: boolean;
  analyses: AnalysisStatusPayload[];
};
