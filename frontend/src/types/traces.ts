export type TraceDecision = {
  thought?: string;
  confidence?: string;
  action?: string;
  parameters?: Record<string, unknown>;
};

export type TraceToolExecution = {
  name?: string;
  status?: string;
  output?: unknown;
  artifact_ref?: unknown;
};

export type TraceStep = {
  step: number;
  input?: unknown;
  decision?: TraceDecision;
  tool?: TraceToolExecution;
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