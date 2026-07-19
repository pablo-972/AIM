import type { AgentTrace } from "./traces";

export type JsonArtifact<T = unknown> = {
  available: boolean;
  data: T | null;
};

export type TextArtifact = {
  available: boolean;
  content: string;
};

export type AnalysisArtifacts = {
  analysisJson: JsonArtifact | null;
  staticInference: JsonArtifact<AgentTrace> | null;
  dynamicInference: JsonArtifact<AgentTrace> | null;
  enrichment: TextArtifact | null;
  reverseAgent: JsonArtifact<AgentTrace> | null;
  report: TextArtifact | null;
};
