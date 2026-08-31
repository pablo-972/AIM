export type TraceDecision = {
  thought?: string | null;
  thinking?: string[];
  summary?: string;
  confidence?: string;
  action?: string;
  parameters?: Record<string, unknown>;
};

export type TraceInput = {
  type?: string;
  tool?: string;
  target?: string;
  chunk?: number;
  total_chunks?: number;
  status?: string;
};

export type TraceToolCall = {
  tool?: string;
  target?: string;
  priority?: number;
};

export type TraceStep = {
  step: number;
  input?: TraceInput;
  decision?: TraceDecision;
  finding?: unknown;
  tool_calls?: TraceToolCall[];
  error?: string | null;
};

export type AgentTrace = {
  agent?: string;
  status?: string;
  state?: unknown;
  steps?: TraceStep[];
  findings?: unknown[];
  queue?: unknown[];
  errors?: unknown[];
};
