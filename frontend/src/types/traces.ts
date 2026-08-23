export type TraceDecision = {
  thought?: string;
  confidence?: string;
  action?: string;
  parameters?: Record<string, unknown>;
};

export type TraceActionExecution = {
  tool?: string;
  target?: string;
  status?: string;
};

export type TraceFollowUp = {
  tool?: string;
  target?: string;
  priority?: number;
};

export type TraceStep = {
  step: number;
  input?: unknown;
  decision?: TraceDecision;
  action?: TraceActionExecution | null;
  finding?: unknown;
  follow_ups?: TraceFollowUp[];
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
