export type PhaseState = "pending" | "running" | "completed" | "failed";

export type AnalysisStatusPayload = {
  analysis_id: string;
  status: "queued" | "running" | "completed" | "failed";
  current_phase: string | null;
  phases: Record<string, PhaseState>;
  error: string | null;
  filename?: string;
  pipeline_name?: string;
  sample_sha256?: string | null;
  output_dir?: string | null;
  created_at?: string;
};

export type AnalysisListPayload = {
  available: boolean;
  analyses: AnalysisStatusPayload[];
};

export type JsonArtifact<T = unknown> = {
  available: boolean;
  data: T | null;
};

export type TextArtifact = {
  available: boolean;
  content: string;
};

export type TraceStep = {
  step: number;
  input?: unknown;
  decision?: {
    thought?: string;
    confidence?: string;
    action?: string;
    parameters?: Record<string, unknown>;
  };
  tool?: {
    name?: string;
    status?: string;
    output?: unknown;
    artifact_ref?: unknown;
  };
  finding?: unknown;
  error?: string | null;
};

export type AgentTrace = {
  agent?: string;
  status?: string;
  steps?: TraceStep[];
  findings?: unknown[];
  queue?: unknown[];
  errors?: unknown[];
};
