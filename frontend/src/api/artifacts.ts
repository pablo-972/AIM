import type { AgentTrace, JsonArtifact, TextArtifact } from "../types";

import { request } from "./client";

export function getAnalysisJson(analysisId: string): Promise<JsonArtifact> {
  const encodedAnalysisId = encodeURIComponent(analysisId);

  return request<JsonArtifact>(
    `/api/analyses/${encodedAnalysisId}/analysis-json`,
  );
}

export function getStaticInference(
  analysisId: string
): Promise<JsonArtifact<AgentTrace>> {
  const encodedAnalysisId = encodeURIComponent(analysisId);

  return request<JsonArtifact<AgentTrace>>(
    `/api/analyses/${encodedAnalysisId}/static-inference`,
  );
}

export function getDynamicInference(
  analysisId: string
): Promise<JsonArtifact<AgentTrace>> {
  const encodedAnalysisId = encodeURIComponent(analysisId);

  return request<JsonArtifact<AgentTrace>>(
    `/api/analyses/${encodedAnalysisId}/dynamic-inference`,
  );
}

export function getEnrichment(analysisId: string): Promise<TextArtifact> {
  const encodedAnalysisId = encodeURIComponent(analysisId);

  return request<TextArtifact>(
    `/api/analyses/${encodedAnalysisId}/enrichment`,
  );
}

export function getReverseAgent(
  analysisId: string
): Promise<JsonArtifact<AgentTrace>> {
  const encodedAnalysisId = encodeURIComponent(analysisId);

  return request<JsonArtifact<AgentTrace>>(
    `/api/analyses/${encodedAnalysisId}/reverse-agent`,
  );
}

export function getReport(analysisId: string): Promise<TextArtifact> {
  const encodedAnalysisId = encodeURIComponent(analysisId);

  return request<TextArtifact>(
    `/api/analyses/${encodedAnalysisId}/report`,
  );
}
