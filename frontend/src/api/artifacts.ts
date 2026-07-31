import type { AgentTrace, JsonArtifact, TextArtifact } from "../types";

import { request } from "./client";

export function getAnalysisJson(sha256: string): Promise<JsonArtifact> {
  const encodedSha256 = encodeURIComponent(sha256);

  return request<JsonArtifact>(
    `/api/analyses/${encodedSha256}/analysis-json`,
  );
}

export function getStaticInference(
  sha256: string
): Promise<JsonArtifact<AgentTrace>> {
  const encodedSha256 = encodeURIComponent(sha256);

  return request<JsonArtifact<AgentTrace>>(
    `/api/analyses/${encodedSha256}/static-inference`,
  );
}

export function getDynamicInference(
  sha256: string
): Promise<JsonArtifact<AgentTrace>> {
  const encodedSha256 = encodeURIComponent(sha256);

  return request<JsonArtifact<AgentTrace>>(
    `/api/analyses/${encodedSha256}/dynamic-inference`,
  );
}

export function getEnrichment(sha256: string): Promise<TextArtifact> {
  const encodedSha256 = encodeURIComponent(sha256);

  return request<TextArtifact>(
    `/api/analyses/${encodedSha256}/enrichment`,
  );
}

export function getReverseAgent(
  sha256: string
): Promise<JsonArtifact<AgentTrace>> {
  const encodedSha256 = encodeURIComponent(sha256);

  return request<JsonArtifact<AgentTrace>>(
    `/api/analyses/${encodedSha256}/reverse-agent`,
  );
}

export function getReport(sha256: string): Promise<TextArtifact> {
  const encodedSha256 = encodeURIComponent(sha256);

  return request<TextArtifact>(
    `/api/analyses/${encodedSha256}/report`,
  );
}
